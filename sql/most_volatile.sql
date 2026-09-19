WITH latest AS (
    SELECT symbol, price_date, close, volatility_30d,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY price_date DESC) AS rn
    FROM alphavantage_db.gold_stock_analytics
)
SELECT symbol, price_date, close, volatility_30d
FROM latest
WHERE rn = 1
ORDER BY volatility_30d DESC
LIMIT {limit}