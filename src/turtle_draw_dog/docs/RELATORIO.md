# Documentacao tecnica - Turtle Draw Dog

## Objetivo

O objetivo do projeto foi transformar uma imagem de um cachorro em trajetorias para o `turtlesim`, usando ROS 2. A solucao foi dividida em duas partes: uma pipeline de visao computacional extrai linhas da imagem, e um no ROS 2 envia comandos para a tartaruga desenhar essas linhas. O sistema permite dois modos: desenho detalhado, com linhas internas, e `external_only`, com apenas a silhueta.

## Decisoes de implementacao da pipeline

### 1. Carregamento e conversao para cinza

A imagem e carregada com OpenCV apenas para leitura do arquivo. Depois disso, o processamento foi feito com NumPy para deixar claro o funcionamento da pipeline. A primeira transformacao converte RGB para escala de cinza com `0.299 R + 0.587 G + 0.114 B`, reduzindo o problema para uma matriz 2D.

### 2. Recorte automatico do cachorro

Como a foto tem muito fundo claro, a pipeline localiza o cachorro antes de detectar bordas. Pixels escuros criam uma mascara inicial, e componentes conectados com vizinhanca 8 identificam as maiores regioes. A partir delas, e calculada uma caixa de recorte com margem. Isso evita que a tartaruga desperdice tempo desenhando parede, chao ou ruido.

### 3. Redimensionamento e normalizacao

Depois do recorte, a imagem e redimensionada por interpolacao bilinear. O parametro `target_width` controla esse tamanho: valores maiores preservam mais detalhe, mas deixam o desenho mais lento. Em seguida, a imagem e normalizada por percentis para aumentar contraste sem depender de valores fixos de iluminacao.

### 4. Suavizacao e deteccao de bordas

Para o desenho detalhado, a pipeline aplica um filtro Gaussiano por convolucao 2D para reduzir ruido. Depois, usa Sobel para encontrar mudancas fortes de intensidade. A supressao nao maxima afina as bordas, mantendo apenas maximos locais, e a histerese preserva bordas fracas somente quando conectadas a bordas fortes.

### 5. Modo somente contorno externo

O modo `external_only` gera uma versao limpa, apenas com a silhueta. Nesse modo, a pipeline nao usa bordas internas do Sobel. Ela reaproveita a mascara do cachorro, preenche buracos internos e extrai somente a fronteira externa. Assim, olhos, focinho e rugas nao aparecem.

### 6. Conversao de bordas em caminhos

Depois de gerar o mapa de bordas, cada componente conectado vira uma lista ordenada de pontos. O algoritmo escolhe um ponto inicial, percorre vizinhos nao visitados e cria novos caminhos quando uma ramificacao termina. Os caminhos sao simplificados por distancia minima e pelo algoritmo Ramer-Douglas-Peucker. Depois, pequenos vaos entre trechos proximos sao conectados, e segmentos longos sao densificados para virar linhas mais continuas.

O parametro `max_points` limita a quantidade de pontos enviados ao `turtlesim`. No inicio, o limitador mantinha apenas os caminhos mais longos e removia detalhes do rosto. A versao atual distribui melhor os pontos entre caminhos grandes e pequenos.

### 7. Mapeamento para o espaco do turtlesim

Os pontos da imagem sao convertidos para o sistema do `turtlesim`, que vai aproximadamente de 0 a 11. O mapeamento preserva proporcao, centraliza o cachorro e inverte o eixo vertical, pois imagens crescem para baixo e o plano do `turtlesim` cresce para cima.

## Controle com ROS 2

O no `draw_dog` executa a pipeline, recebe os caminhos e desenha cada segmento no `turtlesim`. O movimento usa `/turtle1/cmd_vel`, entao a tartaruga anda de verdade e o rastro aparece progressivamente. Os servicos `/clear`, `/turtle1/set_pen` e `/turtle1/teleport_absolute` limpam a tela, controlam a caneta e reposicionam a tartaruga.

Entre segmentos desconectados, a tartaruga e teleportada com a caneta desligada para evitar linhas falsas. Em segmentos reais, ela liga a caneta, anda ate o final e so depois desliga a caneta. Essa ordem foi ajustada para evitar pequenas falhas no rastro.

O launch file inicia o `turtlesim_node` e o no de desenho. Parametros como `target_width`, `max_points`, `stroke_speed` e `external_only` permitem controlar qualidade, velocidade e estilo do resultado.

## Evolucao da solucao

A primeira versao gerava pontos de borda, mas a visualizacao parecia pontilhada. Depois, a previa passou a renderizar os caminhos como linhas. Em seguida, a qualidade foi aumentada: a simplificacao ficou menos agressiva, pequenos vaos passaram a ser conectados e o limite de pontos foi elevado. Por fim, foi criada a versao de contorno externo para atender a necessidade de uma silhueta simples.

Tambem houve ajustes de execucao no Windows/WSL. O script `run_turtle_draw.ps1` roda o launch a partir da raiz do repositorio usando caminhos relativos ao projeto e aceita `-ExternalOnly` para iniciar diretamente a versao de silhueta.

## Dificuldades encontradas

A maior dificuldade foi equilibrar detalhe visual e tempo de desenho. Muitos pontos deixam o cachorro mais fiel, mas tornam o `turtlesim` lento. Poucos pontos deixam o desenho rapido, mas removem curvas importantes. Outra dificuldade foi transformar pixels soltos em caminhos ordenados, porque uma borda de imagem nao vem naturalmente como uma linha pronta.

Tambem houve desafios com a visualizacao no WSLg. Em alguns momentos, a janela do `turtlesim` abria minimizada ou presa em modo de copia. Por isso, o README e o script auxiliar foram ajustados para facilitar a execucao.

No final, a solucao ficou dividida de forma clara: a pipeline transforma imagem em trajetorias, e o no ROS 2 apenas executa essas trajetorias no `turtlesim`. Essa separacao facilita testar a visao computacional com `preview_pipeline` antes de rodar o desenho real.
