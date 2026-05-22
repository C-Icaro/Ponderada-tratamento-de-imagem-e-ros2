from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


NEIGHBORS_8 = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


@dataclass
class VisionResult:
    original_shape: tuple[int, int]
    crop_box: tuple[int, int, int, int]
    work_image: np.ndarray
    edge_map: np.ndarray
    paths_pixels: list[np.ndarray]
    paths_turtlesim: list[np.ndarray]
    total_points: int


def load_image_rgb(path: str | Path) -> np.ndarray:
    """Load an image with OpenCV only; all processing after this is NumPy."""
    import cv2

    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(f"Could not load image: {path}")
    return image_bgr[:, :, ::-1].astype(np.float32) / 255.0


def rgb_to_gray(rgb: np.ndarray) -> np.ndarray:
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    return 0.299 * red + 0.587 * green + 0.114 * blue


def normalize01(image: np.ndarray, low_percentile: float = 2.0, high_percentile: float = 98.0) -> np.ndarray:
    low = float(np.percentile(image, low_percentile))
    high = float(np.percentile(image, high_percentile))
    if high <= low:
        return np.zeros_like(image, dtype=np.float32)
    return np.clip((image - low) / (high - low), 0.0, 1.0).astype(np.float32)


def resize_bilinear(image: np.ndarray, target_width: int) -> np.ndarray:
    height, width = image.shape[:2]
    if width == target_width:
        return image.copy()
    target_height = max(2, int(round(height * target_width / width)))

    y_positions = np.linspace(0, height - 1, target_height)
    x_positions = np.linspace(0, width - 1, target_width)
    y0 = np.floor(y_positions).astype(np.int32)
    x0 = np.floor(x_positions).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, height - 1)
    x1 = np.clip(x0 + 1, 0, width - 1)
    wy = (y_positions - y0).astype(np.float32)
    wx = (x_positions - x0).astype(np.float32)

    if image.ndim == 2:
        top = (1.0 - wx) * image[y0[:, None], x0[None, :]] + wx * image[y0[:, None], x1[None, :]]
        bottom = (1.0 - wx) * image[y1[:, None], x0[None, :]] + wx * image[y1[:, None], x1[None, :]]
        return ((1.0 - wy)[:, None] * top + wy[:, None] * bottom).astype(np.float32)

    top = (1.0 - wx)[None, :, None] * image[y0[:, None], x0[None, :], :] + wx[None, :, None] * image[
        y0[:, None], x1[None, :], :
    ]
    bottom = (1.0 - wx)[None, :, None] * image[y1[:, None], x0[None, :], :] + wx[None, :, None] * image[
        y1[:, None], x1[None, :], :
    ]
    return ((1.0 - wy)[:, None, None] * top + wy[:, None, None] * bottom).astype(np.float32)


