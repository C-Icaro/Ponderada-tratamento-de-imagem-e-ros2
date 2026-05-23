# Turtle Draw Dog

Ponderada de Robotica e Visao Computacional com ROS 2. O projeto le uma imagem de um cachorro, extrai contornos com uma pipeline de visao computacional implementada em NumPy e faz a tartaruga do `turtlesim` desenhar o resultado.

Este repositorio ja e a raiz do workspace ROS 2.

## Video explicativo

O video explicativo da ponderada esta disponivel no Google Drive:
[pasta do video](https://drive.google.com/drive/folders/1yftGnDimFqZ7LHwQjKPfBi88MUNSUe0v?usp=drive_link).

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
ros2 launch turtle_draw_dog turtle_draw.launch.py max_points:=1800 target_width:=230 stroke_speed:=4.0
```

## Visualizar apenas a pipeline

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_draw_dog
source install/setup.bash
ros2 run turtle_draw_dog preview_pipeline --output pipeline_debug --max-points 1800 --target-width 230
```

As imagens de debug aparecem em `pipeline_debug`.

## Somente contorno externo

Para desenhar apenas a silhueta do cachorro, sem olhos, focinho ou rugas internas:

```bash
ros2 launch turtle_draw_dog turtle_draw.launch.py external_only:=true max_points:=700 target_width:=230 stroke_speed:=4.0
```

Para conferir a imagem gerada antes de abrir o `turtlesim`:

```bash
ros2 run turtle_draw_dog preview_pipeline --output pipeline_debug_outline --external-only --max-points 700 --target-width 230
```

## Script auxiliar para Windows

Se a janela do `turtlesim` ficar presa no WSLg, rode pelo PowerShell a partir da raiz do repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_turtle_draw.ps1
```

Para rodar a versao apenas com contorno externo:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_turtle_draw.ps1 -ExternalOnly
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
- A documentacao tecnica da pipeline esta em `src/turtle_draw_dog/docs/RELATORIO.md`.
