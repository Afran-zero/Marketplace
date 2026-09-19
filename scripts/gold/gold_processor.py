import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from prefect_aws import AwsCredentials
from pyspark.sql import SparkSession
from pyspark.sql import Window
from pyspark.sql.functions import (
    col, lag, avg, stddev, round as spark_round, current_timestamp
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SILVER_PATH = PROJECT_ROOT / "data" / "silver"
GOLD_PATH = PROJECT_ROOT / "data" / "gold"


def get_spark():
    return (
        SparkSession.builder
        .appName("GoldProcessor")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "1g")
        .getOrCreate()
    )


def main():
    print(f"[gold] Reading Silver from {SILVER_PATH}")
    if not SILVER_PATH.exists():
        print(f"[gold] ERROR: {SILVER_PATH} does not exist.")
        sys.exit(1)

    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    silver_df = spark.read.parquet(str(SILVER_PATH))
    print(f"[gold] Silver rows: {silver_df.count()}")

    # ------------------------------------------------------------
    # Define a window: for each symbol, ordered by date.
    # All rolling calculations use this window.
    # ------------------------------------------------------------
    window_sym = Window.partitionBy("symbol").orderBy("price_date")

    # ------------------------------------------------------------
    # 1. Daily return: (close_today - close_yesterday) / close_yesterday * 100
    # ------------------------------------------------------------
    gold_df = silver_df.withColumn(
        "prev_close", lag("close").over(window_sym)
    ).withColumn(
        "daily_return_pct",
        spark_round(
            (col("close") - col("prev_close")) / col("prev_close") * 100, 4
        )
    )

    # ------------------------------------------------------------
    # 2. Rolling averages — 7-day and 30-day, using a window that
    #    looks BACKWARDS by (N-1) rows including the current row.
    # ------------------------------------------------------------
    window_7d = window_sym.rowsBetween(-6, 0)
    window_30d = window_sym.rowsBetween(-29, 0)

    gold_df = (
        gold_df
        .withColumn("moving_avg_7d",
                    spark_round(avg("close").over(window_7d), 4))
        .withColumn("moving_avg_30d",
                    spark_round(avg("close").over(window_30d), 4))
        .withColumn("volume_avg_7d",
                    spark_round(avg("volume").over(window_7d), 2))
    )

    # ------------------------------------------------------------
    # 3. Volatility: stddev of daily_return over trailing 30 days.
    #    (Needs another pass because daily_return is now a column.)
    # ------------------------------------------------------------
    gold_df = gold_df.withColumn(
        "volatility_30d",
        spark_round(stddev("daily_return_pct").over(window_30d), 4)
    )

    # ------------------------------------------------------------
    # 4. Price range: how wide was the day's swing, as % of close.
    # ------------------------------------------------------------
    gold_df = gold_df.withColumn(
        "price_range_pct",
        spark_round((col("high") - col("low")) / col("close") * 100, 4)
    )

    # ------------------------------------------------------------
    # 5. Cleanup: drop intermediate, add timestamp, sort for readability.
    # ------------------------------------------------------------
    gold_df = (
        gold_df
        .drop("prev_close")
        .withColumn("computed_at", current_timestamp())
        .orderBy("symbol", "price_date")
    )

    row_count = gold_df.count()
    print(f"[gold] Gold rows: {row_count}")

    GOLD_PATH.mkdir(parents=True, exist_ok=True)
    (
        gold_df
        .write
        .mode("overwrite")
        .partitionBy("symbol")
        .parquet(str(GOLD_PATH))
    )

    print(f"[gold] Wrote Gold Parquet to {GOLD_PATH}")

    # ------------------------------------------------------------
    # Push Gold Parquet to S3
    # ------------------------------------------------------------
    ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s3_prefix = f"gold/stock_analytics/ingest_date={ingest_date}/"

    print(f"[gold] Uploading Parquet to s3://.../{s3_prefix}")

    creds = AwsCredentials.load("aws-credentials")
    s3 = creds.get_boto3_session().client("s3")
    bucket_name = "alphavantage-medallion-kaif12589"

    uploaded = 0
    for root, _, files in os.walk(GOLD_PATH):
        for fname in files:
            if not fname.endswith(".parquet"):
                continue
            local_file = Path(root) / fname
            relative = local_file.relative_to(GOLD_PATH)
            s3_key = s3_prefix + str(relative).replace("\\", "/")
            s3.upload_file(str(local_file), bucket_name, s3_key)
            uploaded += 1

    print(f"[gold] Uploaded {uploaded} Parquet files to S3")
    spark.stop()


if __name__ == "__main__":
    main()