def convolve2d(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    pad_y = kernel.shape[0] // 2
    pad_x = kernel.shape[1] // 2
    padded = np.pad(image, ((pad_y, pad_y), (pad_x, pad_x)), mode="edge")
    output = np.zeros_like(image, dtype=np.float32)
    for ky in range(kernel.shape[0]):
        for kx in range(kernel.shape[1]):
            output += kernel[ky, kx] * padded[ky : ky + image.shape[0], kx : kx + image.shape[1]]
    return output


def gaussian_kernel(size: int = 5, sigma: float = 1.1) -> np.ndarray:
    axis = np.arange(-(size // 2), size // 2 + 1, dtype=np.float32)
    yy, xx = np.meshgrid(axis, axis, indexing="ij")
    kernel = np.exp(-(xx * xx + yy * yy) / (2.0 * sigma * sigma))
    return (kernel / kernel.sum()).astype(np.float32)


def binary_dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        expanded = np.zeros_like(result, dtype=bool)
        for dy, dx in NEIGHBORS_8 + ((0, 0),):
            expanded |= padded[1 + dy : 1 + dy + result.shape[0], 1 + dx : 1 + dx + result.shape[1]]
        result = expanded
    return result


def binary_erode(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        shrunk = np.ones_like(result, dtype=bool)
        for dy, dx in NEIGHBORS_8 + ((0, 0),):
            shrunk &= padded[1 + dy : 1 + dy + result.shape[0], 1 + dx : 1 + dx + result.shape[1]]
        result = shrunk
    return result


def component_boxes(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    visited = np.zeros(mask.shape, dtype=bool)
    ys, xs = np.nonzero(mask)
    boxes: list[tuple[int, int, int, int, int]] = []

    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x]:
            continue
        stack = [(start_y, start_x)]
        visited[start_y, start_x] = True
        count = 0
        min_y = max_y = start_y
        min_x = max_x = start_x

        while stack:
            y, x = stack.pop()
            count += 1
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            for dy, dx in NEIGHBORS_8:
                ny, nx = y + dy, x + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))

        boxes.append((count, min_y, min_x, max_y, max_x))

    boxes.sort(reverse=True, key=lambda item: item[0])
    return boxes


def foreground_crop_box(gray: np.ndarray) -> tuple[int, int, int, int]:
    threshold = min(0.45, float(np.percentile(gray, 30.0)))
    foreground = gray < threshold
    foreground = binary_dilate(foreground, iterations=1)
    foreground = binary_erode(foreground, iterations=1)

    boxes = component_boxes(foreground)
    if not boxes:
        return (0, 0, gray.shape[1], gray.shape[0])

    largest = boxes[0][0]
    selected = [box for box in boxes if box[0] >= max(80, int(largest * 0.05))]
    min_y = min(box[1] for box in selected)
    min_x = min(box[2] for box in selected)
    max_y = max(box[3] for box in selected)
    max_x = max(box[4] for box in selected)

    box_width = max_x - min_x + 1
    box_height = max_y - min_y + 1
    margin = int(round(0.14 * max(box_width, box_height)))
    x0 = max(0, min_x - margin)
    y0 = max(0, min_y - margin)
    x1 = min(gray.shape[1], max_x + margin + 1)
    y1 = min(gray.shape[0], max_y + margin + 1)
    return (x0, y0, x1, y1)


def sobel_gradients(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float32)
    gx = convolve2d(image, sobel_x)
    gy = convolve2d(image, sobel_y)
    magnitude = np.hypot(gx, gy)
    angle = np.rad2deg(np.arctan2(gy, gx)) % 180.0
    return gx, gy, magnitude, angle


def non_maximum_suppression(magnitude: np.ndarray, angle: np.ndarray) -> np.ndarray:
    output = np.zeros_like(magnitude, dtype=np.float32)
    center = magnitude[1:-1, 1:-1]
    local_angle = angle[1:-1, 1:-1]

    left = magnitude[1:-1, :-2]
    right = magnitude[1:-1, 2:]
    up = magnitude[:-2, 1:-1]
    down = magnitude[2:, 1:-1]
    up_left = magnitude[:-2, :-2]
    up_right = magnitude[:-2, 2:]
    down_left = magnitude[2:, :-2]
    down_right = magnitude[2:, 2:]

    horizontal = (local_angle < 22.5) | (local_angle >= 157.5)
    diagonal_45 = (local_angle >= 22.5) & (local_angle < 67.5)
    vertical = (local_angle >= 67.5) & (local_angle < 112.5)
    diagonal_135 = (local_angle >= 112.5) & (local_angle < 157.5)

    keep = np.zeros_like(center, dtype=bool)
    keep |= horizontal & (center >= left) & (center >= right)
    keep |= diagonal_45 & (center >= up_right) & (center >= down_left)
    keep |= vertical & (center >= up) & (center >= down)
    keep |= diagonal_135 & (center >= up_left) & (center >= down_right)

    output[1:-1, 1:-1] = np.where(keep, center, 0.0)
    return output


def hysteresis_threshold(nms: np.ndarray, high_percentile: float = 72.0, low_ratio: float = 0.35) -> np.ndarray:
    positive = nms[nms > 0]
    if positive.size == 0:
        return np.zeros_like(nms, dtype=bool)

    high = float(np.percentile(positive, high_percentile))
    low = high * low_ratio
    strong = nms >= high
    weak = (nms >= low) & ~strong
    edges = strong.copy()

    queue = list(zip(*np.nonzero(strong)))
    while queue:
        y, x = queue.pop()
        for dy, dx in NEIGHBORS_8:
            ny, nx = y + dy, x + dx
            if 0 <= ny < nms.shape[0] and 0 <= nx < nms.shape[1] and weak[ny, nx] and not edges[ny, nx]:
                edges[ny, nx] = True
                queue.append((ny, nx))

    return edges


def detect_edges(image: np.ndarray) -> np.ndarray:
    blurred = convolve2d(image, gaussian_kernel(size=5, sigma=1.05))
    _, _, magnitude, angle = sobel_gradients(blurred)
    nms = non_maximum_suppression(magnitude, angle)

    best_edges = np.zeros_like(nms, dtype=bool)
    for percentile in (76.0, 70.0, 64.0):
        edges = hysteresis_threshold(nms, high_percentile=percentile, low_ratio=0.35)
        best_edges = edges
        if int(edges.sum()) >= 350:
            break
    return best_edges


def edge_components(edge_map: np.ndarray, min_size: int) -> list[np.ndarray]:
    visited = np.zeros(edge_map.shape, dtype=bool)
    ys, xs = np.nonzero(edge_map)
    components: list[np.ndarray] = []

    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x]:
            continue
        stack = [(start_y, start_x)]
        visited[start_y, start_x] = True
        points: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            points.append((y, x))
            for dy, dx in NEIGHBORS_8:
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < edge_map.shape[0]
                    and 0 <= nx < edge_map.shape[1]
                    and edge_map[ny, nx]
                    and not visited[ny, nx]
                ):
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        if len(points) >= min_size:
            components.append(np.array(points, dtype=np.int32))

    components.sort(reverse=True, key=len)
    return components


