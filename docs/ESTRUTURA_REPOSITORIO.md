# Estrutura do Repositorio

Mapa dos principais componentes para facilitar auditoria tecnica e revisao por pares.

## 1. Orquestracao de experimentos

- automation_controller_tradeoff.py: bateria A (intervalo de rotacao).
- automation_controller_qkd_sensitivity.py: experimento 2 (taxa QKD x T_r).
- automation_controller_agility.py: bateria B (variacao de algoritmo PQC).

## 2. Analise de dados

- analisar_tradeoff_variaveis.py
- analisar_sensibilidade_qkd.py
- analisar_agility.py

Cada script gera:
- CSV de resumo (pronto para tabela/figura)
- JSON detalhado (rastreabilidade)

## 3. Visualizacao

- plot_graphics_article_tradeoff.py
- plot_fig_and_table_agility.py
- plot_experimentos_qkd_pqc.py

## 4. Scripts de suporte

- scripts/sdn_controller_multi_node.py: controlador SDN.
- scripts/simulate_network_conditions.py: injecao de perfis de rede.
- scripts/microbenchmark_kems.py: benchmark isolado de KEM.
- scripts/validate_outputs.py: validacao de consistencia de artefatos.

## 5. Artefatos de saida

- teste_tradeoff/: resultados brutos por intervalo.
- teste_sensibilidade_qkd/: resultados brutos por cenario QKD.
- teste_agility/: resultados brutos por algoritmo.
- teste_kem/: resultados brutos do microbenchmark.

- out_tradeoff/: agregados para o trade-off.
- out_sensibilidade_qkd/: agregados de sensibilidade QKD.
- out_agilidade/: agregados da bateria de agilidade.

- figs_tradeoff/: figuras do trade-off.
- figs_experimentos/: figuras de sensibilidade/agilidade/benchmark.

## 6. Infraestrutura

- Dockerfile: ambiente base dos containers.
- docker-compose.yml: ambiente principal dos experimentos.
- docker-compose-kem.yml: ambiente dedicado ao microbenchmark KEM.

## 7. Documentacao e governanca

- README.md: entrada principal e comandos.
- docs/METODOLOGIA_EXPERIMENTAL.md: protocolo cientifico.
- docs/REPRODUTIBILIDADE.md: roteiro de replicacao.
- CONTRIBUTING.md: padroes de contribuicao.
- CITATION.cff: metadados de citacao.
