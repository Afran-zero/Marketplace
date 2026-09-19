WITH ranked AS (
    SELECT symbol, price_date, close, daily_return_pct, volatility_30d,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY price_date DESC) AS rn
    FROM alphavantage_db.gold_stock_analytics
)
SELECT symbol, price_date, close, daily_return_pct, volatility_30d
FROM ranked
WHERE rn = 1
ORDER BY symbol ASC