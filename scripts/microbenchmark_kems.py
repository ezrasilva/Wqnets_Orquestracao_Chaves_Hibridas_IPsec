#!/usr/bin/env python3
"""
Experimento 1 - Microbenchmark isolado dos KEMs.

Mede, por algoritmo:
- latencia de encapsulacao (ms)
- latencia de decapsulacao (ms)
- tamanho da chave publica (bytes)
- tamanho do ciphertext (bytes)

CPU e opcional via --with-cpu.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import oqs

DEFAULT_ALGORITHMS = [
    "ML-KEM-768",
    "BIKE-L1",
    "FrodoKEM-640-AES",
    "Classic-McEliece-348864",
]


def _stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "n": 0,
            "mean": 0.0,
            "std": 0.0,
            "stderr": 0.0,
            "ci95": 0.0,
            "min": 0.0,
            "max": 0.0,
        }

    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    stderr = std / math.sqrt(len(values)) if len(values) > 1 else 0.0
    ci95 = 1.96 * stderr

    return {
        "n": len(values),
        "mean": mean,
        "std": std,
        "stderr": stderr,
        "ci95": ci95,
        "min": min(values),
        "max": max(values),
    }


def _measure_call(func):
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    result = func()
    cpu_end = time.process_time()
    wall_end = time.perf_counter()
    wall_ms = (wall_end - wall_start) * 1000.0
    cpu_ms = (cpu_end - cpu_start) * 1000.0
    return result, wall_ms, cpu_ms


def run_algorithm(algorithm: str, iterations: int, with_cpu: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # Chave estatica para isolar encaps/decaps e evitar medir keygen no loop.
    with oqs.KeyEncapsulation(algorithm) as kem_keygen:
        public_key = kem_keygen.generate_keypair()
        secret_key = kem_keygen.export_secret_key()

    for i in range(1, iterations + 1):
        with oqs.KeyEncapsulation(algorithm) as kem_enc:
            (ciphertext, shared_secret_enc), encaps_ms, encaps_cpu_ms = _measure_call(
                lambda: kem_enc.encap_secret(public_key)
            )

        with oqs.KeyEncapsulation(algorithm, secret_key=secret_key) as kem_dec:
            shared_secret_dec, decaps_ms, decaps_cpu_ms = _measure_call(
                lambda: kem_dec.decap_secret(ciphertext)
            )

        if shared_secret_enc != shared_secret_dec:
            raise RuntimeError(
                f"Shared secret divergente em {algorithm} na iteracao {i}"
            )

        row = {
            "algorithm": algorithm,
            "iteration": i,
            "encaps_ms": round(encaps_ms, 6),
            "decaps_ms": round(decaps_ms, 6),
            "public_key_bytes": len(public_key),
            "ciphertext_bytes": len(ciphertext),
        }

        if with_cpu:
            row["encaps_cpu_ms"] = round(encaps_cpu_ms, 6)
            row["decaps_cpu_ms"] = round(decaps_cpu_ms, 6)

        rows.append(row)

    summary = {
        "algorithm": algorithm,
        "iterations": iterations,
        "encaps": _stats([r["encaps_ms"] for r in rows]),
        "decaps": _stats([r["decaps_ms"] for r in rows]),
        "public_key_bytes": int(rows[0]["public_key_bytes"]),
        "ciphertext_bytes": int(rows[0]["ciphertext_bytes"]),
    }

    if with_cpu:
        summary["encaps_cpu"] = _stats([r["encaps_cpu_ms"] for r in rows])
        summary["decaps_cpu"] = _stats([r["decaps_cpu_ms"] for r in rows])

    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Microbenchmark isolado dos KEMs")
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=DEFAULT_ALGORITHMS,
        help="Lista de algoritmos KEM do liboqs",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Numero de iteracoes por algoritmo",
    )
    parser.add_argument(
        "--out-dir",
        default="teste_kem",
        help="Diretorio de saida",
    )
    parser.add_argument(
        "--with-cpu",
        action="store_true",
        help="Inclui CPU media das operacoes",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    detail_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for algorithm in args.algorithms:
        print(f"[RUN] {algorithm}")
        try:
            rows, summary = run_algorithm(algorithm, args.iterations, args.with_cpu)
            detail_rows.extend(rows)
            summaries.append(summary)
            print(
                f"[OK] {algorithm} encaps={summary['encaps']['mean']:.3f}ms, "
                f"decaps={summary['decaps']['mean']:.3f}ms"
            )
        except Exception as exc:
            print(f"[ERRO] {algorithm}: {exc}")

    if not summaries:
        raise SystemExit("Nenhum algoritmo executou com sucesso.")

    detail_csv = out_dir / "kem_microbenchmark_detalhado.csv"
    fieldnames = list(detail_rows[0].keys())
    with detail_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detail_rows)

    summary_csv = out_dir / "kem_microbenchmark_resumo.csv"
    summary_rows: list[dict[str, Any]] = []
    for s in summaries:
        row = {
            "algorithm": s["algorithm"],
            "iterations": s["iterations"],
            "encaps_mean_ms": s["encaps"]["mean"],
            "encaps_ci95_ms": s["encaps"]["ci95"],
            "decaps_mean_ms": s["decaps"]["mean"],
            "decaps_ci95_ms": s["decaps"]["ci95"],
            "public_key_bytes": s["public_key_bytes"],
            "ciphertext_bytes": s["ciphertext_bytes"],
        }
        if args.with_cpu:
            row["encaps_cpu_mean_ms"] = s["encaps_cpu"]["mean"]
            row["decaps_cpu_mean_ms"] = s["decaps_cpu"]["mean"]
        summary_rows.append(row)

    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    summary_json = out_dir / "kem_microbenchmark_resumo.json"
    with summary_json.open("w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)

    print(f"[OK] Detalhado: {detail_csv}")
    print(f"[OK] Resumo CSV: {summary_csv}")
    print(f"[OK] Resumo JSON: {summary_json}")


if __name__ == "__main__":
    main()
