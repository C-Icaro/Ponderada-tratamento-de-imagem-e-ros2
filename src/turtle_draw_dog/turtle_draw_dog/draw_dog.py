from __future__ import annotations

import math
import time
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_srvs.srv import Empty
from turtlesim.msg import Pose
from turtlesim.srv import SetPen, TeleportAbsolute

from turtle_draw_dog.image_pipeline import build_vision_paths


def default_image_path() -> str:
    share_dir = Path(get_package_share_directory("turtle_draw_dog"))
    return str(share_dir / "assets" / "dog.png")


class TurtleDogDrawer(Node):
    def __init__(self) -> None:
        super().__init__("turtle_dog_drawer")
        self.declare_parameter("image_path", default_image_path())
        self.declare_parameter("target_width", 230)
        self.declare_parameter("max_points", 1800)
        self.declare_parameter("pen_width", 3)
        self.declare_parameter("draw_delay", 0.0)
        self.declare_parameter("move_tolerance", 0.09)
        self.declare_parameter("max_linear_speed", 3.2)
        self.declare_parameter("max_angular_speed", 8.0)
        self.declare_parameter("stroke_speed", 4.0)
        self.declare_parameter("min_segment_time", 0.018)

        self.teleport_client = self.create_client(TeleportAbsolute, "/turtle1/teleport_absolute")
        self.pen_client = self.create_client(SetPen, "/turtle1/set_pen")
        self.clear_client = self.create_client(Empty, "/clear")
        self.cmd_vel_pub = self.create_publisher(Twist, "/turtle1/cmd_vel", 10)
        self.pose_sub = self.create_subscription(Pose, "/turtle1/pose", self.pose_callback, 10)
        self.pose: Pose | None = None

    def pose_callback(self, pose: Pose) -> None:
        self.pose = pose

    def wait_for_services(self) -> None:
        services = (
            (self.teleport_client, "/turtle1/teleport_absolute"),
            (self.pen_client, "/turtle1/set_pen"),
            (self.clear_client, "/clear"),
        )
        for client, name in services:
            self.get_logger().info(f"Aguardando servico {name}...")
            if not client.wait_for_service(timeout_sec=20.0):
                raise RuntimeError(f"Servico indisponivel: {name}")

    def call_service(self, client, request, timeout_sec: float = 10.0):
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if not future.done():
            raise TimeoutError("Timeout aguardando resposta de servico")
        result = future.result()
        if result is None and future.exception() is not None:
            raise future.exception()
        return result

    def clear_canvas(self) -> None:
        self.call_service(self.clear_client, Empty.Request())

    def set_pen(self, off: bool) -> None:
        request = SetPen.Request()
        request.r = 20
        request.g = 20
        request.b = 20
        request.width = int(self.get_parameter("pen_width").value)
        request.off = 1 if off else 0
        self.call_service(self.pen_client, request)

    def teleport(self, x: float, y: float, theta: float = 0.0) -> None:
        request = TeleportAbsolute.Request()
        request.x = float(x)
        request.y = float(y)
        request.theta = float(theta)
        self.call_service(self.teleport_client, request)
        self.wait_for_pose_near(x, y)

    @staticmethod
    def segment_theta(previous: tuple[float, float], current: tuple[float, float]) -> float:
        return math.atan2(current[1] - previous[1], current[0] - previous[0])

    @staticmethod
    def normalize_angle(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    def publish_stop(self) -> None:
        self.cmd_vel_pub.publish(Twist())

    def wait_for_pose_near(self, x: float, y: float, timeout_sec: float = 2.0) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            if self.pose is None:
                continue
            if math.hypot(float(self.pose.x) - x, float(self.pose.y) - y) < 0.12:
                return

    def move_to(self, x: float, y: float) -> bool:
        x = max(0.45, min(10.55, x))
        y = max(0.45, min(10.55, y))
        tolerance = float(self.get_parameter("move_tolerance").value)
        max_linear = float(self.get_parameter("max_linear_speed").value)
        max_angular = float(self.get_parameter("max_angular_speed").value)
        deadline = time.monotonic() + 3.0

        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.01)
            if self.pose is None:
                continue

            dx = x - float(self.pose.x)
            dy = y - float(self.pose.y)
            distance = math.hypot(dx, dy)
            if distance <= tolerance:
                self.publish_stop()
                return True

            target_theta = math.atan2(dy, dx)
            angle_error = self.normalize_angle(target_theta - float(self.pose.theta))

            command = Twist()
            command.angular.z = max(-max_angular, min(max_angular, 5.5 * angle_error))
            if abs(angle_error) < 0.35:
                command.linear.x = max(0.15, min(max_linear, 3.2 * distance))
            else:
                command.linear.x = 0.0
            self.cmd_vel_pub.publish(command)

        self.publish_stop()
        return False

    def drive_straight_for(self, duration: float, speed: float) -> None:
        command = Twist()
        command.linear.x = float(speed)
        end_time = time.monotonic() + max(0.0, duration)
        while rclpy.ok() and time.monotonic() < end_time:
            self.cmd_vel_pub.publish(command)
            rclpy.spin_once(self, timeout_sec=0.01)
        self.publish_stop()

    def draw_segment(self, previous: tuple[float, float], current: tuple[float, float]) -> None:
        theta = self.segment_theta(previous, current)
        distance = math.hypot(current[0] - previous[0], current[1] - previous[1])
        speed = float(self.get_parameter("stroke_speed").value)
        min_segment_time = float(self.get_parameter("min_segment_time").value)
        duration = max(min_segment_time, distance / max(0.1, speed))

        self.set_pen(off=True)
        self.teleport(previous[0], previous[1], theta)
        self.set_pen(off=False)
        self.drive_straight_for(duration, speed)
        self.teleport(current[0], current[1], theta)
        self.set_pen(off=True)

    def draw_paths(self, paths: list) -> None:
        delay = float(self.get_parameter("draw_delay").value)
        drawn_points = 0
        for index, path in enumerate(paths, start=1):
            if len(path) < 2:
                continue

            first = path[0]
            self.set_pen(off=True)
            self.teleport(float(first[0]), float(first[1]), 0.0)
            self.set_pen(off=False)

            previous = (float(first[0]), float(first[1]))
            for point in path[1:]:
                current = (float(point[0]), float(point[1]))
                self.draw_segment(previous, current)
                previous = current
                drawn_points += 1
                if delay > 0.0:
                    time.sleep(delay)

            if index % 10 == 0:
                self.get_logger().info(f"{index} caminhos desenhados...")

        self.set_pen(off=True)
        self.publish_stop()
        self.get_logger().info(f"Desenho concluido com {drawn_points} segmentos.")

    def run(self) -> None:
        image_path = str(self.get_parameter("image_path").value)
        target_width = int(self.get_parameter("target_width").value)
        max_points = int(self.get_parameter("max_points").value)

        self.wait_for_services()
        self.clear_canvas()
        self.get_logger().info(f"Processando imagem: {image_path}")
        result = build_vision_paths(
            image_path=image_path,
            target_width=target_width,
            max_points=max_points,
        )
        self.get_logger().info(
            "Pipeline pronta: "
            f"crop={result.crop_box}, bordas={int(result.edge_map.sum())}, "
            f"caminhos={len(result.paths_turtlesim)}, pontos={result.total_points}"
        )
        self.draw_paths(result.paths_turtlesim)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TurtleDogDrawer()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
