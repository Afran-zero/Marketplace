import sys
import glob as _glob
from pathlib import Path as _Path
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, explode, current_timestamp
from pyspark.sql.types import (
    StructType, StructField, StringType, MapType
)
import os
from datetime import datetime, timezone
import boto3
from prefect_aws import AwsCredentials


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRONZE_PATH = PROJECT_ROOT / "data" / "bronze"
SILVER_PATH = PROJECT_ROOT / "data" / "silver"


def get_spark():
    return (
        SparkSession.builder
        .appName("SilverProcessor")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .getOrCreate()
    )


BRONZE_SCHEMA = StructType([
    StructField("Meta Data", StructType([
        StructField("2. Symbol", StringType(), True),
    ]), True),
    StructField(
        "Time Series (Daily)",
        MapType(StringType(), MapType(StringType(), StringType())),
        True,
    ),
])


def main():
    print(f"[silver] Reading Bronze from {BRONZE_PATH}")
    if not BRONZE_PATH.exists():
        print(f"[silver] ERROR: {BRONZE_PATH} does not exist.")
        sys.exit(1)

    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    glob = str(BRONZE_PATH / "ingest_date=*" / "*.json")
    print(f"[silver] Glob pattern: {glob}")

    # Diagnostic: confirm files exist BEFORE handing to Spark
    matching_files = _glob.glob(glob)
    print(f"[silver] Python glob found {len(matching_files)} matching files")
    if not matching_files:
        print("[silver] ERROR: No files matched. Contents of BRONZE_PATH:")
        for p in _Path(BRONZE_PATH).iterdir():
            print(f"  {p}")
        sys.exit(1)

    bronze_df = (
        spark.read
        .option("multiLine", True)
        .schema(BRONZE_SCHEMA)
        .json(glob)
    )

    print(f"[silver] Bronze files loaded: {bronze_df.count()}")

    exploded = bronze_df.select(
        col("`Meta Data`.`2. Symbol`").alias("symbol"),
        explode(col("`Time Series (Daily)`")).alias("price_date", "ohlcv"),
    )

    silver_df = exploded.select(
        col("symbol"),
        to_date(col("price_date"), "yyyy-MM-dd").alias("price_date"),
        col("ohlcv.`1. open`").cast("double").alias("open"),
        col("ohlcv.`2. high`").cast("double").alias("high"),
        col("ohlcv.`3. low`").cast("double").alias("low"),
        col("ohlcv.`4. close`").cast("double").alias("close"),
        col("ohlcv.`5. volume`").cast("long").alias("volume"),
    )

    silver_df = (
        silver_df
        .dropDuplicates(["symbol", "price_date"])
        .withColumn("ingested_at", current_timestamp())
    )

    print(f"[silver] Rows after dedup: {silver_df.count()}")

    SILVER_PATH.mkdir(parents=True, exist_ok=True)
    (
        silver_df
        .write
        .mode("overwrite")
        .partitionBy("symbol")
        .parquet(str(SILVER_PATH))
    )

    print(f"[silver] Wrote Parquet to {SILVER_PATH}")
        # ------------------------------------------------------------
    # Push Silver Parquet to S3
    # ------------------------------------------------------------
    ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s3_prefix = f"silver/daily_prices/ingest_date={ingest_date}/"

    print(f"[silver] Uploading Parquet to s3://.../{s3_prefix}")

    creds = AwsCredentials.load("aws-credentials")
    s3 = creds.get_boto3_session().client("s3")
    bucket_name = "alphavantage-medallion-kaif12589"

    uploaded = 0
    for root, _, files in os.walk(SILVER_PATH):
        for fname in files:
            if not fname.endswith(".parquet"):
                continue
            local_file = Path(root) / fname
            relative = local_file.relative_to(SILVER_PATH)
            s3_key = s3_prefix + str(relative).replace("\\", "/")
            s3.upload_file(str(local_file), bucket_name, s3_key)
            uploaded += 1

    print(f"[silver] Uploaded {uploaded} Parquet files to S3")
    spark.stop()


if __name__ == "__main__":
    main()