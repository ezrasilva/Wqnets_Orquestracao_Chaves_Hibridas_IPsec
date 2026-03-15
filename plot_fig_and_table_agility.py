#!/usr/bin/env python3
"""
Gera:
1) Figura com 2 gráficos em 1 para a bateria de agilidade criptográfica
2) CSV com os dados resumidos da tabela do artigo

Entrada:
- CSV resumo gerado por analisar_agilidade.py

Saídas:
- fig_agilidade_2em1.png
- agilidade_tabela_artigo.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def carregar_dados(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    colunas_numericas = [
        "throughput_media_mbps",
        "throughput_ic95_mbps",
        "latencia_media_ms",
        "latencia_ic95_ms",
        "cpu_media",
        "cpu_ic95",
        "memoria_media",
        "memoria_ic95",
    ]

    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def gerar_csv_tabela(df: pd.DataFrame, out_dir: Path) -> Path:
    colunas_desejadas = [
        "algoritmo",
        "throughput_media_mbps",
        "throughput_ic95_mbps",
        "latencia_media_ms",
        "latencia_ic95_ms",
        "cpu_media",
        "cpu_ic95",
        "memoria_media",
        "memoria_ic95",
    ]

    colunas_existentes = [c for c in colunas_desejadas if c in df.columns]
    tabela = df[colunas_existentes].copy()

    caminho_saida = out_dir / "agilidade_tabela_artigo.csv"
    tabela.to_csv(caminho_saida, index=False, encoding="utf-8")
    return caminho_saida


def gerar_figura_2em1(df: pd.DataFrame, out_dir: Path) -> Path:
    algoritmos = df["algoritmo"].tolist()
    x = range(len(algoritmos))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # Gráfico 1: Throughput
    y_thr = df["throughput_media_mbps"]
    yerr_thr = df["throughput_ic95_mbps"] if "throughput_ic95_mbps" in df.columns else None

    axes[0].bar(x, y_thr, yerr=yerr_thr, capsize=4)
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(algoritmos, rotation=30, ha="right")
    axes[0].set_ylabel("Throughput médio (Mbps)")
    axes[0].set_title("(a) Throughput por algoritmo")
    axes[0].grid(True, axis="y", alpha=0.3)

    # Gráfico 2: Latência
    y_lat = df["latencia_media_ms"]
    yerr_lat = df["latencia_ic95_ms"] if "latencia_ic95_ms" in df.columns else None

    axes[1].bar(x, y_lat, yerr=yerr_lat, capsize=4)
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(algoritmos, rotation=30, ha="right")
    axes[1].set_ylabel("Latência média de rekey (ms)")
    axes[1].set_title("(b) Latência de rekey por algoritmo")
    axes[1].grid(True, axis="y", alpha=0.3)

    fig.suptitle("Avaliação da agilidade criptográfica", fontsize=12)
    fig.tight_layout()

    caminho_saida = out_dir / "fig_agilidade_2em1.png"
    fig.savefig(caminho_saida, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return caminho_saida


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera figura 2-em-1 e CSV da tabela da bateria de agilidade criptográfica"
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="CSV resumo gerado por analisar_agilidade.py",
    )
    parser.add_argument(
        "--out-dir",
        default="figs_agilidade",
        help="Diretório de saída",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df = carregar_dados(csv_path)

    caminho_csv_tabela = gerar_csv_tabela(df, out_dir)
    caminho_figura = gerar_figura_2em1(df, out_dir)

    print(f"[OK] Figura salva em: {caminho_figura}")
    print(f"[OK] CSV da tabela salvo em: {caminho_csv_tabela}")


if __name__ == "__main__":
    main()