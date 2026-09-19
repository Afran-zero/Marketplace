WITH latest AS (
    SELECT symbol, price_date, close, daily_return_pct,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY price_date DESC) AS rn
    FROM alphavantage_db.gold_stock_analytics
)
SELECT symbol, price_date, close, daily_return_pct
FROM latest
WHERE rn = 1
ORDER BY daily_return_pct {order_dir}
LIMIT {limit}