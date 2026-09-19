# Runs the Medallion pipeline end-to-end.
# Usage: .\run_pipeline.ps1

$ProjectRoot = "G:\data-Engineer\marketplus"
Set-Location $ProjectRoot

& "$ProjectRoot\.venv\Scripts\Activate.ps1"

# Command 1 is standalone. Clear an inherited local API URL so Prefect can
# create its temporary API for this one-shot flow run.
$env:PREFECT_API_URL = $null
$env:PREFECT_SERVER_EPHEMERAL_ENABLED = "true"

python "$ProjectRoot\flows\medallion_pipeline.py"
