from __future__ import annotations

import argparse
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from turtle_draw_dog.image_pipeline import build_vision_paths, save_debug_images


def default_image_path() -> Path:
    share_dir = Path(get_package_share_directory("turtle_draw_dog"))
    return share_dir / "assets" / "dog.png"


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa apenas a pipeline de visao e salva imagens de debug.")
    parser.add_argument("--image", type=Path, default=default_image_path())
    parser.add_argument("--output", type=Path, default=Path("pipeline_debug"))
    parser.add_argument("--target-width", type=int, default=230)
    parser.add_argument("--max-points", type=int, default=1800)
    parser.add_argument("--external-only", action="store_true")
    args = parser.parse_args()

    result = build_vision_paths(
        image_path=args.image,
        target_width=args.target_width,
        max_points=args.max_points,
        external_only=args.external_only,
    )
    save_debug_images(result, args.output)

    print(f"Imagem original: {result.original_shape}")
    print(f"Recorte usado: {result.crop_box}")
    print(f"Imagem de trabalho: {result.work_image.shape}")
    print(f"Pixels de borda: {int(result.edge_map.sum())}")
    print(f"Caminhos: {len(result.paths_turtlesim)}")
    print(f"Pontos enviados ao turtlesim: {result.total_points}")
    print(f"Apenas contorno externo: {args.external_only}")
    print(f"Debug salvo em: {args.output.resolve()}")


if __name__ == "__main__":
    main()
