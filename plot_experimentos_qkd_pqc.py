#!/usr/bin/env python3
"""
Gera os plots solicitados para os experimentos:
- Grafico 3: Sustentabilidade vs taxa QKD (heatmap + tabela pivot opcional)
- Grafico 4: Microbenchmark PQC (barras encaps/decaps por algoritmo)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_sustentabilidade_heatmap(df: pd.DataFrame, out_dir: Path) -> None:
    pivot = (
        df.pivot_table(
            index="qkd_bps",
            columns="tr_s",
            values="folga_bits_s",
            aggfunc="mean",
        )
        .sort_index(axis=0)
        .sort_index(axis=1)
    )

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    img = ax.imshow(pivot.values, cmap="YlGn", aspect="auto")

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{int(c)}s" if float(c).is_integer() else str(c) for c in pivot.columns])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{int(i)} bps" if float(i).is_integer() else str(i) for i in pivot.index])
    ax.set_xlabel("Intervalo de rotacao (Tr)")
    ax.set_ylabel("Taxa QKD")
    ax.set_title("Sustentabilidade vs taxa QKD (folga de entropia em bits/s)")

    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            val = float(pivot.iloc[r, c])
            ax.text(c, r, f"{val:.1f}", ha="center", va="center", fontsize=9)

    cbar = fig.colorbar(img, ax=ax)
    cbar.set_label("Folga de entropia (bits/s)")

    plt.tight_layout()
    fig.savefig(out_dir / "grafico3_sustentabilidade_vs_qkd_heatmap.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)

    table_df = (
        df[["qkd_bps", "tr_s", "consumo_bits_s", "folga_bits_s", "sustentavel"]]
        .sort_values(["qkd_bps", "tr_s"])
        .reset_index(drop=True)
    )
    table_df.to_csv(out_dir / "grafico3_sustentabilidade_tabela.csv", index=False)


def plot_microbenchmark_barras(df: pd.DataFrame, out_dir: Path) -> None:
    df = df.copy().sort_values("algorithm").reset_index(drop=True)
    x = range(len(df))
    width = 0.38

    encaps = pd.to_numeric(df["encaps_mean_ms"], errors="coerce")
    decaps = pd.to_numeric(df["decaps_mean_ms"], errors="coerce")

    encaps_err = pd.to_numeric(df.get("encaps_ci95_ms"), errors="coerce").fillna(0)
    decaps_err = pd.to_numeric(df.get("decaps_ci95_ms"), errors="coerce").fillna(0)

    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    ax.bar([i - width / 2 for i in x], encaps, width=width, yerr=encaps_err, capsize=4, label="Encaps")
    ax.bar([i + width / 2 for i in x], decaps, width=width, yerr=decaps_err, capsize=4, label="Decaps")

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["algorithm"], rotation=20, ha="right")
    ax.set_ylabel("Latencia media (ms)")
    ax.set_title("Microbenchmark PQC por algoritmo")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()

    plt.tight_layout()
    fig.savefig(out_dir / "grafico4_microbenchmark_pqc_barras.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera plots dos experimentos de QKD e microbenchmark PQC")
    parser.add_argument(
        "--sens-csv",
        default="out_sensibilidade_qkd/sensibilidade_variaveis_resumo.csv",
        help="CSV de resumo da sensibilidade QKD",
    )
    parser.add_argument(
        "--kem-csv",
        default="teste_kem/kem_microbenchmark_resumo.csv",
        help="CSV de resumo do microbenchmark KEM",
    )
    parser.add_argument(
        "--out-dir",
        default="figs_experimentos",
        help="Diretorio de saida das figuras",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sens_path = Path(args.sens_csv).resolve()
    if not sens_path.exists():
        raise SystemExit(f"Arquivo nao encontrado: {sens_path}")

    sens_df = pd.read_csv(sens_path)
    for col in ["qkd_bps", "tr_s", "consumo_bits_s", "folga_bits_s"]:
        sens_df[col] = pd.to_numeric(sens_df[col], errors="coerce")
    plot_sustentabilidade_heatmap(sens_df, out_dir)
    print(f"[OK] Grafico 3 salvo em: {out_dir}")

    kem_path = Path(args.kem_csv).resolve()
    if kem_path.exists():
        kem_df = pd.read_csv(kem_path)
        plot_microbenchmark_barras(kem_df, out_dir)
        print(f"[OK] Grafico 4 salvo em: {out_dir}")
    else:
        print(f"[WARN] Microbenchmark nao encontrado em: {kem_path}")
        print("[WARN] Grafico 4 foi ignorado (opcional).")


if __name__ == "__main__":
    main()