def selected_component_mask(mask: np.ndarray, keep_ratio: float = 0.05) -> np.ndarray:
    components = edge_components(mask, min_size=8)
    selected = np.zeros(mask.shape, dtype=bool)
    if not components:
        return selected

    largest = len(components[0])
    for component in components:
        if len(component) < max(8, int(largest * keep_ratio)):
            break
        selected[component[:, 0], component[:, 1]] = True
    return selected


def foreground_boundary_edges(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    threshold = min(0.58, float(np.percentile(image, 45.0)))
    dark_regions = image < threshold
    dark_regions = binary_dilate(dark_regions, iterations=1)
    subject = selected_component_mask(dark_regions, keep_ratio=0.045)
    subject = binary_dilate(subject, iterations=2)
    subject = binary_erode(subject, iterations=1)
    boundary = subject & ~binary_erode(subject, iterations=1)
    return subject, boundary


def neighbor_degree(point: tuple[int, int], point_set: set[tuple[int, int]]) -> int:
    y, x = point
    return sum((y + dy, x + dx) in point_set for dy, dx in NEIGHBORS_8)


def pick_trace_start(unvisited: set[tuple[int, int]], point_set: set[tuple[int, int]]) -> tuple[int, int]:
    candidates = list(unvisited)
    endpoints = [point for point in candidates if neighbor_degree(point, point_set) <= 1]
    if endpoints:
        return min(endpoints)
    return min(candidates)


def trace_component(component: np.ndarray) -> list[np.ndarray]:
    point_set = {tuple(item) for item in component.tolist()}
    unvisited = set(point_set)
    paths: list[np.ndarray] = []

    while unvisited:
        current = pick_trace_start(unvisited, point_set)
        path = [current]
        unvisited.remove(current)
        previous: tuple[int, int] | None = None

        while True:
            y, x = current
            neighbors = [(y + dy, x + dx) for dy, dx in NEIGHBORS_8 if (y + dy, x + dx) in unvisited]
            if not neighbors:
                break
            if previous is None:
                next_point = min(neighbors)
            else:
                direction = np.array([current[0] - previous[0], current[1] - previous[1]], dtype=np.float32)

                def score(point: tuple[int, int]) -> float:
                    candidate = np.array([point[0] - current[0], point[1] - current[1]], dtype=np.float32)
                    return float(np.dot(direction, candidate))

                next_point = max(neighbors, key=score)
            previous = current
            current = next_point
            path.append(current)
            unvisited.remove(current)

        if len(path) >= 2:
            paths.append(np.array(path, dtype=np.float32))

    return paths


def simplify_by_distance(points: np.ndarray, min_step: float) -> np.ndarray:
    if len(points) <= 2:
        return points
    kept = [points[0]]
    last = points[0]
    for point in points[1:-1]:
        if float(np.linalg.norm(point - last)) >= min_step:
            kept.append(point)
            last = point
    kept.append(points[-1])
    return np.array(kept, dtype=np.float32)


def rdp_simplify(points: np.ndarray, epsilon: float) -> np.ndarray:
    if len(points) <= 2:
        return points

    keep = np.zeros(len(points), dtype=bool)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]

    while stack:
        start, end = stack.pop()
        segment = points[end] - points[start]
        middle = points[start + 1 : end]
        if middle.size == 0:
            continue
        length = float(np.linalg.norm(segment))
        if length == 0.0:
            distances = np.linalg.norm(middle - points[start], axis=1)
        else:
            vectors = middle - points[start]
            distances = np.abs(segment[1] * vectors[:, 0] - segment[0] * vectors[:, 1]) / length
        index = int(np.argmax(distances))
        if float(distances[index]) > epsilon:
            split = start + 1 + index
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))

    return points[keep]


