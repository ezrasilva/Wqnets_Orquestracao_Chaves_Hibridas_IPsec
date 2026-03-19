#!/usr/bin/env python3
"""
Gera gráficos do artigo a partir do CSV resumo produzido por analisar_tradeoff.py.

Gráficos gerados:
1) janela_exposicao_vs_tr.png
2) consumo_qkd_vs_tr.png
3) throughput_vs_tr.png
4) volume_exposicao_vs_tr.png (opcional, mas útil)
5) tradeoff_seguranca_consumo.pdf (consumo QKD vs volume exposto)

Uso:
python gerar_graficos_tradeoff.py --csv out_tradeoff/tradeoff_variaveis_resumo.csv --out-dir figs_tradeoff
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def carregar_dados(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    colunas_numericas = [
        "T_r_s",
        "janela_exposicao_s",
        "consumo_qkd_bits_s",
        "volume_exposicao_megabits",
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

    df = df.sort_values("T_r_s").reset_index(drop=True)
    return df


def grafico_janela_exposicao(df: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(7, 4.5))
    plt.plot(df["T_r_s"], df["janela_exposicao_s"], marker="o")
    plt.xlabel("Intervalo de rotação $T_r$ (s)")
    plt.ylabel("Janela de exposição $W_e$ (s)")
    plt.title("Janela de exposição vs. intervalo de rotação")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "janela_exposicao_vs_tr.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def grafico_consumo_qkd(df: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(7, 4.5))
    plt.plot(df["T_r_s"], df["consumo_qkd_bits_s"], marker="o")
    plt.xlabel("Intervalo de rotação $T_r$ (s)")
    plt.ylabel("Consumo de entropia QKD (bits/s)")
    plt.title("Consumo de entropia QKD vs. intervalo de rotação")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "consumo_qkd_vs_tr.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def grafico_throughput(df: pd.DataFrame, out_dir: Path) -> None:
    plt.figure(figsize=(7, 4.5))

    x = df["T_r_s"]
    y = df["throughput_media_mbps"]

    if "throughput_ic95_mbps" in df.columns:
        yerr = df["throughput_ic95_mbps"].fillna(0)
        plt.errorbar(x, y, yerr=yerr, marker="o", capsize=4)
    else:
        plt.plot(x, y, marker="o")

    plt.xlabel("Intervalo de rotação $T_r$ (s)")
    plt.ylabel("Throughput médio (Mbps)")
    plt.title("Throughput do túnel vs. intervalo de rotação")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "throughput_vs_tr.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def grafico_volume_exposicao(df: pd.DataFrame, out_dir: Path) -> None:
    if "volume_exposicao_megabits" not in df.columns:
        return

    plt.figure(figsize=(7, 4.5))
    x = df["T_r_s"]
    y = df["volume_exposicao_megabits"]

    # Pontos experimentais + linha de tendência visual.
    plt.plot(x, y, "-o", linewidth=2, markersize=6)

    # Escala fixa para visual limpo e comparável entre execuções.
    plt.ylim(0, 900)

    # Ticks explícitos para facilitar comparação por T_r.
    plt.xticks(sorted(x.dropna().unique()))

    plt.xlabel("Intervalo de rotação $T_r$ (s)")
    plt.ylabel("Volume de exposição por chave (Mbits)")
    plt.title("Volume de exposição vs. intervalo de rotação")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "volume_exposicao_vs_tr.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def grafico_latencia(df: pd.DataFrame, out_dir: Path) -> None:
    if "latencia_media_ms" not in df.columns:
        return

    plt.figure(figsize=(7, 4.5))

    x = df["T_r_s"]
    y = df["latencia_media_ms"]

    if "latencia_ic95_ms" in df.columns:
        yerr = df["latencia_ic95_ms"].fillna(0)
        plt.errorbar(x, y, yerr=yerr, marker="o", capsize=4)
    else:
        plt.plot(x, y, marker="o")

    plt.xlabel("Intervalo de rotação $T_r$ (s)")
    plt.ylabel("Latência média de rekey (ms)")
    plt.title("Latência de rekey vs. intervalo de rotação")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "latencia_rekey_vs_tr.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def grafico_throughput_consumo_combinado(df: pd.DataFrame, out_dir: Path) -> None:
    """Combina throughput e consumo QKD em uma única figura com duas subfiguras."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.5))

    # Subfigura 1: Throughput
    x = df["T_r_s"]
    y_thr = df["throughput_media_mbps"]

    if "throughput_ic95_mbps" in df.columns:
        yerr = df["throughput_ic95_mbps"].fillna(0)
        ax1.errorbar(x, y_thr, yerr=yerr, marker="o", capsize=4)
    else:
        ax1.plot(x, y_thr, marker="o")

    ax1.set_xlabel("Intervalo de rotação $T_r$ (s)")
    ax1.set_ylabel("Throughput médio (Mbps)")
    ax1.set_title("(a) Throughput do túnel")
    ax1.grid(True, alpha=0.3)

    # Subfigura 2: Consumo QKD
    y_qkd = df["consumo_qkd_bits_s"]
    ax2.plot(x, y_qkd, marker="o", color="tab:orange")
    ax2.set_xlabel("Intervalo de rotação $T_r$ (s)")
    ax2.set_ylabel("Consumo de entropia QKD (bits/s)")
    ax2.set_title("(b) Consumo de entropia QKD")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_dir / "throughput_consumo_vs_tr.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def grafico_tradeoff_direto(df: pd.DataFrame, out_dir: Path) -> None:
    """Plota o trade-off central: consumo de entropia QKD vs volume de exposição."""
    if "consumo_qkd_bits_s" not in df.columns or "volume_exposicao_megabits" not in df.columns:
        return

    plt.figure(figsize=(7, 4.8))

    x = df["consumo_qkd_bits_s"]
    y = df["volume_exposicao_megabits"]
    tr_values = df["T_r_s"] if "T_r_s" in df.columns else [None] * len(df)

    plt.scatter(x, y, s=55, color="tab:blue", zorder=3)

    # Pequeno deslocamento para evitar sobreposição do texto com o marcador.
    x_off = (x.max() - x.min()) * 0.01 if len(x) > 1 else 0.5
    y_off = (y.max() - y.min()) * 0.01 if len(y) > 1 else 0.5

    for x_i, y_i, tr in zip(x, y, tr_values):
        if pd.isna(x_i) or pd.isna(y_i):
            continue
        if tr is None or pd.isna(tr):
            label = "Tr=?"
        else:
            tr_num = int(tr) if float(tr).is_integer() else tr
            label = f"Tr={tr_num}s"
        plt.annotate(label, (x_i + x_off, y_i + y_off), fontsize=9)

    plt.xlabel("Consumo de entropia QKD (bits/s)")
    plt.ylabel("Volume de exposição por chave (Mbits)")
    plt.title("Trade-off entre segurança e consumo de entropia")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "tradeoff_seguranca_consumo.pdf", dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera gráficos do artigo a partir do CSV resumo do trade-off"
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Caminho para o CSV resumo gerado pelo script de análise",
    )
    parser.add_argument(
        "--out-dir",
        default="figs_tradeoff",
        help="Diretório de saída das figuras",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df = carregar_dados(csv_path)

    grafico_janela_exposicao(df, out_dir)
    grafico_consumo_qkd(df, out_dir)
    grafico_throughput(df, out_dir)
    grafico_volume_exposicao(df, out_dir)
    grafico_latencia(df, out_dir)
    grafico_throughput_consumo_combinado(df, out_dir)
    grafico_tradeoff_direto(df, out_dir)

    print(f"[OK] Figuras salvas em: {out_dir}")


if __name__ == "__main__":
    main()