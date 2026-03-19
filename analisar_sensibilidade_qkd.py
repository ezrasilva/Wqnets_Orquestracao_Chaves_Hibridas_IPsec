#!/usr/bin/env python3
"""
Analise do Experimento 2 - Sensibilidade a taxa QKD.

Para cada cenario qkd_<rate>bps_tr_<T>s calcula:
- consumo de entropia
- sustentabilidade
- throughput medio
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any


def _stats(values: list[float], mean_key: str) -> dict[str, Any]:
	if not values:
		return {
			"n": 0,
			mean_key: None,
			"desvio_padrao": None,
			"erro_padrao": None,
			"ic95": None,
			"min": None,
			"max": None,
		}

	mean = statistics.mean(values)
	std = statistics.stdev(values) if len(values) > 1 else 0.0
	stderr = (std / math.sqrt(len(values))) if len(values) > 1 else 0.0
	ci95 = 1.96 * stderr
	return {
		"n": len(values),
		mean_key: mean,
		"desvio_padrao": std,
		"erro_padrao": stderr,
		"ic95": ci95,
		"min": min(values),
		"max": max(values),
	}


def extract_throughput_mbps(json_path: Path) -> float:
	with json_path.open("r", encoding="utf-8") as f:
		data = json.load(f)

	if isinstance(data, dict) and "end" in data and isinstance(data["end"], dict):
		end = data["end"]
		if "sum_received" in end and "bits_per_second" in end["sum_received"]:
			return float(end["sum_received"]["bits_per_second"]) / 1_000_000
		if "sum_sent" in end and "bits_per_second" in end["sum_sent"]:
			return float(end["sum_sent"]["bits_per_second"]) / 1_000_000

	if isinstance(data, dict) and "intervals" in data and isinstance(data["intervals"], list):
		bps = []
		for item in data["intervals"]:
			if isinstance(item, dict) and isinstance(item.get("sum"), dict):
				val = item["sum"].get("bits_per_second")
				if val is not None:
					bps.append(float(val))
		if bps:
			return statistics.mean(bps) / 1_000_000

	raise ValueError(f"Nao foi possivel extrair throughput de {json_path}")


def summarize_throughput(folder: Path) -> dict[str, Any] | None:
	values: list[float] = []
	for fp in sorted(folder.glob("throughput_iter_*.json")):
		try:
			values.append(extract_throughput_mbps(fp))
		except Exception:
			pass
	if not values:
		return None

	r = _stats(values, "media_mbps")
	r["desvio_padrao_mbps"] = r.pop("desvio_padrao")
	r["erro_padrao_mbps"] = r.pop("erro_padrao")
	r["ic95_mbps"] = r.pop("ic95")
	r["min_mbps"] = r.pop("min")
	r["max_mbps"] = r.pop("max")
	return r


def summarize_rekey_latency(folder: Path) -> dict[str, Any] | None:
	metrics_csv = folder / "sdn_metrics.csv"
	if not metrics_csv.exists():
		return None

	values: list[float] = []
	with metrics_csv.open("r", encoding="utf-8", newline="") as f:
		reader = csv.DictReader(f)
		for row in reader:
			if str(row.get("event_type", "")).upper() != "E2E_REKEY_LATENCY":
				continue
			raw = row.get("value_ms")
			if not raw:
				continue
			try:
				values.append(float(raw))
			except ValueError:
				pass

	if not values:
		return None

	r = _stats(values, "media_ms")
	r["desvio_padrao_ms"] = r.pop("desvio_padrao")
	r["erro_padrao_ms"] = r.pop("erro_padrao")
	r["ic95_ms"] = r.pop("ic95")
	r["min_ms"] = r.pop("min")
	r["max_ms"] = r.pop("max")
	return r


def entropy_metrics(k_bits: float, tr_s: float, qkd_rate_bps: float) -> dict[str, Any]:
	consumo = k_bits / tr_s
	sustentavel = consumo <= qkd_rate_bps
	return {
		"consumo_bits_s": consumo,
		"sustentavel": sustentavel,
		"folga_bits_s": qkd_rate_bps - consumo,
		"qkd_rate_bps": qkd_rate_bps,
	}


def main() -> None:
	parser = argparse.ArgumentParser(description="Analisa sensibilidade a taxa QKD")
	parser.add_argument("--base-dir", default="teste_sensibilidade_qkd")
	parser.add_argument("--out-dir", default="out_sensibilidade_qkd")
	parser.add_argument("--k-bits", type=float, default=256.0)
	args = parser.parse_args()

	base = Path(args.base_dir).resolve()
	out = Path(args.out_dir).resolve()
	out.mkdir(parents=True, exist_ok=True)

	detailed: list[dict[str, Any]] = []
	summary_rows: list[dict[str, Any]] = []

	for folder in sorted(base.glob("qkd_*bps_tr_*s")):
		if not folder.is_dir():
			continue

		name = folder.name
		try:
			# qkd_256bps_tr_2s
			parts = name.split("_")
			qkd_bps = float(parts[1].replace("bps", ""))
			tr_s = float(parts[3].replace("s", ""))
		except Exception:
			print(f"[WARN] Nome de cenario invalido: {name}")
			continue

		throughput = summarize_throughput(folder)
		rekey_latency = summarize_rekey_latency(folder)
		entropy = entropy_metrics(args.k_bits, tr_s, qkd_bps)

		detailed_item = {
			"cenario": name,
			"qkd_bps": qkd_bps,
			"tr_s": tr_s,
			"throughput": throughput,
			"latencia_rekey": rekey_latency,
			"entropia": entropy,
		}
		detailed.append(detailed_item)

		row = {
			"cenario": name,
			"qkd_bps": qkd_bps,
			"tr_s": tr_s,
			"consumo_bits_s": entropy["consumo_bits_s"],
			"sustentavel": entropy["sustentavel"],
			"folga_bits_s": entropy["folga_bits_s"],
		}
		if throughput:
			row.update(
				{
					"throughput_n": throughput["n"],
					"throughput_media_mbps": throughput["media_mbps"],
					"throughput_ic95_mbps": throughput["ic95_mbps"],
				}
			)
		else:
			row.update(
				{
					"throughput_n": None,
					"throughput_media_mbps": None,
					"throughput_ic95_mbps": None,
				}
			)

		if rekey_latency:
			row.update(
				{
					"latencia_n": rekey_latency["n"],
					"latencia_media_ms": rekey_latency["media_ms"],
					"latencia_ic95_ms": rekey_latency["ic95_ms"],
				}
			)
		else:
			row.update(
				{
					"latencia_n": None,
					"latencia_media_ms": None,
					"latencia_ic95_ms": None,
				}
			)

		summary_rows.append(row)

	if summary_rows:
		csv_out = out / "sensibilidade_variaveis_resumo.csv"
		with csv_out.open("w", encoding="utf-8", newline="") as f:
			writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
			writer.writeheader()
			writer.writerows(summary_rows)
		print(f"[OK] CSV resumo: {csv_out}")

	if detailed:
		json_out = out / "sensibilidade_variaveis_detalhado.json"
		with json_out.open("w", encoding="utf-8") as f:
			json.dump(detailed, f, indent=2, ensure_ascii=False)
		print(f"[OK] JSON detalhado: {json_out}")


if __name__ == "__main__":
	main()
