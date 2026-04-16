# Reprodutibilidade

Guia operacional para reproduzir os resultados do artigo sem Makefile, usando apenas comandos Python e Docker.

## 1. Ambiente minimo

- Linux
- Docker Engine + Docker Compose v2
- Python 3.10+ no host

## 1.1 Ambiente de execucao dos testes reportados

As simulacoes reportadas no artigo foram executadas no seguinte ambiente:
- SO: Debian GNU/Linux 12 (bookworm) x86_64
- Kernel: 6.1.0-37-amd64
- CPU: AMD Ryzen 7 3800X (16 cores) @ 4.200GHz
- GPU: NVIDIA GeForce RTX 2070 SUPER
- Memoria: 16GB
- Shell: bash 5.2.15

## 2. Preparacao

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 3. Ordem recomendada de execucao

1. Experimento 1 (microbenchmark KEM)
2. Experimento 2 (sensibilidade QKD)
3. Bateria A (trade-off)
4. Bateria B (agilidade)
5. Analises e plots
6. Validacao de artefatos

## 4. Comandos de reproducao

## 4.1 Experimento 1

```bash
docker compose -f docker-compose-kem.yml up --build -d
docker exec -it test_kem python3 /workspace/scripts/microbenchmark_kems.py --iterations 100 --out-dir /workspace/teste_kem
docker compose -f docker-compose-kem.yml down
```

## 4.2 Experimento 2

```bash
python3 automation_controller_qkd_sensitivity.py --duration 60 --iterations 1 --profile wan-fiber
python3 analisar_sensibilidade_qkd.py --base-dir teste_sensibilidade_qkd --out-dir out_sensibilidade_qkd
```

## 4.3 Bateria A

```bash
python3 automation_controller_tradeoff.py --duration 60 --iterations 1 --profile wan-fiber
python3 analisar_tradeoff_variaveis.py --base-dir teste_tradeoff --out-dir out_tradeoff --k-bits 256 --r-qkd 1000
```

## 4.4 Bateria B

```bash
python3 automation_controller_agility.py --duration 60 --iterations 1 --profile wan-fiber
python3 analisar_agility.py --base-dir teste_agility --out-dir out_agilidade
```

## 4.5 Gera figuras e tabelas

```bash
python3 plot_graphics_article_tradeoff.py --csv out_tradeoff/tradeoff_variaveis_resumo.csv --out-dir figs_tradeoff
python3 plot_fig_and_table_agility.py --csv out_agilidade/agilidade_variaveis_resumo.csv --out-dir figs_experimentos
python3 plot_experimentos_qkd_pqc.py --sens-csv out_sensibilidade_qkd/sensibilidade_variaveis_resumo.csv --kem-csv teste_kem/kem_microbenchmark_resumo.csv --out-dir figs_experimentos
```

## 5. Checklist de reproducao

- Scripts executaram sem erro.
- Pastas teste_* contem artefatos brutos por cenario.
- Pastas out_* contem arquivos resumo/detalhado.
- Pastas figs_* contem figuras esperadas.
- scripts/validate_outputs.py retorna status OK ou apenas alertas nao criticos.

## 6. Validacao automatica

```bash
python3 scripts/validate_outputs.py
```

Modo estrito:

```bash
python3 scripts/validate_outputs.py --strict
```

## 7. Registro para submissao

Ao preparar material para revisao:
- Preservar arquivos CSV/JSON de saida.
- Informar parametros usados (duration, iterations, profile).
- Registrar hash do commit correspondente aos resultados.
