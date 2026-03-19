#!/usr/bin/env python3
"""
Experimento 2 - Sensibilidade a taxa QKD.

Executa cenarios combinando:
- Taxas QKD: 256, 1000 e 2000 bits/s (via SAE pair)
- Intervalos de rotacao T_r: 2s, 10s e 60s

Mede e salva por cenario:
- Throughput (iperf3)
- Metricas SDN (inclui eventos de rekey/QKD)
- CPU/memoria via docker stats
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import threading
import time


QKD_RATE_TO_SAE = {
	256: ("sae-3", "sae-4"),
	1000: ("sae-1", "sae-2"),
	2000: ("sae-5", "sae-6"),
}
ROTATION_INTERVALS = [2, 10, 60]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_BASE_DIR = os.path.join(SCRIPT_DIR, "teste_sensibilidade_qkd")
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "scripts")
METRICS_FILE = os.path.join(SCRIPTS_DIR, "experiment_metrics.csv")
RESOURCE_FILE = "resource_metrics.csv"


class QKDSensitivityController:
	def __init__(self, duration: int, profile: str, iterations: int) -> None:
		self.duration = duration
		self.profile = profile
		self.iterations = iterations
		self.running = True
		self.logical_nodes = ["alice", "bob"]
		self.container_map = {node: node for node in self.logical_nodes}
		self.real_containers = list(self.container_map.values())
		self.orchestrator_name = "orchestrator"

	def run_cmd(self, cmd: str, env: dict[str, str] | None = None, detached: bool = False):
		try:
			if detached:
				return subprocess.Popen(
					cmd,
					shell=True,
					env=env,
					stdout=subprocess.DEVNULL,
					stderr=subprocess.DEVNULL,
				)
			return subprocess.run(
				cmd,
				shell=True,
				env=env,
				check=True,
				capture_output=True,
				text=True,
			)
		except subprocess.CalledProcessError as exc:
			print(f"[QKD-Sensitivity] ERRO cmd: {cmd}\n{exc.stderr}")
			return None

	def setup_environment(self, rotation_interval: int, sae_alice: str, sae_bob: str) -> None:
		print(
			"[QKD-Sensitivity] Preparando ambiente "
			f"T_r={rotation_interval}s SAE_ALICE={sae_alice} SAE_BOB={sae_bob}"
		)
		env = os.environ.copy()
		env["ROTATION_INTERVAL"] = str(rotation_interval)
		env["PQC_ALGO"] = "ML-KEM-768"
		env["SAE_ALICE"] = sae_alice
		env["SAE_BOB"] = sae_bob

		compose_file = os.path.join(SCRIPT_DIR, "docker-compose.yml")
		self.run_cmd(f"docker compose -f {compose_file} down", env=env)
		time.sleep(2)
		self.run_cmd(f"docker compose -f {compose_file} up -d", env=env)
		time.sleep(30)

		if self.profile != "perfect":
			containers = " ".join(self.real_containers)
			cmd = (
				f"python3 {SCRIPTS_DIR}/simulate_network_conditions.py "
				f"--profile {self.profile} --containers {containers}"
			)
			self.run_cmd(cmd)

	def monitor_resources_thread(self, scenario_folder: str) -> None:
		res_file = os.path.join(scenario_folder, RESOURCE_FILE)
		with open(res_file, "w", encoding="utf-8") as f:
			f.write("timestamp,container,cpu_perc,mem_mib\n")

		while self.running:
			try:
				ts = time.time()
				containers = self.real_containers + [self.orchestrator_name]
				cmd = (
					"docker stats "
					+ " ".join(containers)
					+ " --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}'"
				)
				res = self.run_cmd(cmd)
				if res and res.stdout:
					with open(res_file, "a", encoding="utf-8") as f:
						for line in res.stdout.strip().split("\n"):
							parts = line.split(",")
							if len(parts) >= 3:
								name = parts[0].replace("/", "")
								cpu = parts[1].replace("%", "")
								mem = (
									parts[2]
									.split("/")[0]
									.strip()
									.replace("MiB", "")
									.replace("GiB", "")
								)
								f.write(f"{ts},{name},{cpu},{mem}\n")
			except Exception:
				pass
			time.sleep(1)

	def run_iperf_test(self, iteration: int, folder: str) -> None:
		self.run_cmd("docker exec -d bob iperf3 -s -D")
		time.sleep(1)
		cmd = f"docker exec alice iperf3 -c 192.168.100.11 -t {self.duration} -J"
		res = self.run_cmd(cmd)
		if res and res.stdout:
			out_path = os.path.join(folder, f"throughput_iter_{iteration}.json")
			with open(out_path, "w", encoding="utf-8") as f:
				f.write(res.stdout)

	def run_battery(self) -> None:
		os.makedirs(RESULTS_BASE_DIR, exist_ok=True)
		summary_rows: list[dict[str, str | int]] = []

		for qkd_rate_bps, (sae_alice, sae_bob) in QKD_RATE_TO_SAE.items():
			for tr in ROTATION_INTERVALS:
				scenario = f"qkd_{qkd_rate_bps}bps_tr_{tr}s"
				scenario_folder = os.path.join(RESULTS_BASE_DIR, scenario)
				os.makedirs(scenario_folder, exist_ok=True)

				print("=" * 70)
				print(
					f"[QKD-Sensitivity] Cenario={scenario} "
					f"(SAEs: {sae_alice}/{sae_bob})"
				)

				try:
					self.setup_environment(tr, sae_alice, sae_bob)

					self.running = True
					mon_thread = threading.Thread(
						target=self.monitor_resources_thread,
						args=(scenario_folder,),
					)
					mon_thread.start()

					try:
						for i in range(1, self.iterations + 1):
							self.run_iperf_test(i, scenario_folder)
							time.sleep(5)

						if os.path.exists(METRICS_FILE):
							shutil.copy(
								METRICS_FILE,
								os.path.join(scenario_folder, "sdn_metrics.csv"),
							)

					finally:
						self.running = False
						mon_thread.join()

					summary_rows.append(
						{
							"scenario": scenario,
							"qkd_rate_bps": qkd_rate_bps,
							"rotation_interval_s": tr,
							"sae_alice": sae_alice,
							"sae_bob": sae_bob,
							"folder": scenario_folder,
						}
					)

				finally:
					compose_file = os.path.join(SCRIPT_DIR, "docker-compose.yml")
					self.run_cmd(f"docker compose -f {compose_file} down")
					time.sleep(3)

		if summary_rows:
			out_csv = os.path.join(RESULTS_BASE_DIR, "sensibilidade_summary.csv")
			with open(out_csv, "w", encoding="utf-8", newline="") as f:
				writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
				writer.writeheader()
				writer.writerows(summary_rows)
			print(f"[QKD-Sensitivity] Resumo salvo em {out_csv}")


def main() -> None:
	parser = argparse.ArgumentParser(description="Experimento 2 - Sensibilidade a taxa QKD")
	parser.add_argument("--profile", default="wan-fiber")
	parser.add_argument("--iterations", type=int, default=1)
	parser.add_argument("--duration", type=int, default=60)
	args = parser.parse_args()

	controller = QKDSensitivityController(args.duration, args.profile, args.iterations)
	controller.run_battery()


if __name__ == "__main__":
	main()
