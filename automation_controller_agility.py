#!/usr/bin/env python3
"""
Bateria B — Agilidade Criptográfica

Objetivo: Provar que o SDKM é algoritmo-agnóstico
- Nenhuma reconfiguração do plano de dados
- Overhead negligenciável independente do algoritmo PQC
- Seamless algorithm agility

Variável independente: Algoritmo PQC (para geração de chaves híbridas)
- ML-KEM-768 (padrão NIST)
- BIKE-L1 / BIKE-L3
- HQC-128 / HQC-256
- FrodoKEM-640-AES / FrodoKEM-976-AES
- Classic-McEliece-348864 / Classic-McEliece-460896

Métricas coletadas:
- Latência de hibridização (HKDF_MIX)
- Latência total de ciclo (HYBRIDIZATION_OVERHEAD)
- Throughput (iperf3)
- CPU do orquestrador
"""

import subprocess
import time
import json
import os
import shutil
import threading
import argparse
import logging
import csv
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÕES DO EXPERIMENTO DE AGILIDADE ---
PQC_ALGORITHMS = [
    "ML-KEM-768",           # NIST Standard
    "BIKE-L1",
    "BIKE-L3", 
    "HQC-128",
    "HQC-256",
    "FrodoKEM-640-AES",
    "FrodoKEM-976-AES",
    "Classic-McEliece-348864",
    "Classic-McEliece-460896"
]

ROTATION_INTERVAL = 10  # Fixo para agilidade
TEST_DURATION = 30      # Segundos por teste

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_BASE_DIR = os.path.join(SCRIPT_DIR, "teste_agility")
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "scripts")
METRICS_FILE = os.path.join(SCRIPT_DIR, "scripts", "experiment_metrics.csv")
RESOURCE_FILE = "resource_metrics.csv"

