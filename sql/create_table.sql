-- Run in Athena console after uploading Gold Parquet to
-- s3://alphavantage-medallion-kaif12589/gold/stock_analytics/
-- Do NOT run these together - run each statement separately.

CREATE EXTERNAL TABLE alphavantage_db.gold_stock_analytics (
    price_date date,
    open double,
    high double,
    low double,
    close double,
    volume bigint,
    ingested_at timestamp,
    daily_return_pct double,
    moving_avg_7d double,
    moving_avg_30d double,
    volume_avg_7d double,
    volatility_30d double,
    price_range_pct double,
    computed_at timestamp
)
PARTITIONED BY (symbol string)
STORED AS PARQUET
LOCATION 's3://alphavantage-medallion-kaif12589/gold/stock_analytics/'

MSCK REPAIR TABLE alphavantage_db.gold_stock_analytics