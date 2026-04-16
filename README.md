# Wqnets - Orquestração de Chaves Híbridas para Túneis IPsec

Uma plataforma experimental para avaliar orquestração de chaves híbridas (QKD + PQC) em túneis VPN IPsec sob diferentes cenários de rede e políticas de rotação.

## Visão Geral

Este repositório implementa um ambiente de experimentação com containers Docker, controlador SDN e automações em Python para medir o impacto de variáveis de segurança e desempenho em túneis IPsec.

O fluxo integra:
- geração e distribuição de material criptográfico híbrido,
- rekey controlado por orquestrador,
- testes de throughput com iperf3,
- coleta de métricas de latência de rekey, consumo de entropia, CPU/memória,
- análise estatística e geração de figuras para artigo.

### Contexto

Este trabalho foi desenvolvido como base experimental para o artigo:
**"orquestração de chaves hibridas para tuneis IPsec"**

O objetivo é demonstrar, com evidência quantitativa, como a arquitetura se comporta em quatro frentes: custo criptográfico intrínseco, sensibilidade à taxa QKD, trade-off entre segurança e consumo de entropia, e agilidade criptográfica entre algoritmos PQC.

## Características Principais

- **Orquestração de chaves híbridas**: combinação de material QKD e PQC para atualização de SAs IPsec.
- **Automação ponta a ponta**: setup, execução, coleta e teardown dos cenários experimentais.
- **Perfis de rede realistas**: simulação de latência, jitter, perda e limitação de banda.
- **Bateria de experimentos reproduzível**: scripts dedicados para execução e análise.
- **Pipeline de publicação**: geração de CSV/JSON consolidados e gráficos prontos para artigo.

## Estrutura do Projeto

```text
.
├── docker-compose.yml                     # Ambiente principal (alice, bob, orchestrator)
├── docker-compose-kem.yml                 # Ambiente para microbenchmark KEM
├── Dockerfile                             # Imagem base com strongSwan, iperf3, liboqs
├── automation_controller_tradeoff.py      # Bateria A: trade-off por intervalo de rotação
├── automation_controller_qkd_sensitivity.py # Experimento 2: sensibilidade à taxa QKD
├── automation_controller_agility.py       # Bateria B: agilidade criptográfica
├── analisar_tradeoff_variaveis.py         # Análise estatística do trade-off
├── analisar_sensibilidade_qkd.py          # Análise da sensibilidade QKD
├── analisar_agility.py                    # Análise da agilidade
├── plot_graphics_article_tradeoff.py      # Gráficos do trade-off
├── plot_fig_and_table_agility.py          # Figura/tabela da agilidade
├── plot_experimentos_qkd_pqc.py           # Figuras de QKD + microbenchmark
├── scripts/
│   ├── sdn_controller_multi_node.py       # Controlador SDN/orquestrador
│   ├── hybrid_key_gen.py                  # Geração de chaves híbridas
│   ├── simulate_network_conditions.py      # Perfis de rede com tc
│   ├── microbenchmark_kems.py             # Experimento 1 (KEM isolado)
│   └── validate_outputs.py                # Validação de artefatos
├── teste_kem/                             # Saídas brutas Exp. 1
├── teste_sensibilidade_qkd/               # Saídas brutas Exp. 2
├── teste_tradeoff/                        # Saídas brutas Bateria A
├── teste_agility/                         # Saídas brutas Bateria B
├── out_sensibilidade_qkd/                 # Saídas analisadas Exp. 2
├── out_tradeoff/                          # Saídas analisadas Bateria A
├── out_agilidade/                         # Saídas analisadas Bateria B
└── figs_tradeoff/ e figs_experimentos/    # Figuras finais
```

## Experimentos

O projeto inclui quatro blocos principais:

1. **Exp1 - Microbenchmark KEM**: custo intrínseco de encaps/decaps por algoritmo.
2. **Exp2 - Sensibilidade QKD**: impacto de taxas QKD diferentes em throughput e sustentabilidade.
3. **Bateria A - Trade-off**: variação de intervalo de rotação para medir exposição versus consumo.
4. **Bateria B - Agilidade**: variação do algoritmo PQC para avaliar neutralidade da arquitetura.

### Métricas Coletadas

- **Throughput (Mbps)**: desempenho de túnel sob tráfego de teste.
- **Latência de Rekey (ms)**: custo temporal da atualização de chaves.
- **Consumo de Entropia QKD (bits/s)**: demanda de entropia por política de rotação.
- **Sustentabilidade**: verificação de consumo <= taxa QKD disponível.
- **CPU e Memória**: custo operacional dos componentes (alice, bob, orchestrator).
- **Volume de Exposição por Chave**: proxy de risco associado ao intervalo de rotação.

## Como Usar

### Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### Executar Experimentos

```bash
# Exp1 - Microbenchmark KEM
docker compose -f docker-compose-kem.yml up --build -d
docker exec -it test_kem python3 /workspace/scripts/microbenchmark_kems.py --iterations 100 --out-dir /workspace/teste_kem
docker compose -f docker-compose-kem.yml down

# Exp2 - Sensibilidade QKD
python3 automation_controller_qkd_sensitivity.py --duration 60 --iterations 1 --profile wan-fiber
python3 analisar_sensibilidade_qkd.py --base-dir teste_sensibilidade_qkd --out-dir out_sensibilidade_qkd

# Bateria A - Trade-off
python3 automation_controller_tradeoff.py --duration 60 --iterations 1 --profile wan-fiber
python3 analisar_tradeoff_variaveis.py --base-dir teste_tradeoff --out-dir out_tradeoff --k-bits 256 --r-qkd 1000

# Bateria B - Agilidade
python3 automation_controller_agility.py --duration 60 --iterations 1 --profile wan-fiber
python3 analisar_agility.py --base-dir teste_agility --out-dir out_agilidade
```

Os resultados são salvos nas pastas `teste_*` (brutos) e `out_*` (analisados).

### Gerar Gráficos

```bash
python3 plot_graphics_article_tradeoff.py --csv out_tradeoff/tradeoff_variaveis_resumo.csv --out-dir figs_tradeoff
python3 plot_fig_and_table_agility.py --csv out_agilidade/agilidade_variaveis_resumo.csv --out-dir figs_experimentos
python3 plot_experimentos_qkd_pqc.py --sens-csv out_sensibilidade_qkd/sensibilidade_variaveis_resumo.csv --kem-csv teste_kem/kem_microbenchmark_resumo.csv --out-dir figs_experimentos
```

## Dependências

- `pandas`: consolidação e análise de métricas experimentais.
- `matplotlib`: geração de gráficos para artigo.
- Docker e Docker Compose v2: execução do ambiente de testes com IPsec e orquestrador.

## Ambiente de Simulação

As simulações foram executadas em um ambiente com as seguintes especificações:

- **SO**: Debian GNU/Linux 12 (bookworm) x86_64
- **Kernel**: 6.1.0-37-amd64
- **CPU**: AMD Ryzen 7 3800X (16 cores) @ 4.200GHz
- **GPU**: NVIDIA GeForce RTX 2070 SUPER
- **Memória**: 16GB
- **Shell**: bash 5.2.15
