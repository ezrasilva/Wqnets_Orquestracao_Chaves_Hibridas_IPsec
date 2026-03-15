#!/usr/bin/env python3
"""
Gera ATÉ 3 gráficos (Bateria A + Bateria B) a partir dos CSVs de resumo.

Entradas esperadas:
- Bateria A: summary_by_interval.csv (gerado pelo seu pipeline)
  Colunas mínimas:
    Tr_s, Ve_mean_megabits, orchestrator_cpu_mean_pct
    (opcionais) throughput_mean_mbps, throughput_ci95_mbps

- Bateria B: summary_by_algorithm.csv
  Colunas mínimas:
    algorithm, overhead_mean_ms
    (opcionais) overhead_sd_ms, throughput_mean_mbps, throughput_ci95_mbps

Saídas:
- fig1_tradeoff_cpu_vs_ve.png   (Figura 1)
- fig2_latency_by_algorithm.png (Figura 2)
- fig3_throughput.png           (Figura 3)  [opcional: A, B, ou ambos]

Uso:
  python make_figures_results.py \
    --a ./out_tradeoff/summary_by_interval.csv \
    --b ./out_agility/summary_by_algorithm.csv \
    --out ./figs_final \
    --fig3 both

Opções fig3:
  --fig3 none | A | B | both
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def _save(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()


def fig1_tradeoff_dual_axis(df_a: pd.DataFrame, out_dir: Path) -> None:
    req = {"Tr_s", "Ve_mean_megabits", "orchestrator_cpu_mean_pct"}
    miss = req - set(df_a.columns)
    if miss:
        raise ValueError(f"Figura 1: faltam colunas em Bateria A: {miss}")

    df_a = df_a.sort_values("Tr_s").reset_index(drop=True)
    x = df_a["Tr_s"].astype(float).to_list()
    ve = df_a["Ve_mean_megabits"].astype(float).to_list()
    cpu = df_a["orchestrator_cpu_mean_pct"].astype(float).to_list()

    fig, ax1 = plt.subplots()
    ax1.set_xlabel(r"Intervalo de rotação $T_r$ (s)")
    ax1.set_ylabel("CPU do controlador (%)")
    ax1.plot(x, cpu, marker="o")

    ax2 = ax1.twinx()
    ax2.set_ylabel(r"Exposição por instância $V_e$ (Mb)")
    ax2.plot(x, ve, marker="s")

    ax1.set_title("Trade-off: custo computacional vs exposição")
    _save(out_dir / "fig1_tradeoff_cpu_vs_ve.png")


def fig2_latency_by_algorithm(df_b: pd.DataFrame, out_dir: Path) -> None:
    req = {"algorithm", "overhead_mean_ms"}
    miss = req - set(df_b.columns)
    if miss:
        raise ValueError(f"Figura 2: faltam colunas em Bateria B: {miss}")

    df_b = df_b.copy()
    # Ordena do menor overhead para o maior (mais “visual”)
    df_b = df_b.sort_values("overhead_mean_ms").reset_index(drop=True)

    x = df_b["algorithm"].astype(str).to_list()
    y = df_b["overhead_mean_ms"].astype(float).to_list()

    plt.figure()
    plt.bar(x, y)
    plt.xlabel("Mecanismo pós-quântico")
    plt.ylabel("Latência média (ms)")
    plt.title("Agilidade criptográfica: latência de derivação/rekey por algoritmo")
    plt.xticks(rotation=45, ha="right")
    _save(out_dir / "fig2_latency_by_algorithm.png")


def fig3_throughput_A(df_a: pd.DataFrame, out_dir: Path) -> None:
    req = {"Tr_s", "throughput_mean_mbps"}
    miss = req - set(df_a.columns)
    if miss:
        raise ValueError(f"Figura 3(A): faltam colunas em Bateria A: {miss}")

    df_a = df_a.sort_values("Tr_s").reset_index(drop=True)
    x = df_a["Tr_s"].astype(float).to_list()
    y = df_a["throughput_mean_mbps"].astype(float).to_list()

    plt.figure()
    if "throughput_ci95_mbps" in df_a.columns and df_a["throughput_ci95_mbps"].notna().any():
        yerr = df_a["throughput_ci95_mbps"].astype(float).to_list()
        plt.errorbar(x, y, yerr=yerr, marker="o", capsize=4)
    else:
        plt.plot(x, y, marker="o")

    plt.xlabel(r"Intervalo de rotação $T_r$ (s)")
    plt.ylabel("Throughput médio (Mbps)")
    plt.title("Plano de dados: throughput vs intervalo de rotação")
    _save(out_dir / "fig3_throughput_A.png")


def fig3_throughput_B(df_b: pd.DataFrame, out_dir: Path) -> None:
    req = {"algorithm", "throughput_mean_mbps"}
    miss = req - set(df_b.columns)
    if miss:
        raise ValueError(f"Figura 3(B): faltam colunas em Bateria B: {miss}")

    df_b = df_b.copy().sort_values("algorithm").reset_index(drop=True)
    x = df_b["algorithm"].astype(str).to_list()
    y = df_b["throughput_mean_mbps"].astype(float).to_list()

    plt.figure()
    if "throughput_ci95_mbps" in df_b.columns and df_b["throughput_ci95_mbps"].notna().any():
        yerr = df_b["throughput_ci95_mbps"].astype(float).to_list()
        plt.errorbar(x, y, yerr=yerr, fmt="o", capsize=4)
    else:
        plt.plot(x, y, marker="o")

    plt.xlabel("Mecanismo pós-quântico")
    plt.ylabel("Throughput médio (Mbps)")
    plt.title("Plano de dados: throughput vs mecanismo pós-quântico")
    plt.xticks(rotation=45, ha="right")
    _save(out_dir / "fig3_throughput_B.png")


def fig3_throughput_both(df_a: pd.DataFrame, df_b: pd.DataFrame, out_dir: Path) -> None:
    """
    Uma única figura com duas séries:
    - Série A: throughput vs Tr_s
    - Série B: throughput vs algoritmo (categorias)

    Como os eixos X são diferentes, fazemos 2 subplots? (não pode, você pediu no máximo 3 gráficos,
    mas subplots ainda contam como 1 figura). Se você preferir SEM subplots, use fig3=A ou fig3=B.
    """
    # Para não complicar demais visualmente, usamos 2 subplots DENTRO da mesma figura.
    # Isso conta como 1 figura no artigo.
    req_a = {"Tr_s", "throughput_mean_mbps"}
    req_b = {"algorithm", "throughput_mean_mbps"}
    miss_a = req_a - set(df_a.columns)
    miss_b = req_b - set(df_b.columns)
    if miss_a:
        raise ValueError(f"Figura 3(both): faltam colunas em Bateria A: {miss_a}")
    if miss_b:
        raise ValueError(f"Figura 3(both): faltam colunas em Bateria B: {miss_b}")

    df_a = df_a.sort_values("Tr_s").reset_index(drop=True)
    df_b = df_b.copy().sort_values("algorithm").reset_index(drop=True)

    fig = plt.figure(figsize=(10, 4))

    ax1 = fig.add_subplot(1, 2, 1)
    x1 = df_a["Tr_s"].astype(float).to_list()
    y1 = df_a["throughput_mean_mbps"].astype(float).to_list()
    if "throughput_ci95_mbps" in df_a.columns and df_a["throughput_ci95_mbps"].notna().any():
        yerr1 = df_a["throughput_ci95_mbps"].astype(float).to_list()
        ax1.errorbar(x1, y1, yerr=yerr1, marker="o", capsize=4)
    else:
        ax1.plot(x1, y1, marker="o")
    ax1.set_xlabel(r"$T_r$ (s)")
    ax1.set_ylabel("Throughput (Mbps)")
    ax1.set_title("A: Throughput vs rotação")

    ax2 = fig.add_subplot(1, 2, 2)
    x2 = df_b["algorithm"].astype(str).to_list()
    y2 = df_b["throughput_mean_mbps"].astype(float).to_list()
    if "throughput_ci95_mbps" in df_b.columns and df_b["throughput_ci95_mbps"].notna().any():
        yerr2 = df_b["throughput_ci95_mbps"].astype(float).to_list()
        ax2.errorbar(x2, y2, yerr=yerr2, fmt="o", capsize=4)
    else:
        ax2.plot(x2, y2, marker="o")
    ax2.set_xlabel("Algoritmo")
    ax2.set_title("B: Throughput vs algoritmo")
    ax2.tick_params(axis="x", rotation=45)

    fig.suptitle("Plano de dados: estabilidade do throughput (A e B)")
    _save(out_dir / "fig3_throughput.png")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="summary_by_interval.csv (Bateria A)")
    ap.add_argument("--b", required=True, help="summary_by_algorithm.csv (Bateria B)")
    ap.add_argument("--out", required=True, help="Pasta de saída das figuras")
    ap.add_argument("--fig3", default="both", choices=["none", "A", "B", "both"],
                    help="Qual versão da Figura 3 gerar")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df_a = pd.read_csv(Path(args.a).resolve())
    df_b = pd.read_csv(Path(args.b).resolve())

    # Figura 1 e 2 são fixas no seu plano de “até 3 gráficos”
    fig1_tradeoff_dual_axis(df_a, out_dir)
    fig2_latency_by_algorithm(df_b, out_dir)

    # Figura 3 é configurável
    if args.fig3 == "A":
        fig3_throughput_A(df_a, out_dir)
    elif args.fig3 == "B":
        fig3_throughput_B(df_b, out_dir)
    elif args.fig3 == "both":
        fig3_throughput_both(df_a, df_b, out_dir)
    else:
        pass

    print("OK! Figuras geradas em:", out_dir)
    print(" - fig1_tradeoff_cpu_vs_ve.png")
    print(" - fig2_latency_by_algorithm.png")
    if args.fig3 == "A":
        print(" - fig3_throughput_A.png")
    elif args.fig3 == "B":
        print(" - fig3_throughput_B.png")
    elif args.fig3 == "both":
        print(" - fig3_throughput.png")


if __name__ == "__main__":
    main()