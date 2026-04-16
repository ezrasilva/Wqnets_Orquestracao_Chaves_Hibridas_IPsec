#!/usr/bin/env python3
"""
Valida artefatos experimentais esperados no repositório.

Uso:
  python3 scripts/validate_outputs.py
  python3 scripts/validate_outputs.py --strict
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class CheckResult:
    ok: bool
    message: str


def _exists(path: Path, required: bool = True) -> CheckResult:
    if path.exists():
        return CheckResult(True, f"[OK] {path}")
    prefix = "[ERRO]" if required else "[WARN]"
    return CheckResult(not required, f"{prefix} ausente: {path}")


def _csv_has_columns(path: Path, columns: Iterable[str], required: bool = True) -> CheckResult:
    if not path.exists():
        prefix = "[ERRO]" if required else "[WARN]"
        return CheckResult(not required, f"{prefix} CSV ausente: {path}")

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = set(reader.fieldnames or [])

    missing = [col for col in columns if col not in header]
    if not missing:
        return CheckResult(True, f"[OK] colunas presentes em {path}")

    prefix = "[ERRO]" if required else "[WARN]"
    return CheckResult(
        not required,
        f"{prefix} colunas faltantes em {path}: {', '.join(missing)}",
    )


def run_checks(root: Path, strict: bool) -> list[CheckResult]:
    required = True
    optional = not strict

    checks: list[CheckResult] = []

    checks.append(_exists(root / "README.md", required=required))
    checks.append(_exists(root / "docs" / "METODOLOGIA_EXPERIMENTAL.md", required=required))
    checks.append(_exists(root / "docs" / "REPRODUTIBILIDADE.md", required=required))
    checks.append(_exists(root / "docs" / "ESTRUTURA_REPOSITORIO.md", required=required))

    checks.append(_exists(root / "teste_kem" / "kem_microbenchmark_resumo.csv", required=optional))
    checks.append(_exists(root / "out_tradeoff" / "tradeoff_variaveis_resumo.csv", required=optional))
    checks.append(_exists(root / "out_sensibilidade_qkd" / "sensibilidade_variaveis_resumo.csv", required=optional))
    checks.append(_exists(root / "out_agilidade" / "agilidade_variaveis_resumo.csv", required=optional))

    checks.append(
        _csv_has_columns(
            root / "out_tradeoff" / "tradeoff_variaveis_resumo.csv",
            ["cenario", "T_r_s", "throughput_media_mbps", "consumo_qkd_bits_s", "sustentavel"],
            required=optional,
        )
    )
    checks.append(
        _csv_has_columns(
            root / "out_sensibilidade_qkd" / "sensibilidade_variaveis_resumo.csv",
            ["cenario", "qkd_bps", "tr_s", "consumo_bits_s", "sustentavel"],
            required=optional,
        )
    )
    checks.append(
        _csv_has_columns(
            root / "out_agilidade" / "agilidade_variaveis_resumo.csv",
            ["algoritmo", "throughput_media_mbps", "latencia_media_ms"],
            required=optional,
        )
    )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida estrutura e artefatos do projeto")
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Raiz do repositório (default: raiz detectada automaticamente)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falha se artefatos experimentais opcionais estiverem ausentes",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checks = run_checks(root, strict=args.strict)

    errors = 0
    warnings = 0

    for item in checks:
        print(item.message)
        if item.message.startswith("[ERRO]"):
            errors += 1
        elif item.message.startswith("[WARN]"):
            warnings += 1

    print("\nResumo:")
    print(f"- erros: {errors}")
    print(f"- avisos: {warnings}")

    if errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
