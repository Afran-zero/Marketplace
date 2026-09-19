# MarketPlus

MarketPlus is a local stock analytics dashboard backed by AWS S3, Athena,
Glue, FastAPI, React, Spark, and Prefect. It uses a Bronze -> Silver -> Gold
medallion architecture.

## Architecture

```text
AWS CLOUD

Alpha Vantage API
       |
       v
EventBridge Scheduler -> Lambda ingestion -> S3 Bronze (raw JSON)
                                      |
                                      v
                              S3 Silver (Parquet)
                                      |
                                      v
                               S3 Gold (Parquet)
                                      |
                                      v
                         Glue Data Catalog + Athena
                                      |
                                      v
LOCAL WINDOWS MACHINE

Prefect medallion flow -> local Spark processing -> S3 Silver and Gold

Athena <- FastAPI backend <- React dashboard
             |
             +-> Prefect task and flow observability
```

Cloud ingestion runs independently in AWS. The local pipeline only syncs the
Bronze data and rebuilds Silver and Gold when you request it.

## Quick Start

From the repository root:

```powershell
cd "G:\data-Engineer\marketplus"
```

### 1. Rebuild the data pipeline

This is a one-shot command. It runs Bronze synchronization, Silver processing,
and Gold processing in order, then exits:

```powershell
.\run_pipeline.ps1
```

The flow is named `medallion-pipeline` in Prefect and contains these tasks:

1. `sync-bronze` downloads new raw JSON objects from S3.
2. `process-silver` cleans and writes Silver Parquet.
3. `process-gold` calculates analytics and writes Gold Parquet.

Each processing stage uploads its Parquet output back to S3.

### 2. Start the dashboard

This starts Prefect, FastAPI, and Vite in separate PowerShell windows:

```powershell
.\run_dashboard.ps1
```

Open the dashboard here:

```text
http://localhost:5173
```

Service URLs:

| Service | URL |
|---|---|
| React dashboard | http://localhost:5173 |
| FastAPI backend | http://127.0.0.1:8000 |
| FastAPI health | http://127.0.0.1:8000/api/health |
| Prefect UI | http://127.0.0.1:4200 |

Close the three PowerShell windows, or press `Ctrl+C` in each, to stop the
dashboard services.

## Data Flow

### Cloud ingestion

EventBridge invokes the Lambda ingestion function after the US market close.
Lambda requests daily data for the configured symbols from Alpha Vantage and
writes raw responses to:

```text
s3://alphavantage-medallion-kaif12589/bronze/alpha_vantage/daily_prices/ingest_date=YYYY-MM-DD/
```

The cloud schedule and Lambda are independent of the local dashboard. They do
not need Prefect, FastAPI, or React to be running.

### Bronze to Silver

`sync_bronze.py` loads the Prefect `bronze-bucket` block, lists the Bronze S3
prefix, and downloads files that are not already present locally. The Silver
processor then:

- Reads the Bronze JSON with an explicit schema.
- Explodes the daily time-series map into rows.
- Casts prices, volume, and dates to the correct types.
- Deduplicates by `(symbol, price_date)`.
- Adds the ingestion timestamp.
- Writes partitioned Parquet to `data/silver/`.
- Uploads Silver files to S3.

### Silver to Gold

The Gold processor reads Silver Parquet and calculates analytics per symbol:

- `daily_return_pct`
- `moving_avg_7d`
- `moving_avg_30d`
- `volume_avg_7d`
- `volatility_30d`
- `price_range_pct`

Gold output is written to `data/gold/` and uploaded to:

```text
s3://alphavantage-medallion-kaif12589/gold/stock_analytics/ingest_date=YYYY-MM-DD/
```

## Dashboard API

FastAPI is in `backend/` and queries the Athena Gold table through Prefect
tasks and flows. Every dashboard query is therefore visible in the local
Prefect UI.

| Route | Purpose |
|---|---|
| `/api/health` | Backend health check |
| `/api/symbols` | Latest row for each symbol |
| `/api/symbol/{symbol}?days=30` | Historical price and analytics data |
| `/api/top-movers` | Top gainers and losers |
| `/api/most-volatile` | Most volatile symbols |
| `/api/download/{symbol}.csv?days=100` | CSV download for one symbol |

The frontend calls only FastAPI. It does not connect directly to Athena or S3.

## AWS Query Configuration

The dashboard expects:

| Setting | Value |
|---|---|
| S3 bucket | `alphavantage-medallion-kaif12589` |
| Glue database | `alphavantage_db` |
| Athena table | `gold_stock_analytics` |
| Athena results | `s3://alphavantage-medallion-kaif12589/athena-results/` |
| Prefect AWS block | `aws-credentials` |

AWS credentials are loaded through Prefect blocks rather than being hardcoded
in application code.

## Project Layout

| Area | Location |
|---|---|
| Pipeline flow | `flows/medallion_pipeline.py` |
| Pipeline launcher | `run_pipeline.ps1` |
| Dashboard launcher | `run_dashboard.ps1` |
| Bronze synchronization | `scripts/bronze/` |
| Silver processing | `scripts/silver/` |
| Gold processing | `scripts/gold/` |
| FastAPI backend | `backend/` |
| React frontend | `frontend/` |
| SQL definitions | `sql/` |
| Local staging data | `data/bronze/`, `data/silver/`, `data/gold/` |
| Prefect local state | `%USERPROFILE%\.prefect\prefect.db` |

## Manual Development Commands

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start only the backend:

```powershell
$env:PREFECT_API_URL = "http://127.0.0.1:4200/api"
$env:PREFECT_SERVER_EPHEMERAL_ENABLED = "false"
python -m uvicorn backend.main:app --port 8000
```

Start only the frontend:

```powershell
Set-Location frontend
npm install
npm run dev
```

If you use the optional Docker Compose Airflow stack, set its webserver secret
in the shell before starting it:

```powershell
$env:AIRFLOW__WEBSERVER__SECRET_KEY = "use-a-local-secret-value"
docker compose up
```

Build the frontend:

```powershell
Set-Location frontend
npm run build
```

On Windows, use `python -m uvicorn` and `python -m prefect` instead of relying
on launcher executables. Avoid `--reload` for the backend because it can start
multiple Prefect-related processes and cause local port conflicts.

## Operational Notes

- The pipeline is idempotent at the Bronze download step and skips files that
  already match the S3 object size.
- Silver deduplicates overlapping daily records before Gold calculations.
- Parquet and partitioned paths reduce storage and Athena scan cost.
- The local pipeline usually takes about 60-90 seconds, depending on Spark and
  S3 activity.
- The EventBridge schedule is separate from local processing and can be
  disabled independently in AWS.
- Run `scripts/maintenance/cleanup_prefect.py` occasionally to keep local
  Prefect history manageable.

## Troubleshooting

If the dashboard cannot load data:

1. Confirm Prefect is running at `http://127.0.0.1:4200`.
2. Confirm FastAPI responds at `/api/health`.
3. Confirm the `aws-credentials` Prefect block exists.
4. Confirm Athena can write to the configured results location.
5. Run the pipeline before opening the dashboard if Gold data is stale or
   missing.

If PowerShell blocks the launcher scripts, run once as your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
