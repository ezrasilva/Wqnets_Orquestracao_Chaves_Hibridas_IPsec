# Metodologia Experimental

Este documento descreve o protocolo metodologico adotado para avaliar a arquitetura SDKM em cenarios QKD+PQC.

## 1. Perguntas de pesquisa

- RQ1: Qual o trade-off entre frequencia de rotacao de chaves e volume de exposicao de trafego?
- RQ2: Como diferentes taxas QKD impactam sustentabilidade, desempenho e latencia de rekey?
- RQ3: A arquitetura e agnostica ao algoritmo PQC no nivel de sistema?
- RQ4: Qual o custo intrinseco dos KEMs em isolamento criptografico?

## 2. Desenho experimental

A avaliacao e dividida em quatro blocos:

1. Experimento 1 (microbenchmark KEM): mede custo intrinseco de encaps/decaps por algoritmo.
2. Experimento 2 (sensibilidade QKD): varia taxa de entropia QKD e intervalo de rotacao.
3. Bateria A (trade-off): varia apenas o intervalo de rotacao T_r.
4. Bateria B (agilidade): varia apenas o algoritmo PQC de hibridizacao.

Principios metodologicos:
- Variacao univariada por bloco para isolar efeitos.
- Repeticao por cenario para estimar tendencia central e dispersao.
- Controle de condicao de rede via perfis pre-definidos.
- Coleta padronizada de throughput, rekey, CPU e memoria.

## 3. Variaveis

## 3.1 Variaveis independentes

- Experimento 1: algoritmo KEM.
- Experimento 2: taxa QKD e T_r.
- Bateria A: T_r (2, 5, 10, 15, 30, 60 s).
- Bateria B: PQC_ALGO.

## 3.2 Variaveis dependentes

- Throughput medio (Mbps).
- Latencia de rekey ponta a ponta (ms).
- CPU e memoria dos componentes.
- Consumo de entropia QKD (bits/s).
- Sustentabilidade (consumo <= taxa QKD).
- Janela/volume de exposicao por chave (trade-off).
- Overhead de hibridizacao (agilidade).

## 4. Metricas derivadas

- Consumo de entropia: consumo = k_bits / T_r.
- Criterio de sustentabilidade: consumo <= R_qkd.
- Janela efetiva: W_e = T_r + L_rekey_medio (quando latencia disponivel).
- Volume exposto: V_e = Throughput * W_e.

## 5. Coleta e instrumentacao

- Throughput via iperf3 em JSON por iteracao.
- Eventos SDN/rekey via sdn_metrics.csv.
- Recursos (CPU/memoria) via docker stats em resource_metrics.csv.
- Analise por scripts Python gerando CSV de resumo e JSON detalhado.

## 6. Tratamento estatistico

Para cada metrica por cenario:
- n (numero de observacoes)
- media
- desvio padrao
- erro padrao
- IC95 (1.96 * erro_padrao)
- minimo e maximo

## 7. Controle de validade

- Mesma base de software para todos os cenarios.
- Perfil de rede explicitamente declarado em cada execucao.
- Parametros de experimento versionados e documentados.
- Validacao automatica de artefatos por scripts/validate_outputs.py.

## 8. Ameacas a validade

- Dependencia de infraestrutura externa QKD (latencia/estabilidade).
- Variabilidade residual de recursos do host Docker.
- Mudancas de versao de bibliotecas/containers sem congelamento estrito.

Mitigacoes:
- Relatar versoes de ambiente.
- Executar repeticoes por cenario.
- Preservar artefatos brutos e analisados no repositorio.
