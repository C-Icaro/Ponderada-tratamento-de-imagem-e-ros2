# Turtle Draw Dog

Ponderada de Robotica e Visao Computacional com ROS 2. O projeto le uma imagem de um cachorro, extrai contornos com uma pipeline de visao computacional implementada em NumPy e faz a tartaruga do `turtlesim` desenhar o resultado.

Este repositorio ja e a raiz do workspace ROS 2.

## Execucao rapida

Entre no WSL:

```powershell
wsl -d Ubuntu-24.04
```

Na raiz do repositorio:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_draw_dog
source install/setup.bash
ros2 launch turtle_draw_dog turtle_draw.launch.py max_points:=180 target_width:=130 stroke_speed:=4.5
```

## Visualizar apenas a pipeline

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_draw_dog
source install/setup.bash
ros2 run turtle_draw_dog preview_pipeline --output pipeline_debug
```

As imagens de debug aparecem em `pipeline_debug`.

## Script auxiliar para Windows

Se a janela do `turtlesim` ficar presa no WSLg, rode pelo PowerShell a partir da raiz do repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_turtle_draw.ps1
```

## Estrutura

```text
.
|-- src/
|   `-- turtle_draw_dog/
|       |-- assets/dog.png
|       |-- docs/RELATORIO.md
|       |-- launch/turtle_draw.launch.py
|       |-- turtle_draw_dog/
|       |   |-- draw_dog.py
|       |   |-- image_pipeline.py
|       |   `-- preview_pipeline.py
|       `-- README.md
|-- dog.png
`-- run_turtle_draw.ps1
```

## Observacoes

- OpenCV e usado apenas para carregar a imagem.
- A pipeline de visao usa NumPy para o processamento.
- `build/`, `install/`, `log/` e imagens de debug nao devem ser versionados.
- Mais detalhes estao em `src/turtle_draw_dog/README.md`.
