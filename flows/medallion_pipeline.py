import subprocess
from pathlib import Path

from prefect import flow, task

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")


def run_script(script_path: str, label: str):
    full_path = PROJECT_ROOT / script_path
    print(f"[{label}] Running {full_path}")
    result = subprocess.run(
        [PYTHON, str(full_path)],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed (exit {result.returncode})")


@task(name="sync-bronze", retries=2, retry_delay_seconds=30)
def sync_bronze():
    run_script("scripts/bronze/sync_bronze.py", "bronze")


@task(name="process-silver", retries=1, retry_delay_seconds=15)
def process_silver():
    run_script("scripts/silver/silver_processor.py", "silver")


@task(name="process-gold", retries=1, retry_delay_seconds=15)
def process_gold():
    run_script("scripts/gold/gold_processor.py", "gold")


@flow(name="medallion-pipeline", log_prints=True)
def medallion_pipeline():
    sync_bronze()
    process_silver()
    process_gold()


if __name__ == "__main__":
    medallion_pipeline()
