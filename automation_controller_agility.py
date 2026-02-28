import subprocess
import os
import time
import shutil
import logging


ALGORITHMS = ["kyber768", "bike1-l1-cpa", "hqc-128-cpa", "frodokem-640-aes", "mceliece348864"]
RESULTS_BASE_DIR = "teste_agilidade"
ITERATIONS = 30  
ROTATION_INTERVAL = 30 

logging.basicConfig(level=logging.INFO, format='[Agility-Bench] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Agility")

def run_cmd(cmd, env=None):
    subprocess.run(cmd, shell=True, env=env)

def main():
    if not os.path.exists(RESULTS_BASE_DIR):
        os.makedirs(RESULTS_BASE_DIR)

    for algo in ALGORITHMS:
        logger.info(f"\n{'='*50}\nTESTANDO ALGORITMO: {algo}\n{'='*50}")
        
        algo_folder = os.path.join(RESULTS_BASE_DIR, algo)
        os.makedirs(algo_folder, exist_ok=True)
        
       
        env = os.environ.copy()
        env["PQC_ALGO"] = algo
        env["ROTATION_INTERVAL"] = str(ROTATION_INTERVAL)
        
        logger.info(f"[*] Reiniciando ambiente Docker para {algo}...")
        run_cmd("docker compose down", env=env)
        run_cmd("docker compose up -d", env=env)
        time.sleep(20)

        logger.info(f"[*] Iniciando 30 iterações de coleta para {algo}...")
        run_cmd(f"python3 automation_controller.py --iterations {ITERATIONS} --duration 30 --interval {ROTATION_INTERVAL}")

        
        if os.path.exists("scripts/experiment_metrics.csv"):
            shutil.copy("scripts/experiment_metrics.csv", os.path.join(algo_folder, "sdn_metrics.csv"))
        if os.path.exists("resource_metrics.csv"):
            shutil.copy("resource_metrics.csv", os.path.join(algo_folder, "resource_metrics.csv"))
            
        logger.info(f"✅ Dados de {algo} salvos em {algo_folder}")

    run_cmd("docker compose down")
    logger.info(" Bateria de Agilidade Criptográfica Finalizada!")

if __name__ == "__main__":
    main()