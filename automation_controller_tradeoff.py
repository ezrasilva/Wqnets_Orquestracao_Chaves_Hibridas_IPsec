import subprocess
import time
import json
import os
import shutil
import threading
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÕES DO EXPERIMENTO DE TRADE-OFF ---
INTERVALS = [2, 5, 15, 10, 30, 60]  # Intervalos de rotação em segundos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_BASE_DIR = os.path.join(SCRIPT_DIR, "teste_tradeoff")
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "scripts")
METRICS_FILE = os.path.join(SCRIPT_DIR, "scripts", "experiment_metrics.csv")
RESOURCE_FILE = "resource_metrics.csv"

logging.basicConfig(
    level=logging.INFO,
    format='[TradeOff-Bench] %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TradeOff")

class TradeOffController:
    def __init__(self, duration, profile, iterations):
        self.duration = duration
        self.profile = profile
        self.iterations = iterations
        self.running = True
        self.logical_nodes = ['alice', 'bob', 'carol', 'dave']
        self.container_map = {node: node for node in self.logical_nodes}
        self.real_containers = list(self.container_map.values())
        self.orchestrator_name = "orchestrator"
        self.all_containers = self.real_containers + [self.orchestrator_name]

    def run_cmd(self, cmd, env=None, detached=False):
        try:
            if detached:
                return subprocess.Popen(cmd, shell=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return subprocess.run(cmd, shell=True, env=env, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao executar '{cmd}': {e.stderr}")
            return None

    def docker_exec(self, logical_name, cmd, detached=False):
        container = self.container_map.get(logical_name)
        detach_flag = "-d " if detached else ""
        full_cmd = f"docker exec {detach_flag}{container} {cmd}"
        return self.run_cmd(full_cmd)

    def setup_environment(self, interval):
        logger.info(f"♻️  Preparando ambiente para INTERVALO = {interval}s...")
        
        # Define a variável de ambiente para o docker-compose e o orquestrador
        env = os.environ.copy()
        env["ROTATION_INTERVAL"] = str(interval)
        
        compose_file = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
        self.run_cmd(f"docker compose -f {compose_file} down", env=env)
        time.sleep(2)
        self.run_cmd(f"docker compose -f {compose_file} up -d", env=env)
        
        logger.info("⏳ Aguardando estabilização (30s)...")
        time.sleep(30)
        
        # Aplica perfil de rede WAN se necessário
        if self.profile != "perfect":
            containers_str = " ".join(self.real_containers)
            cmd = f"python3 {SCRIPTS_DIR}/simulate_network_conditions.py --profile {self.profile} --containers {containers_str}"
            self.run_cmd(cmd)

    def monitor_resources_thread(self, interval_folder):
        res_file = os.path.join(interval_folder, RESOURCE_FILE)
        with open(res_file, 'w') as f:
            f.write("timestamp,container,cpu_perc,mem_mib\n")
            
        while self.running:
            try:
                ts = time.time()
                cmd = "docker stats " + " ".join(self.all_containers) + " --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}'"
                res = self.run_cmd(cmd)
                if res and res.stdout:
                    with open(res_file, 'a') as f:
                        for line in res.stdout.strip().split('\n'):
                            parts = line.split(',')
                            if len(parts) >= 3:
                                name, cpu, mem = parts[0], parts[1].replace('%', ''), parts[2].split('/')[0].strip().replace('MiB', '').replace('GiB', '')
                                f.write(f"{ts},{name},{cpu},{mem}\n")
            except: pass
            time.sleep(1)

    def run_iperf_tests(self, iteration, folder):
        logger.info(f"🚀 [Iter {iteration}] Iniciando testes de vazão...")
        
        # Inicia servidor iperf3 em bob (em background)
        self.docker_exec("bob", "iperf3 -s -D", detached=True)
        time.sleep(1)  # Aguarda servidor iniciar
        
        # Executa teste de vazão TCP de alice para bob
        target_ip = "192.168.100.11"  # IP de bob
        cmd = f"iperf3 -c {target_ip} -t {self.duration} -J"
        res = self.docker_exec("alice", cmd)
        
        # Salva resultado
        if res and res.stdout:
            file_name = f"throughput_iter_{iteration}.json"
            with open(os.path.join(folder, file_name), 'w') as f:
                f.write(res.stdout)
        else:
            logger.warning(f"⚠️ [Iter {iteration}] Teste iperf3 falhou")

    def run_tradeoff_battery(self):
        if not os.path.exists(RESULTS_BASE_DIR):
            os.makedirs(RESULTS_BASE_DIR)

        for interval in INTERVALS:
            logger.info(f"\n{'='*50}\nBATERIA: INTERVALO {interval}s\n{'='*50}")
            
            interval_folder = os.path.join(RESULTS_BASE_DIR, f"interval_{interval}s")
            os.makedirs(interval_folder, exist_ok=True)
            
            self.setup_environment(interval)
            
            self.running = True
            mon_thread = threading.Thread(target=self.monitor_resources_thread, args=(interval_folder,))
            mon_thread.start()
            
            try:
                for i in range(1, self.iterations + 1):
                    self.run_iperf_tests(i, interval_folder)
                    time.sleep(5)
                
                # Coleta o arquivo de métricas gerado pelo SDN Controller no container
                if os.path.exists(METRICS_FILE):
                    shutil.copy(METRICS_FILE, os.path.join(interval_folder, "sdn_metrics.csv"))
                    logger.info(f"✅ Métricas SDN copiadas para {interval_folder}")

            finally:
                self.running = False
                mon_thread.join()
                compose_file = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
                self.run_cmd(f"docker compose -f {compose_file} down")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="wan-fiber")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    controller = TradeOffController(args.duration, args.profile, args.iterations)
    controller.run_tradeoff_battery()