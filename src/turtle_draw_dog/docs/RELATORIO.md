# Relatorio tecnico - Turtle Draw Dog

## Objetivo

O objetivo foi transformar a imagem `dog.png` em trajetorias para o `turtlesim`. A solucao foi separada em duas partes: uma pipeline de visao computacional em NumPy, responsavel por extrair os contornos, e um no ROS 2, responsavel por enviar os movimentos para a tartaruga.

## Pipeline de visao computacional

A imagem e carregada com OpenCV, unica etapa em que a biblioteca e usada. Depois disso, todo o processamento e feito com NumPy. A imagem RGB e convertida para escala de cinza pela combinacao ponderada dos canais: `0.299 R + 0.587 G + 0.114 B`. Essa escolha aproxima a percepcao humana de luminancia e reduz o problema para uma matriz 2D.

Antes da deteccao de bordas, a pipeline faz um recorte automatico do objeto principal. Como o cachorro e escuro em um fundo claro, e criada uma mascara de baixa intensidade. Em seguida, componentes conectados sao calculados do zero com busca em profundidade sobre vizinhanca 8. Os maiores componentes formam a caixa de recorte, com margem. Esse passo evita que a tartaruga desenhe partes vazias da parede ou do chao.

Depois do recorte, a imagem e redimensionada por interpolacao bilinear para reduzir a quantidade de pontos. A normalizacao usa percentis para aumentar contraste sem depender de valores fixos absolutos. Em seguida, aplica-se um filtro Gaussiano implementado por convolucao 2D manual para reduzir ruido antes do calculo dos gradientes.

A deteccao de bordas usa operadores Sobel implementados por convolucao. O modulo do gradiente indica a intensidade da borda, e o angulo indica a direcao local. Para afinar as bordas, foi implementada supressao nao maxima: cada pixel so permanece se for maximo local na direcao do gradiente. Por fim, a limiarizacao por histerese separa bordas fortes e fracas; bordas fracas so sao mantidas quando conectadas a uma borda forte. Isso reduz ruido sem quebrar demais os contornos relevantes.

## Planejamento de caminho

O mapa binario de bordas e convertido em componentes conectados. Cada componente e percorrido por uma estrategia de rastreamento local: a pipeline escolhe um ponto inicial, avanca por vizinhos ainda nao visitados e cria um novo segmento quando um ramo termina. Depois, os caminhos sao simplificados por distancia minima entre pontos e pelo algoritmo Ramer-Douglas-Peucker, tambem implementado no projeto. Essa simplificacao e importante porque o `turtlesim` nao precisa receber todos os pixels da borda.

Os pontos da imagem sao mapeados para o espaco do `turtlesim`, que vai aproximadamente de 0 a 11 nos eixos `x` e `y`. O mapeamento preserva a proporcao do desenho, centraliza os contornos na tela e inverte o eixo vertical, pois imagens crescem para baixo enquanto o plano cartesiano do `turtlesim` cresce para cima.

## Controle ROS 2

O pacote `turtle_draw_dog` possui o no `draw_dog`. Ele chama a pipeline, recebe uma lista de caminhos e controla a tartaruga com `/turtle1/cmd_vel`, fazendo a tartaruga andar de verdade sobre cada segmento. Os servicos `/clear`, `/turtle1/set_pen` e `/turtle1/teleport_absolute` tambem sao usados: o teleporte reposiciona a tartaruga com a caneta desligada entre segmentos desconectados, evitando linhas falsas; o desenho em si e feito com velocidade linear, o que torna o rastro visivel na janela do `turtlesim`.

O launch file inicia o `turtlesim_node` com fundo claro e depois executa o no de desenho. Os parametros `target_width`, `max_points` e `draw_delay` permitem controlar o nivel de detalhe e a velocidade do desenho.

## Dificuldades encontradas

A principal dificuldade foi equilibrar detalhe visual e quantidade de comandos para o `turtlesim`. Uma borda pixel a pixel gera muitos pontos e torna o desenho lento. Por isso, foram adicionadas etapas de recorte, redimensionamento, supressao nao maxima e simplificacao de caminhos. Outra dificuldade foi evitar bibliotecas prontas de visao computacional; por isso, convolucao, componentes conectados, histerese e simplificacao foram implementados manualmente.
