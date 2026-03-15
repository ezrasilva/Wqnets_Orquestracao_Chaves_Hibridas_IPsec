#!/usr/bin/env python3
"""
Percorre cenários em teste_tradeoff/interval_* e extrai variáveis para análise:

1) Throughput médio
2) Janela de exposição
3) Volume de exposição por chave (V_e = T_bar * T_r)
4) Consumo de entropia QKD
5) Sustentabilidade
6) Intervalo mínimo teórico de rotação
7) Latência de rekey
8) CPU média
9) Memória média

Saídas:
- CSV resumido por cenário
- JSON detalhado por cenário
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


def _stats(valores: list[float], prefixo_media: str) -> dict[str, Any]:
    if not valores:
        return {
            "n": 0,
            prefixo_media: None,
            "desvio_padrao": None,
            "erro_padrao": None,
            "ic95": None,
            "min": None,
            "max": None,
            "valores": [],
        }

    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 0.0
    erro_padrao = (desvio / math.sqrt(len(valores))) if len(valores) > 1 else 0.0
    ic95 = 1.96 * erro_padrao

    return {
        "n": len(valores),
        prefixo_media: media,
        "desvio_padrao": desvio,
        "erro_padrao": erro_padrao,
        "ic95": ic95,
        "min": min(valores),
        "max": max(valores),
        "valores": valores,
    }


def extrair_throughput_json(caminho_json: Path) -> float:
    with caminho_json.open("r", encoding="utf-8") as f:
        dados = json.load(f)

    if isinstance(dados, dict) and "bits_per_second" in dados:
        return float(dados["bits_per_second"]) / 1_000_000

    if isinstance(dados, dict) and "end" in dados and isinstance(dados["end"], dict):
        end = dados["end"]
        if "sum_received" in end and "bits_per_second" in end["sum_received"]:
            return float(end["sum_received"]["bits_per_second"]) / 1_000_000
        if "sum_sent" in end and "bits_per_second" in end["sum_sent"]:
            return float(end["sum_sent"]["bits_per_second"]) / 1_000_000

    if isinstance(dados, dict) and "intervals" in dados and isinstance(dados["intervals"], list):
        bps_intervalos: list[float] = []
        for item in dados["intervals"]:
            if isinstance(item, dict):
                sum_block = item.get("sum", {})
                if isinstance(sum_block, dict) and "bits_per_second" in sum_block:
                    bps_intervalos.append(float(sum_block["bits_per_second"]))

        if bps_intervalos:
            return statistics.mean(bps_intervalos) / 1_000_000

    raise ValueError(f"Campo de throughput não encontrado em {caminho_json}")


def analisar_throughput_pasta(pasta_cenario: Path) -> dict[str, Any]:
    valores: list[float] = []

    for caminho in sorted(pasta_cenario.glob("throughput_iter_*.json")):
        try:
            valores.append(extrair_throughput_json(caminho))
        except Exception as e:
            print(f"[WARN] Erro em {caminho.name}: {e}")

    if not valores:
        for caminho in sorted(pasta_cenario.glob("*.json")):
            try:
                valores.append(extrair_throughput_json(caminho))
            except Exception:
                pass

    if not valores:
        raise ValueError(f"Nenhum JSON válido encontrado em {pasta_cenario}")

    r = _stats(valores, "media_mbps")
    r["desvio_padrao_mbps"] = r.pop("desvio_padrao")
    r["erro_padrao_mbps"] = r.pop("erro_padrao")
    r["ic95_mbps"] = r.pop("ic95")
    r["min_mbps"] = r.pop("min")
    r["max_mbps"] = r.pop("max")
    return r


def calcular_janela_exposicao(T_r: float) -> float:
    return T_r


def calcular_volume_exposicao_bits(throughput_mbps: float, T_r: float) -> float:
    """
    V_e = T_bar * T_r
    throughput_mbps em megabits/s
    resultado em bits
    """
    throughput_bps = throughput_mbps * 1_000_000
    return throughput_bps * T_r


def calcular_volume_exposicao_megabits(throughput_mbps: float, T_r: float) -> float:
    """
    Resultado em megabits
    """
    return throughput_mbps * T_r


def calcular_consumo_qkd(k_bits: float, T_r: float) -> float:
    return k_bits / T_r


def verificar_sustentabilidade(k_bits: float, T_r: float, R_qkd: float) -> dict[str, Any]:
    consumo = k_bits / T_r
    sustentavel = consumo <= R_qkd

    return {
        "consumo_bits_s": consumo,
        "R_qkd_bits_s": R_qkd,
        "sustentavel": sustentavel,
        "folga_bits_s": R_qkd - consumo,
    }


def calcular_tr_minimo(k_bits: float, R_qkd: float) -> float:
    return k_bits / R_qkd


def _parse_timestamp_flex(value: str) -> datetime:
    value = str(value).strip()

    # Trata ISO com Z
    if value.endswith("Z"):
        value = value[:-1]

    # Tenta ISO
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    # Tenta formatos conhecidos
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    # Fallback: epoch
    return datetime.fromtimestamp(float(value))


def calcular_latencias_rekey_controller_log(csv_log: Path) -> list[float]:
    """
    Pareamento robusto:
    usa o próximo evento de finalização após um REKEY_START.
    """
    latencias_ms: list[float] = []
    inicio_atual: datetime | None = None

    eventos_fim = {"SA_UPDATED", "REKEY_END", "TUNNEL_ESTABLISHED"}

    with csv_log.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event = str(row.get("event", "")).strip().upper()
            if not event:
                continue

            ts_raw = row.get("timestamp")
            if ts_raw is None or str(ts_raw).strip() == "":
                continue

            ts = _parse_timestamp_flex(str(ts_raw))

            if event == "REKEY_START":
                inicio_atual = ts
                continue

            if event in eventos_fim and inicio_atual is not None:
                lat = (ts - inicio_atual).total_seconds() * 1000
                if lat >= 0:
                    latencias_ms.append(lat)
                inicio_atual = None

    return latencias_ms


def calcular_latencias_rekey_sdn_metrics(csv_log: Path) -> list[float]:
    latencias: list[float] = []

    with csv_log.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_type = str(row.get("event_type", "")).strip().upper()
            if event_type != "E2E_REKEY_LATENCY":
                continue

            value_ms = row.get("value_ms")
            if value_ms is None or str(value_ms).strip() == "":
                continue

            try:
                latencias.append(float(value_ms))
            except ValueError:
                continue

    return latencias


def resumo_latencia_rekey(pasta_cenario: Path) -> dict[str, Any] | None:
    controller_log = pasta_cenario / "controller_log.csv"
    sdn_metrics = pasta_cenario / "sdn_metrics.csv"

    latencias: list[float] = []
    if controller_log.exists():
        latencias = calcular_latencias_rekey_controller_log(controller_log)

    if not latencias and sdn_metrics.exists():
        latencias = calcular_latencias_rekey_sdn_metrics(sdn_metrics)

    if not latencias:
        return None

    r = _stats(latencias, "media_ms")
    r["desvio_padrao_ms"] = r.pop("desvio_padrao")
    r["erro_padrao_ms"] = r.pop("erro_padrao")
    r["ic95_ms"] = r.pop("ic95")
    r["min_ms"] = r.pop("min")
    r["max_ms"] = r.pop("max")
    return r


def _ler_coluna_numerica(csv_resources: Path, colunas_candidatas: list[str]) -> list[float]:
    valores: list[float] = []

    with csv_resources.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        header = set(reader.fieldnames or [])
        coluna = None
        for c in colunas_candidatas:
            if c in header:
                coluna = c
                break

        if coluna is None:
            return []

        for row in reader:
            raw = row.get(coluna)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                valores.append(float(raw))
            except ValueError:
                continue

    return valores


def analisar_cpu(csv_resources: Path) -> dict[str, Any] | None:
    cpu = _ler_coluna_numerica(csv_resources, ["cpu_percent", "cpu_perc"])
    if not cpu:
        return None

    r = _stats(cpu, "media_cpu")
    r["desvio_padrao_cpu"] = r.pop("desvio_padrao")
    r["erro_padrao_cpu"] = r.pop("erro_padrao")
    r["ic95_cpu"] = r.pop("ic95")
    r["min_cpu"] = r.pop("min")
    r["max_cpu"] = r.pop("max")
    return r


def analisar_memoria(csv_resources: Path) -> dict[str, Any] | None:
    memoria = _ler_coluna_numerica(csv_resources, ["memory_mb", "mem_mib", "memory_mib"])
    if not memoria:
        return None

    r = _stats(memoria, "media_memoria")
    r["desvio_padrao_memoria"] = r.pop("desvio_padrao")
    r["erro_padrao_memoria"] = r.pop("erro_padrao")
    r["ic95_memoria"] = r.pop("ic95")
    r["min_memoria"] = r.pop("min")
    r["max_memoria"] = r.pop("max")
    return r


def _extrair_intervalo_da_pasta(pasta_cenario: Path) -> float:
    match = re.search(r"interval_(\d+(?:\.\d+)?)s", pasta_cenario.name)
    if not match:
        raise ValueError(f"Não foi possível extrair T_r do nome da pasta: {pasta_cenario.name}")
    return float(match.group(1))


def _achar_arquivo_recursos(pasta_cenario: Path) -> Path | None:
    candidatos = [
        pasta_cenario / "resource_metrics.csv",
        pasta_cenario / "resources.csv",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    return None


def analisar_cenario(pasta_cenario: Path, k_bits: float = 256, R_qkd: float = 1000) -> dict[str, Any]:
    T_r = _extrair_intervalo_da_pasta(pasta_cenario)

    resultado: dict[str, Any] = {
        "cenario": pasta_cenario.name,
        "T_r_s": T_r,
        "janela_exposicao_s": calcular_janela_exposicao(T_r),
        "consumo_qkd_bits_s": calcular_consumo_qkd(k_bits, T_r),
        "tr_min_teorico_s": calcular_tr_minimo(k_bits, R_qkd),
        "sustentabilidade": verificar_sustentabilidade(k_bits, T_r, R_qkd),
    }

    throughput = analisar_throughput_pasta(pasta_cenario)
    resultado["throughput"] = throughput

    throughput_mbps = throughput["media_mbps"]
    if throughput_mbps is not None:
        resultado["volume_exposicao_bits"] = calcular_volume_exposicao_bits(throughput_mbps, T_r)
        resultado["volume_exposicao_megabits"] = calcular_volume_exposicao_megabits(throughput_mbps, T_r)

    lat = resumo_latencia_rekey(pasta_cenario)
    if lat is not None:
        resultado["latencia_rekey"] = lat

    resources = _achar_arquivo_recursos(pasta_cenario)
    if resources is not None:
        cpu = analisar_cpu(resources)
        if cpu is not None:
            resultado["cpu"] = cpu

        mem = analisar_memoria(resources)
        if mem is not None:
            resultado["memoria"] = mem

    return resultado


def _flatten_summary(r: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cenario": r.get("cenario"),
        "T_r_s": r.get("T_r_s"),
        "janela_exposicao_s": r.get("janela_exposicao_s"),
        "volume_exposicao_megabits": r.get("volume_exposicao_megabits"),
        "volume_exposicao_bits": r.get("volume_exposicao_bits"),
        "consumo_qkd_bits_s": r.get("consumo_qkd_bits_s"),
        "tr_min_teorico_s": r.get("tr_min_teorico_s"),
        "sustentavel": r.get("sustentabilidade", {}).get("sustentavel"),
        "folga_bits_s": r.get("sustentabilidade", {}).get("folga_bits_s"),
        "R_qkd_bits_s": r.get("sustentabilidade", {}).get("R_qkd_bits_s"),
    }

    thr = r.get("throughput", {})
    out.update(
        {
            "throughput_n": thr.get("n"),
            "throughput_media_mbps": thr.get("media_mbps"),
            "throughput_desvio_padrao_mbps": thr.get("desvio_padrao_mbps"),
            "throughput_erro_padrao_mbps": thr.get("erro_padrao_mbps"),
            "throughput_ic95_mbps": thr.get("ic95_mbps"),
            "throughput_min_mbps": thr.get("min_mbps"),
            "throughput_max_mbps": thr.get("max_mbps"),
        }
    )

    lat = r.get("latencia_rekey", {})
    out.update(
        {
            "latencia_n": lat.get("n"),
            "latencia_media_ms": lat.get("media_ms"),
            "latencia_desvio_padrao_ms": lat.get("desvio_padrao_ms"),
            "latencia_erro_padrao_ms": lat.get("erro_padrao_ms"),
            "latencia_ic95_ms": lat.get("ic95_ms"),
            "latencia_min_ms": lat.get("min_ms"),
            "latencia_max_ms": lat.get("max_ms"),
        }
    )

    cpu = r.get("cpu", {})
    out.update(
        {
            "cpu_n": cpu.get("n"),
            "cpu_media": cpu.get("media_cpu"),
            "cpu_desvio_padrao": cpu.get("desvio_padrao_cpu"),
            "cpu_erro_padrao": cpu.get("erro_padrao_cpu"),
            "cpu_ic95": cpu.get("ic95_cpu"),
            "cpu_min": cpu.get("min_cpu"),
            "cpu_max": cpu.get("max_cpu"),
        }
    )

    mem = r.get("memoria", {})
    out.update(
        {
            "memoria_n": mem.get("n"),
            "memoria_media": mem.get("media_memoria"),
            "memoria_desvio_padrao": mem.get("desvio_padrao_memoria"),
            "memoria_erro_padrao": mem.get("erro_padrao_memoria"),
            "memoria_ic95": mem.get("ic95_memoria"),
            "memoria_min": mem.get("min_memoria"),
            "memoria_max": mem.get("max_memoria"),
        }
    )

    return out


def analisar_teste_tradeoff(
    base_dir: Path,
    out_dir: Path,
    k_bits: float,
    R_qkd: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cenarios = sorted([p for p in base_dir.iterdir() if p.is_dir() and p.name.startswith("interval_")])
    if not cenarios:
        raise ValueError(f"Nenhuma pasta interval_* encontrada em {base_dir}")

    resultados: list[dict[str, Any]] = []
    for cenario in cenarios:
        try:
            resultados.append(analisar_cenario(cenario, k_bits=k_bits, R_qkd=R_qkd))
            print(f"[OK] Cenário analisado: {cenario.name}")
        except Exception as e:
            print(f"[WARN] Falha no cenário {cenario.name}: {e}")

    if not resultados:
        raise ValueError("Nenhum cenário pôde ser analisado.")

    resultados.sort(key=lambda x: float(x.get("T_r_s", 0)))
    resumo = [_flatten_summary(r) for r in resultados]

    out_dir.mkdir(parents=True, exist_ok=True)

    json_out = out_dir / "tradeoff_variaveis_detalhado.json"
    csv_out = out_dir / "tradeoff_variaveis_resumo.csv"

    with json_out.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    campos_csv = list(resumo[0].keys())
    with csv_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos_csv)
        writer.writeheader()
        writer.writerows(resumo)

    print(f"\n[OK] JSON detalhado: {json_out}")
    print(f"[OK] CSV resumo:    {csv_out}")

    return resultados, resumo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Percorre teste_tradeoff e extrai variáveis para análise do artigo"
    )
    parser.add_argument(
        "--base-dir",
        default="teste_tradeoff",
        help="Diretório base com pastas interval_* (default: teste_tradeoff)",
    )
    parser.add_argument(
        "--out-dir",
        default="out_tradeoff",
        help="Diretório de saída para CSV/JSON (default: out_tradeoff)",
    )
    parser.add_argument(
        "--k-bits",
        type=float,
        default=256,
        help="Bits consumidos por rotação (default: 256)",
    )
    parser.add_argument(
        "--r-qkd",
        type=float,
        default=1000,
        help="Taxa QKD em bits/s (default: 1000)",
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    analisar_teste_tradeoff(
        base_dir=base_dir,
        out_dir=out_dir,
        k_bits=float(args.k_bits),
        R_qkd=float(args.r_qkd),
    )


if __name__ == "__main__":
    main()