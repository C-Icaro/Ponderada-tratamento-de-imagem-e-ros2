# Turtle Draw Dog - Ponderada ROS 2

Pacote ROS 2 em Python que le uma imagem, extrai contornos com uma pipeline de visao computacional implementada com NumPy e faz a tartaruga do `turtlesim` desenhar esses contornos.

Imagem usada por padrao: `assets/dog.png`.

## Video explicativo

O video explicativo da ponderada esta disponivel no Google Drive:
[pasta do video](https://drive.google.com/drive/folders/1yftGnDimFqZ7LHwQjKPfBi88MUNSUe0v?usp=drive_link).

## Requisitos

- ROS 2 Jazzy
- `turtlesim`
- Python 3 com `numpy`, `opencv-python`/`python3-opencv` e `matplotlib`

No ambiente WSL configurado para esta ponderada, o ROS 2 Jazzy ja esta instalado.

## Como buildar

No Windows PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Dentro do Ubuntu, entre na raiz do repositorio:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_draw_dog
source install/setup.bash
```

Se voce adicionou ou trocou a imagem depois de ja ter buildado, rode o build novamente:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_draw_dog
source install/setup.bash
```

## Como visualizar a pipeline

Este comando roda apenas o processamento da imagem e salva imagens intermediarias:

```bash
ros2 run turtle_draw_dog preview_pipeline --output pipeline_debug --max-points 1800 --target-width 230
```

Saidas esperadas:

- `pipeline_debug/01_preprocessed_gray.png`
- `pipeline_debug/02_edges.png`
- `pipeline_debug/03_paths_preview.png`

Se o comando acima falhar com `Package 'turtle_draw_dog' not found` ou `No executable found`, o terminal ainda nao esta com o workspace carregado. Rode:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 pkg executables turtle_draw_dog
```

O resultado deve listar:

```text
turtle_draw_dog draw_dog
turtle_draw_dog preview_pipeline
```

Se falhar com erro de imagem, confirme que ela existe no pacote:

```bash
ls src/turtle_draw_dog/assets/dog.png
ls install/turtle_draw_dog/share/turtle_draw_dog/assets/dog.png
```

## Como desenhar no turtlesim

```bash
ros2 launch turtle_draw_dog turtle_draw.launch.py
```

O launch desenha por `/turtle1/cmd_vel`, entao a tartaruga anda de verdade e o rastro aparece progressivamente. Entre segmentos desconectados ela reposiciona com a caneta desligada. Para uma demonstracao com contornos mais definidos:

```bash
ros2 launch turtle_draw_dog turtle_draw.launch.py max_points:=1800 target_width:=230 stroke_speed:=4.0
```

Para gravar um video mais rapido, reduza os pontos:

```bash
ros2 launch turtle_draw_dog turtle_draw.launch.py target_width:=160 max_points:=350 stroke_speed:=4.5 min_segment_time:=0.018
```

Para desenhar somente o contorno externo do cachorro:

```bash
ros2 launch turtle_draw_dog turtle_draw.launch.py external_only:=true max_points:=700 target_width:=230 stroke_speed:=4.0
```

Para gerar a previa desse modo:

```bash
ros2 run turtle_draw_dog preview_pipeline --output pipeline_debug_outline --external-only --max-points 700 --target-width 230
```

## Se a janela do TurtleSim nao abrir

As vezes o WSLg mostra o `TurtleSim` na barra de tarefas, mas a janela fica presa/minimizada em modo `[WARN:COPY MODE]`. Primeiro feche qualquer janela antiga do TurtleSim. Depois, no PowerShell do Windows, rode o script auxiliar que fica na raiz deste projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_turtle_draw.ps1
```

Se ainda aparecer so a miniatura na barra de tarefas, use `Alt+Tab` e selecione `TurtleSim (Ubuntu-24.04)`. Se o titulo mostrar `[WARN:COPY MODE]`, pressione `Esc` e tente clicar na janela de novo.

Para usar outra imagem:

```bash
ros2 launch turtle_draw_dog turtle_draw.launch.py image_path:=dog.png
```

## Estrutura

```text
turtle_draw_dog/
  assets/dog.png
  launch/turtle_draw.launch.py
  turtle_draw_dog/image_pipeline.py
  turtle_draw_dog/draw_dog.py
  turtle_draw_dog/preview_pipeline.py
  docs/RELATORIO.md
```

## O que foi implementado do zero

- Conversao RGB para escala de cinza.
- Recorte automatico do objeto principal por componentes conectados.
- Redimensionamento bilinear.
- Normalizacao por percentis.
- Convolucao 2D.
- Filtro Gaussiano.
- Gradientes Sobel.
- Supressao nao maxima.
- Limiarizacao por histerese.
- Componentes conectados de bordas.
- Ordenacao e simplificacao dos caminhos.
- Mapeamento dos pontos da imagem para o espaco do `turtlesim`.
- Modo `external_only` para desenhar apenas a silhueta externa.

O OpenCV e usado apenas para carregar a imagem, conforme permitido no enunciado.
