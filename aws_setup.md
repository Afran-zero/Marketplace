
```markdown
# AWS Setup Guide — MarketPlus Medallion Pipeline

This document records the exact AWS configuration used to build the 
cloud side of the MarketPlus pipeline. It covers:

- IAM user and policy
- S3 bucket and folder structure
- Lambda function for daily ingestion
- EventBridge Scheduler for the daily trigger and 30-day auto-stop
- CloudWatch log retention
- Glue Data Catalog + Athena table for querying Gold Parquet
- Verification steps

All commands use the **AWS Console** unless otherwise noted. 
Region used throughout: **us-east-1**.

---

## 1. IAM Setup

### 1.1 Create the S3 Bucket First

Bucket names must be globally unique. This guide assumes:

```
alphavantage-medallion-kaif12589
```

**Steps:**
1. Go to **S3 Console** → **Create bucket**
2. **Bucket name:** `alphavantage-medallion-kaif12589`
3. **AWS Region:** `us-east-1`
4. Leave everything else default
5. Click **Create bucket**

The folder structure is created implicitly when objects are uploaded 
with the corresponding prefixes. Planned prefixes:

```
bronze/alpha_vantage/daily_prices/ingest_date=YYYY-MM-DD/{SYMBOL}.json
silver/daily_prices/ingest_date=YYYY-MM-DD/symbol={SYMBOL}/*.parquet
gold/stock_analytics/ingest_date=YYYY-MM-DD/symbol={SYMBOL}/*.parquet
athena-results/
```

### 1.2 Create the IAM Policy

**Policy name:** `AlphaVantageProjectPolicy`

**Steps:**
1. Go to **IAM Console** → **Policies** → **Create policy**
2. Switch to the **JSON** tab
3. Paste this policy (replace `YOUR-BUCKET-NAME` with the real name):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::YOUR-BUCKET-NAME",
                "arn:aws:s3:::YOUR-BUCKET-NAME/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "logs:*",
            "Resource": "*"
        }
    ]
}
```

4. **Policy name:** `AlphaVantageProjectPolicy`
5. Click **Create policy**

### 1.3 Create the IAM User

**User name:** `alphavantage_dev_user`

**Steps:**
1. Go to **IAM Console** → **Users** → **Create user**
2. **User name:** `alphavantage_dev_user`
3. **Do NOT** enable console access (programmatic only)
4. Click **Next**
5. Choose **Attach policies directly**
6. Search for `AlphaVantageProjectPolicy` and check it
7. Click **Next** → **Create user**

### 1.4 Generate Access Keys

1. Click on `alphavantage_dev_user`
2. Go to the **Security credentials** tab
3. Click **Create access key**
4. Choose **Command Line Interface (CLI)**
5. Confirm and proceed
6. **Download the .csv** — this is the only time the Secret Access Key 
   is shown
7. Save the keys somewhere safe

These keys are used by:
- The local Prefect block `aws-credentials`
- Any local scripts using boto3

### 1.5 Attach Lambda Execution Policy (Deferred)

This is done in section 3.4, after the Lambda is created.

---

## 2. S3 Bucket Layout

After all steps in this document are complete, the bucket contains:

```
alphavantage-medallion-kaif12589/
├── athena-results/                          # Athena query outputs
├── bronze/
│   └── alpha_vantage/
│       └── daily_prices/
│           └── ingest_date=YYYY-MM-DD/
│               ├── AAPL.json
│               ├── MSFT.json
│               └── ... (20 symbols total)
├── silver/
│   └── daily_prices/
│       └── ingest_date=YYYY-MM-DD/
│           └── symbol=AAPL/
│               └── part-*.snappy.parquet
└── gold/
    └── stock_analytics/
        └── ingest_date=YYYY-MM-DD/
            └── symbol=AAPL/
                └── part-*.snappy.parquet
```

---

## 3. Lambda Function — Daily Ingestion

### 3.1 Create the Lambda

1. Go to **Lambda Console** → **Create function**
2. **Author from scratch**
3. **Function name:** `AlphaVantageIngestionLambda`
4. **Runtime:** Python 3.12
5. **Architecture:** x86_64
6. **Permissions:** Choose **Create a new role with basic Lambda permissions**
7. Click **Create function**

### 3.2 Lambda Function Code

Replace the default `lambda_function.py` with:

```python
import json
import os
import time
import urllib.request
import boto3
from datetime import datetime, timezone

API_KEY = os.environ['ALPHAVANTAGE_API_KEY']
S3_BUCKET = os.environ['S3_BUCKET_NAME']
SYMBOLS = [s.strip() for s in os.environ.get('TICKER_SYMBOLS', 'IBM').split(',')]

s3 = boto3.client('s3')

def lambda_handler(event, context):
    ingest_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    results = []

    for symbol in SYMBOLS:
        url = (
            f"https://www.alphavantage.co/query?"
            f"function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
        )
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            results.append({"symbol": symbol, "status": "error", "error": str(e)})
            continue

        key = f"bronze/alpha_vantage/daily_prices/ingest_date={ingest_date}/{symbol}.json"

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(data),
            ContentType='application/json'
        )

        print(f"Uploaded {symbol} to s3://{S3_BUCKET}/{key}")
        results.append({"symbol": symbol, "status": "ok", "key": key})

        time.sleep(1.5)  # respect free-tier rate limit (~5 calls/min)

    return {"statusCode": 200, "body": json.dumps(results)}
```

Click **Deploy**.

### 3.3 Environment Variables

Go to **Configuration** → **Environment variables** → **Edit** and add:

| Key | Value |
|-----|-------|
| `ALPHAVANTAGE_API_KEY` | your Alpha Vantage API key |
| `S3_BUCKET_NAME` | `alphavantage-medallion-kaif12589` |
| `TICKER_SYMBOLS` | `IBM,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,JPM,V,MA,WMT,DIS,NFLX,ADBE,CRM,ORCL,CSCO,INTC,AMD` |

Save.

### 3.4 Attach S3 Permissions to the Lambda's Role

The Lambda's auto-created role has CloudWatch Logs permissions but 
**not** S3 permissions. Fix:

1. Open a new tab → **IAM Console** → **Roles**
2. Search for `AlphaVantageIngestionLambda` and click the role
3. Click **Add permissions** → **Attach policies directly**
4. Search for `AlphaVantageProjectPolicy` and attach it

### 3.5 Adjust the Timeout

Default timeout is 3 seconds — not enough for 20 symbols × 1.5s 
sleep + API calls.

1. Lambda → **Configuration** → **General configuration** → **Edit**
2. Set **Timeout** to **2 minutes**
3. Save

### 3.6 Test the Lambda

1. Go to the **Test** tab
2. Create a new event named `TestEvent` (leave JSON as `{}`)
3. Click **Test**

Expected output (with 20 symbols):
```json
[
  {"symbol": "IBM", "status": "ok", "key": "bronze/.../IBM.json"},
  {"symbol": "AAPL", "status": "ok", "key": "bronze/.../AAPL.json"},
  ...
]
```

Duration: ~30–35 seconds.

Verify in S3: `bronze/alpha_vantage/daily_prices/ingest_date=YYYY-MM-DD/` 
should contain 20 JSON files.

---

## 4. EventBridge Scheduler — Daily Trigger

### 4.1 Create the Schedule

1. Go to **EventBridge Scheduler** console
   (`https://console.aws.amazon.com/scheduler/home`)
2. **Create schedule**

**Step 1 — Schedule details**

| Field | Value |
|-------|-------|
| Name | `alphavantage-daily-ingest` |
| Schedule group | `default` |
| Schedule state | **Enabled** |

**Step 2 — Schedule pattern**

| Field | Value |
|-------|-------|
| Schedule pattern | Recurring schedule |
| Schedule type | Cron-based schedule |
| Cron expression | `30 21 * * ? *` |
| Flexible time window | Off |

This fires at **21:30 UTC every day** = 5:30 PM US Eastern, right 
after market close.

**Step 3 — Timeframe (auto-stop)**

| Field | Value |
|-------|-------|
| Timezone | UTC |
| Start date | default |
| End date | **30 days from creation** |

This is the auto-stop — the schedule simply stops firing after this 
date.

**Step 4 — Select target**

| Field | Value |
|-------|-------|
| Target API | AWS Lambda → Invoke |
| Function | `AlphaVantageIngestionLambda` |
| Payload | (leave blank) |

**Step 5 — Settings**

| Field | Value |
|-------|-------|
| Retry | ON |
| Maximum retries | 2 |
| Maximum event age | 1 hour |
| Permissions | **Create new role for this schedule** |

**Step 6 — Review and create**

Click **Create schedule**.

### 4.2 Verify

In the Scheduler console, the schedule appears as **Enabled**. 
Next invocation appears as `YYYY-MM-DD 21:30:00 UTC`.

---

## 5. CloudWatch Log Retention

By default, Lambda logs never expire. For a time-boxed project, cap 
them:

1. Go to **CloudWatch** → **Log groups**
2. Click `/aws/lambda/AlphaVantageIngestionLambda`
3. **Actions** → **Edit retention setting**
4. Choose **30 days**
5. Save

---

## 6. Glue Data Catalog + Athena

### 6.1 Set Athena Query Result Location

Before running any query in Athena:

1. Go to **Athena Console**
2. If prompted, click **Edit settings**
3. **Query result location:** `s3://alphavantage-medallion-kaif12589/athena-results/`
4. Save

### 6.2 Create the Glue Database

1. Go to **Glue Console** → **Databases** → **Add database**
2. **Name:** `alphavantage_db`
3. Create

### 6.3 Create the Athena Table

Run this in the Athena query editor. **Run each statement separately.**

**Statement 1 — CREATE TABLE**

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS alphavantage_db.gold_stock_analytics (
  `price_date`       DATE,
  `open`             DOUBLE,
  `high`             DOUBLE,
  `low`              DOUBLE,
  `close`            DOUBLE,
  `volume`           BIGINT,
  `ingested_at`      TIMESTAMP,
  `daily_return_pct` DOUBLE,
  `moving_avg_7d`    DOUBLE,
  `moving_avg_30d`   DOUBLE,
  `volume_avg_7d`    DOUBLE,
  `volatility_30d`   DOUBLE,
  `price_range_pct`  DOUBLE,
  `computed_at`      TIMESTAMP
)
PARTITIONED BY (
  `ingest_date` STRING,
  `symbol`      STRING
)
STORED AS PARQUET
LOCATION 's3://alphavantage-medallion-kaif12589/gold/stock_analytics/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');
```

**Statement 2 — Register partitions**

```sql
MSCK REPAIR TABLE alphavantage_db.gold_stock_analytics;
```

**Statement 3 — Test query**

```sql
SELECT symbol, price_date, close, moving_avg_7d, moving_avg_30d
FROM alphavantage_db.gold_stock_analytics
WHERE symbol = 'IBM'
ORDER BY price_date DESC
LIMIT 10;
```

### 6.4 Note on Partitions

`MSCK REPAIR TABLE` must be re-run whenever a new 
`ingest_date=YYYY-MM-DD/` prefix is uploaded to S3. The Gold Prefect 
task can do this automatically — or run it manually after each 
pipeline run.

### 6.5 Note on Glue Crawler

The Glue Crawler is an alternative to manually writing `CREATE TABLE` 
and `MSCK REPAIR`. On some newer AWS accounts, the crawler is blocked 
with `Account is denied access` until the account is verified. If the 
crawler is available, it can replace sections 6.3 and 6.4 entirely.

---

## 7. Verification Checklist

After all steps are done, verify:

| Check | Command / Location | Expected |
|-------|-------------------|----------|
| IAM user exists | IAM → Users | `alphavantage_dev_user` with `AlphaVantageProjectPolicy` attached |
| S3 bucket exists | S3 Console | `alphavantage-medallion-kaif12589` |
| Bronze data present | S3 → `bronze/alpha_vantage/daily_prices/` | At least one `ingest_date=YYYY-MM-DD/` folder with 20 JSON files |
| Lambda runs | Lambda → Test | Returns 20 "ok" statuses |
| Schedule armed | EventBridge Scheduler | Status Enabled, next run at 21:30 UTC |
| CloudWatch retention | CloudWatch → Log groups | 30 days |
| Glue database exists | Glue → Databases | `alphavantage_db` |
| Athena table exists | Athena → Database `alphavantage_db` | `gold_stock_analytics` |
| Athena query works | Athena editor | Row 1: IBM, 2026-09-17, 237.75, 241.42, 235.97 |

---

## 8. Cost Summary

For this project (30 days of operation):

| Service | Usage | Cost |
|---------|-------|------|
| S3 | < 10 MB | Free tier |
| Lambda | 30 invocations/month | Free tier |
| EventBridge Scheduler | 30 invocations | Free tier |
| CloudWatch Logs | < 100 MB | Free tier |
| Glue Data Catalog | < 1000 requests | Free tier |
| Athena | ~100 queries/day × 10 MB min | ~$0.01/month |

**Estimated total: under $0.05 for the entire project lifetime.**

---

## 9. Teardown (After 30 Days)

To shut everything down cleanly:

1. **Disable the EventBridge schedule** (it will also auto-disable 
   after the end date you set).
2. **Delete the Lambda function** (or leave it; it costs nothing at 
   rest).
3. **Empty and delete the S3 bucket** if you no longer need the data.
4. **Delete the IAM user** `alphavantage_dev_user`.
5. **Delete the IAM policy** `AlphaVantageProjectPolicy`.
6. **Delete the Glue database** `alphavantage_db`.
7. **Delete the CloudWatch log group** if you want a clean slate.

If keeping the S3 bucket for archival:
- Consider a **lifecycle rule** to move Bronze to Glacier after 90 days.

---

## Appendix A: Full IAM Policy JSON

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::alphavantage-medallion-kaif12589",
                "arn:aws:s3:::alphavantage-medallion-kaif12589/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "logs:*",
            "Resource": "*"
        }
    ]
}
```

If you later enable FastAPI to query Athena from the same IAM user, 
extend the policy with:

```json
{
    "Effect": "Allow",
    "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution",
        "athena:GetWorkGroup",
        "athena:ListQueryExecutions"
    ],
    "Resource": "*"
},
{
    "Effect": "Allow",
    "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartitions"
    ],
    "Resource": "*"
}
```

## Appendix B: Lambda Environment Variables

| Key | Example Value |
|-----|---------------|
| `ALPHAVANTAGE_API_KEY` | `JG6IIRX0B4W51F56` |
| `S3_BUCKET_NAME` | `alphavantage-medallion-kaif12589` |
| `TICKER_SYMBOLS` | `IBM,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,JPM,V,MA,WMT,DIS,NFLX,ADBE,CRM,ORCL,CSCO,INTC,AMD` |

## Appendix C: EventBridge Cron Reference

| Cron | Meaning |
|------|---------|
| `30 21 * * ? *` | Daily at 21:30 UTC |
| `0 */2 * * ? *` | Every 2 hours |
| `0 14 ? * MON-FRI *` | Weekdays at 14:00 UTC |

The `?` character means "no specific value" and is required in one 
of the day-of-month or day-of-week fields.
```

---

### 📌 How to Use This File

1. Save it as `AWS_SETUP.md` in the root of `G:\data-Engineer\marketplus\`
2. Add it to your project README as a link: `[AWS Setup Guide](./AWS_SETUP.md)`
3. Commit it to Git — it doubles as documentation and a portfolio artifact
4. If you ever tear down and rebuild, you have an exact script to follow

