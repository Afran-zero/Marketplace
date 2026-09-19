SELECT price_date, open, high, low, close, volume, daily_return_pct,
    moving_avg_7d, moving_avg_30d, volatility_30d
FROM alphavantage_db.gold_stock_analytics
WHERE symbol = '{symbol}'
ORDER BY price_date DESC
LIMIT {days}