logging.basicConfig(
    level=logging.INFO,
    format='[Agility-Bench] %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Agility")

class AgilityController:
    """Controller para Bateria B — Agilidade Criptográfica"""
    
    def __init__(self, iterations=3):
        self.iterations = iterations
        self.running = True
        self.logical_nodes = ['alice', 'bob', 'carol', 'dave']
        self.container_map = {node: node for node in self.logical_nodes}
        self.real_containers = list(self.container_map.values())
        self.orchestrator_name = "orchestrator"
        self.all_containers = self.real_containers + [self.orchestrator_name]
        
        # Sumário de resultados
        self.agility_summary = []

    def run_cmd(self, cmd, env=None, detached=False):
        """Executa comando shell"""
        try:
            if detached:
                return subprocess.Popen(
                    cmd, shell=True, env=env, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            return subprocess.run(
                cmd, shell=True, env=env, 
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao executar '{cmd}': {e.stderr}")
            return None

    def docker_exec(self, logical_name, cmd, detached=False):
        """Executa comando dentro de container"""
        container = self.container_map.get(logical_name)
        detach_flag = "-d " if detached else ""
        full_cmd = f"docker exec {detach_flag}{container} {cmd}"
        return self.run_cmd(full_cmd)

    def setup_environment(self, pqc_algo):
        """
        Prepara ambiente com algoritmo PQC específico.
        Variável de ambiente PQC_ALGO é configurada automaticamente.
        """
        logger.info(f"🔐 Preparando ambiente para PQC_ALGO = {pqc_algo}...")
        
        env = os.environ.copy()
        env["ROTATION_INTERVAL"] = str(ROTATION_INTERVAL)
        env["PQC_ALGO"] = pqc_algo
        
        compose_file = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
        
        # Derruba containers anteriores
        self.run_cmd(f"docker compose -f {compose_file} down", env=env)
        time.sleep(2)
        
        # Sobe com novo PQC
        self.run_cmd(f"docker compose -f {compose_file} up -d", env=env)
        
        logger.info("⏳ Aguardando estabilização (30s)...")
        time.sleep(30)

    def monitor_resources_thread(self, pqc_algo_folder):
        """Monitora CPU/memória do orquestrador durante teste"""
        res_file = os.path.join(pqc_algo_folder, RESOURCE_FILE)
        with open(res_file, 'w') as f:
            f.write("timestamp,container,cpu_perc,mem_mib\n")
            
        while self.running:
            try:
                ts = time.time()
                cmd = (
                    "docker stats " + 
                    " ".join([self.orchestrator_name]) + 
                    " --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}'"
                )
                res = self.run_cmd(cmd)
                if res and res.stdout:
                    with open(res_file, 'a') as f:
                        for line in res.stdout.strip().split('\n'):
                            parts = line.split(',')
                            if len(parts) >= 3:
                                name = parts[0].replace('/', '')
                                cpu = parts[1].replace('%', '')
                                mem = parts[2].split('/')[0].strip().replace('MiB', '').replace('GiB', '')
                                f.write(f"{ts},{name},{cpu},{mem}\n")
            except Exception as e:
                logger.debug(f"Erro no monitoramento: {e}")
            time.sleep(1)

    def run_iperf_tests(self, iteration, folder):
        """Executa teste de throughput com iperf3"""
        logger.info(f"📊 [Iter {iteration}] Iniciando teste de vazão ({TEST_DURATION}s)...")
        
        # Inicia servidor iperf3 em bob
        self.docker_exec("bob", "iperf3 -s -D", detached=True)
        time.sleep(1)
        
        # Teste: alice -> bob
        target_ip = "192.168.100.11"
        cmd = f"iperf3 -c {target_ip} -t {TEST_DURATION} -J"
        res = self.docker_exec("alice", cmd)
        
        if res and res.stdout:
            file_name = f"throughput_iter_{iteration}.json"
            try:
                with open(os.path.join(folder, file_name), 'w') as f:
                    f.write(res.stdout)
                logger.info(f"✓ Throughput [Iter {iteration}] salvo")
            except Exception as e:
                logger.warning(f"⚠️ [Iter {iteration}] Erro ao salvar throughput: {e}")
        else:
            logger.warning(f"⚠️ [Iter {iteration}] Teste iperf3 falhou")

    def extract_metrics_from_sdn(self, sdn_metrics_file):
        """
        Extrai métricas-chave do arquivo de métricas do SDN Controller.
        Calcula média de latência de hibridização e overhead total.
        """
        try:
            hkdf_mix_times = []
            hybridization_overheads = []
            
            with open(sdn_metrics_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    event = row.get('event_type', '')
                    
                    if event == 'HKDF_MIX':
                        try:
                            hkdf_mix_times.append(float(row.get('value_ms', 0)))
                        except ValueError:
                            pass
                    
                    elif event == 'HYBRIDIZATION_OVERHEAD':
                        try:
                            hybridization_overheads.append(float(row.get('value_ms', 0)))
                        except ValueError:
                            pass
            
            # Calcula estatísticas
            avg_hkdf = sum(hkdf_mix_times) / len(hkdf_mix_times) if hkdf_mix_times else 0
            max_hkdf = max(hkdf_mix_times) if hkdf_mix_times else 0
            min_hkdf = min(hkdf_mix_times) if hkdf_mix_times else 0
            
            avg_overhead = sum(hybridization_overheads) / len(hybridization_overheads) if hybridization_overheads else 0
            max_overhead = max(hybridization_overheads) if hybridization_overheads else 0
            min_overhead = min(hybridization_overheads) if hybridization_overheads else 0
            
            return {
                'avg_hkdf_mix_ms': round(avg_hkdf, 3),
                'max_hkdf_mix_ms': round(max_hkdf, 3),
                'min_hkdf_mix_ms': round(min_hkdf, 3),
                'count': len(hkdf_mix_times),
                'avg_total_overhead_ms': round(avg_overhead, 3),
                'max_total_overhead_ms': round(max_overhead, 3),
                'min_total_overhead_ms': round(min_overhead, 3)
            }
        except Exception as e:
            logger.error(f"Erro ao extrair métricas SDN: {e}")
            return {}

    def extract_cpu_metrics(self, resource_file):
        """Extrai CPU média do orquestrador durante teste"""
        try:
            cpu_values = []
            with open(resource_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        cpu = float(row.get('cpu_perc', '0').replace('%', ''))
                        if cpu > 0:
                            cpu_values.append(cpu)
                    except ValueError:
                        pass
            
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            max_cpu = max(cpu_values) if cpu_values else 0
            
            return {
                'avg_cpu_perc': round(avg_cpu, 2),
                'max_cpu_perc': round(max_cpu, 2)
            }
        except Exception as e:
            logger.error(f"Erro ao extrair métricas CPU: {e}")
            return {}

    def run_agility_battery(self):
        """Executa bateria de testes de agilidade para todos os algoritmos PQC"""
        if not os.path.exists(RESULTS_BASE_DIR):
            os.makedirs(RESULTS_BASE_DIR)

        logger.info(f"\n{'='*70}")
        logger.info(f"{'BATERIA B — AGILIDADE CRIPTOGRÁFICA':^70}")
        logger.info(f"{'Variável: PQC_ALGO (hibridização)':^70}")
        logger.info(f"{'='*70}\n")

        # Arquivo de sumário
        summary_file = os.path.join(RESULTS_BASE_DIR, "agility_summary.csv")
        summary_rows = []

        for pqc_algo in PQC_ALGORITHMS:
            logger.info(f"\n{'='*70}")
            logger.info(f"PQC ALGORITHM: {pqc_algo}")
            logger.info(f"{'='*70}")
            
            pqc_folder = os.path.join(RESULTS_BASE_DIR, f"pqc_{pqc_algo.replace('/', '_')}")
            os.makedirs(pqc_folder, exist_ok=True)
            
            try:
                # Setup com novo PQC
                self.setup_environment(pqc_algo)
                
                # Monitor de recursos
                self.running = True
                mon_thread = threading.Thread(
                    target=self.monitor_resources_thread,
                    args=(pqc_folder,)
                )
                mon_thread.start()
                
                try:
                    # Executa iterações de teste
                    for i in range(1, self.iterations + 1):
                        logger.info(f"\n[Iteração {i}/{self.iterations}]")
                        self.run_iperf_tests(i, pqc_folder)
                        time.sleep(5)
                    
                    # Coleta métricas do SDN Controller
                    if os.path.exists(METRICS_FILE):
                        sdn_metrics_dest = os.path.join(pqc_folder, "sdn_metrics.csv")
                        shutil.copy(METRICS_FILE, sdn_metrics_dest)
                        logger.info(f"✅ Métricas SDN copiadas")
                        
                        # Extrai e calcula médias
                        sdn_data = self.extract_metrics_from_sdn(sdn_metrics_dest)
                    else:
                        sdn_data = {}
                        logger.warning("⚠️ Arquivo de métricas SDN não encontrado")
                    
                    # Extrai CPU
                    cpu_data = self.extract_cpu_metrics(
                        os.path.join(pqc_folder, RESOURCE_FILE)
                    )
                    
                    # Monta linha de sumário
                    summary_row = {
                        'pqc_algorithm': pqc_algo,
                        **sdn_data,
                        **cpu_data
                    }
                    summary_rows.append(summary_row)
                    
                    # Log resumido
                    logger.info(f"\n📊 RESUMO [{pqc_algo}]:")
                    logger.info(f"   Hybridization HKDF:  {sdn_data.get('avg_hkdf_mix_ms', 'N/A')} ms (avg)")
                    logger.info(f"   Total Overhead:      {sdn_data.get('avg_total_overhead_ms', 'N/A')} ms (avg)")
                    logger.info(f"   CPU Orquestrador:    {cpu_data.get('avg_cpu_perc', 'N/A')}% (avg)")
                    
                finally:
                    self.running = False
                    mon_thread.join()
                    
            except Exception as e:
                logger.error(f"❌ Erro ao testar {pqc_algo}: {e}")
                summary_rows.append({'pqc_algorithm': pqc_algo, 'error': str(e)})
            
            finally:
                # Derruba containers
                compose_file = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
                self.run_cmd(f"docker compose -f {compose_file} down")
                time.sleep(3)

        # Salva sumário
        if summary_rows:
            fieldnames = ['pqc_algorithm', 'avg_hkdf_mix_ms', 'max_hkdf_mix_ms', 
                         'min_hkdf_mix_ms', 'count', 'avg_total_overhead_ms',
                         'max_total_overhead_ms', 'min_total_overhead_ms',
                         'avg_cpu_perc', 'max_cpu_perc', 'error']
            
            with open(summary_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
                writer.writeheader()
                writer.writerows(summary_rows)
            
            logger.info(f"\n✅ Sumário salvo em: {summary_file}")

        # Log final
        logger.info(f"\n{'='*70}")
        logger.info(f"{'BATERIA CONCLUÍDA':^70}")
        logger.info(f"{'Resultados em: ' + RESULTS_BASE_DIR:^70}")
        logger.info(f"{'='*70}\n")

        return summary_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bateria B — Agilidade Criptográfica (varia PQC_ALGO para hibridização)"
    )
    parser.add_argument(
        "--iterations", 
        type=int, 
        default=3,
        help="Número de iterações por algoritmo PQC (padrão: 3)"
    )
    parser.add_argument(
        "--pqcs",
        nargs='+',
        help="Lista de PQC algorithms customizada (espaço-separado). Padrão: todos"
    )
    
    args = parser.parse_args()
    
    # Sobrescreve lista de PQC algorithms se fornecida
    if args.pqcs:
        PQC_ALGORITHMS = args.pqcs
        logger.info(f"Usando PQC algorithms customizados: {PQC_ALGORITHMS}")
    
    controller = AgilityController(iterations=args.iterations)
    summary = controller.run_agility_battery()
    
    # Imprime sumário tabular
    logger.info("\nSUMÁRIO FINAL DE AGILIDADE:")
    logger.info("-" * 100)
    logger.info(f"{'PQC Algorithm':<30} {'Hybrid(ms)':<15} {'Total(ms)':<15} {'CPU(%)':<10}")
    logger.info("-" * 100)
    
    for row in summary:
        pqc = row.get('pqc_algorithm', 'N/A')
        hkdf = row.get('avg_hkdf_mix_ms', 'N/A')
        total = row.get('avg_total_overhead_ms', 'N/A')
        cpu = row.get('avg_cpu_perc', 'N/A')
        logger.info(f"{pqc:<30} {str(hkdf):<15} {str(total):<15} {str(cpu):<10}")
    
    logger.info("-" * 100)

    logger.info(" Bateria de Agilidade Criptográfica Finalizada!")

if __name__ == "__main__":
    main()