def connect_nearby_paths(paths: list[np.ndarray], max_gap: float = 3.0) -> list[np.ndarray]:
    connected: list[np.ndarray] = []
    unused = [path for path in paths if len(path) >= 2]

    while unused:
        current = unused.pop(0)
        while unused:
            best_index = -1
            best_distance = max_gap
            best_mode = "append"
            best_reverse = False

            for index, candidate in enumerate(unused):
                options = (
                    (current[-1], candidate[0], "append", False),
                    (current[-1], candidate[-1], "append", True),
                    (current[0], candidate[-1], "prepend", False),
                    (current[0], candidate[0], "prepend", True),
                )
                for current_endpoint, candidate_endpoint, mode, reverse in options:
                    distance = float(np.linalg.norm(current_endpoint - candidate_endpoint))
                    if distance <= best_distance:
                        best_index = index
                        best_distance = distance
                        best_mode = mode
                        best_reverse = reverse

            if best_index < 0:
                break

            candidate = unused.pop(best_index)
            if best_reverse:
                candidate = candidate[::-1]
            if best_mode == "append":
                current = np.vstack((current, candidate[1:] if best_distance < 0.1 else candidate))
            else:
                current = np.vstack((candidate[:-1] if best_distance < 0.1 else candidate, current))

        connected.append(current)

    return connected


def densify_path(points: np.ndarray, max_step: float = 2.2) -> np.ndarray:
    if len(points) <= 1:
        return points

    dense: list[np.ndarray] = [points[0]]
    for start, end in zip(points[:-1], points[1:]):
        distance = float(np.linalg.norm(end - start))
        steps = max(1, int(np.ceil(distance / max_step)))
        for step in range(1, steps + 1):
            dense.append(start + (end - start) * (step / steps))

    return np.array(dense, dtype=np.float32)


