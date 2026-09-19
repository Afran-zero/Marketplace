SELECT price_date, open, high, low, close, volume, ingested_at,
    daily_return_pct, moving_avg_7d, moving_avg_30d, volume_avg_7d,
    volatility_30d, price_range_pct, computed_at
FROM alphavantage_db.gold_stock_analytics
WHERE symbol = '{symbol}'
ORDER BY price_date DESC
LIMIT {days}