from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    image_path = LaunchConfiguration("image_path")
    target_width = LaunchConfiguration("target_width")
    max_points = LaunchConfiguration("max_points")
    draw_delay = LaunchConfiguration("draw_delay")
    move_tolerance = LaunchConfiguration("move_tolerance")
    max_linear_speed = LaunchConfiguration("max_linear_speed")
    max_angular_speed = LaunchConfiguration("max_angular_speed")
    stroke_speed = LaunchConfiguration("stroke_speed")
    min_segment_time = LaunchConfiguration("min_segment_time")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "image_path",
                default_value=PathJoinSubstitution([FindPackageShare("turtle_draw_dog"), "assets", "dog.png"]),
            ),
            DeclareLaunchArgument("target_width", default_value="230"),
            DeclareLaunchArgument("max_points", default_value="1800"),
            DeclareLaunchArgument("draw_delay", default_value="0.0"),
            DeclareLaunchArgument("move_tolerance", default_value="0.09"),
            DeclareLaunchArgument("max_linear_speed", default_value="3.2"),
            DeclareLaunchArgument("max_angular_speed", default_value="8.0"),
            DeclareLaunchArgument("stroke_speed", default_value="4.0"),
            DeclareLaunchArgument("min_segment_time", default_value="0.018"),
            Node(
                package="turtlesim",
                executable="turtlesim_node",
                name="turtlesim",
                output="screen",
                parameters=[
                    {
                        "background_r": 245,
                        "background_g": 245,
                        "background_b": 245,
                    }
                ],
            ),
            Node(
                package="turtle_draw_dog",
                executable="draw_dog",
                name="turtle_dog_drawer",
                output="screen",
                parameters=[
                    {
                        "image_path": image_path,
                        "target_width": target_width,
                        "max_points": max_points,
                        "draw_delay": draw_delay,
                        "move_tolerance": move_tolerance,
                        "max_linear_speed": max_linear_speed,
                        "max_angular_speed": max_angular_speed,
                        "stroke_speed": stroke_speed,
                        "min_segment_time": min_segment_time,
                    }
                ],
            ),
        ]
    )