def limit_total_points(paths: list[np.ndarray], max_points: int) -> list[np.ndarray]:
    valid_paths = [path for path in paths if len(path) >= 2]
    if not valid_paths or max_points < 2:
        return []

    total_points = sum(len(path) for path in valid_paths)
    if total_points <= max_points:
        return valid_paths

    selected_count = min(len(valid_paths), max(1, max_points // 2))
    selected_paths = valid_paths[:selected_count]
    while selected_paths and sum(min(3, len(path)) for path in selected_paths) > max_points:
        selected_paths.pop()

    if not selected_paths:
        return []

    base_counts = np.array([min(3, len(path)) for path in selected_paths], dtype=np.int32)
    remaining = max_points - int(base_counts.sum())
    weights = np.sqrt(np.array([len(path) for path in selected_paths], dtype=np.float32))
    raw_extra = remaining * weights / max(float(weights.sum()), 1.0)
    extra_counts = np.floor(raw_extra).astype(np.int32)
    counts = base_counts + extra_counts

    spare = max_points - int(counts.sum())
    if spare > 0:
        fractions = raw_extra - extra_counts
        for index in np.argsort(-fractions)[:spare]:
            counts[index] += 1

    limited: list[np.ndarray] = []
    for path, count in zip(selected_paths, counts.tolist()):
        count = max(2, min(int(count), len(path)))
        if count >= len(path):
            limited.append(path)
            continue
        indices = np.linspace(0, len(path) - 1, count).round().astype(np.int32)
        indices = np.unique(indices)
        if len(indices) < 2:
            indices = np.array([0, len(path) - 1], dtype=np.int32)
        limited.append(path[indices])

    return limited


def extract_paths(edge_map: np.ndarray, max_points: int = 1800) -> list[np.ndarray]:
    components = edge_components(edge_map, min_size=8)
    paths: list[np.ndarray] = []
    for component in components[:80]:
        component_paths: list[np.ndarray] = []
        for path in trace_component(component):
            path = simplify_by_distance(path, min_step=1.2)
            path = rdp_simplify(path, epsilon=0.45)
            path = densify_path(path, max_step=2.2)
            if len(path) >= 3:
                component_paths.append(path)
        paths.extend(connect_nearby_paths(component_paths, max_gap=3.0))
    paths.sort(reverse=True, key=len)
    return limit_total_points(paths, max_points=max_points)


def map_paths_to_turtlesim(
    paths: list[np.ndarray],
    canvas_shape: tuple[int, int],
    turtle_min: float = 1.25,
    turtle_max: float = 9.75,
) -> list[np.ndarray]:
    if not paths:
        return []

    all_points = np.vstack(paths)
    min_y, min_x = all_points.min(axis=0)
    max_y, max_x = all_points.max(axis=0)
    width = max(1.0, float(max_x - min_x))
    height = max(1.0, float(max_y - min_y))
    span = turtle_max - turtle_min
    scale = min(span / width, span / height)
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    turtle_center = (turtle_min + turtle_max) / 2.0

    mapped: list[np.ndarray] = []
    for path in paths:
        xs = turtle_center + (path[:, 1] - center_x) * scale
        ys = turtle_center - (path[:, 0] - center_y) * scale
        turtle_path = np.column_stack((xs, ys)).astype(np.float32)
        turtle_path[:, 0] = np.clip(turtle_path[:, 0], 0.2, 10.8)
        turtle_path[:, 1] = np.clip(turtle_path[:, 1], 0.2, 10.8)
        mapped.append(turtle_path)

    return mapped


def build_vision_paths(
    image_path: str | Path,
    target_width: int = 230,
    max_points: int = 1800,
) -> VisionResult:
    rgb = load_image_rgb(image_path)
    gray = rgb_to_gray(rgb)
    x0, y0, x1, y1 = foreground_crop_box(gray)
    cropped = gray[y0:y1, x0:x1]
    resized = resize_bilinear(cropped, target_width=target_width)
    normalized = normalize01(resized)
    sobel_edges = detect_edges(normalized)
    subject_mask, subject_boundary = foreground_boundary_edges(normalized)
    edge_map = (sobel_edges & binary_dilate(subject_mask, iterations=1)) | subject_boundary
    paths_pixels = extract_paths(edge_map, max_points=max_points)
    paths_turtlesim = map_paths_to_turtlesim(paths_pixels, edge_map.shape)
    total_points = sum(len(path) for path in paths_turtlesim)

    return VisionResult(
        original_shape=gray.shape,
        crop_box=(x0, y0, x1, y1),
        work_image=normalized,
        edge_map=edge_map,
        paths_pixels=paths_pixels,
        paths_turtlesim=paths_turtlesim,
        total_points=total_points,
    )


def save_debug_images(result: VisionResult, output_dir: str | Path) -> None:
    import matplotlib.pyplot as plt

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plt.imsave(output / "01_preprocessed_gray.png", result.work_image, cmap="gray")
    plt.imsave(output / "02_edges.png", result.edge_map.astype(np.float32), cmap="gray")

    preview = np.ones((*result.edge_map.shape, 3), dtype=np.float32)
    for path in result.paths_pixels:
        coords = np.round(path).astype(np.int32)
        for start, end in zip(coords[:-1], coords[1:]):
            draw_line_pixels(preview, start, end, color=np.array([0.0, 0.0, 0.0], dtype=np.float32))
    plt.imsave(output / "03_paths_preview.png", preview)


def draw_line_pixels(canvas: np.ndarray, start: np.ndarray, end: np.ndarray, color: np.ndarray) -> None:
    height, width = canvas.shape[:2]
    y0, x0 = int(start[0]), int(start[1])
    y1, x1 = int(end[0]), int(end[1])

    dy = abs(y1 - y0)
    dx = abs(x1 - x0)
    step_y = 1 if y0 < y1 else -1
    step_x = 1 if x0 < x1 else -1

    def mark(y: int, x: int) -> None:
        if 0 <= y < height and 0 <= x < width:
            canvas[y, x, :] = color

    if dx >= dy:
        error = dx // 2
        y = y0
        for x in range(x0, x1 + step_x, step_x):
            mark(y, x)
            error -= dy
            if error < 0:
                y += step_y
                error += dx
    else:
        error = dy // 2
        x = x0
        for y in range(y0, y1 + step_y, step_y):
            mark(y, x)
            error -= dx
            if error < 0:
                x += step_x
                error += dy


def paths_as_lists(paths: Iterable[np.ndarray]) -> list[list[tuple[float, float]]]:
    return [[(float(point[0]), float(point[1])) for point in path] for path in paths]
