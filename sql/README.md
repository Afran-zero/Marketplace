# SQL Queries

All queries target `alphavantage_db.gold_stock_analytics` in Athena. The
Python backend reads these UTF-8 files and substitutes the listed placeholders
with safe values before submitting each query. Athena does not parameterize
these templates directly.

| File | Purpose | Returned columns | Parameters |
|---|---|---|---|
| `symbols_latest.sql` | Latest row for every symbol | `symbol`, `price_date`, `close`, `daily_return_pct`, `volatility_30d` | None |
| `symbol_history.sql` | Recent history for one symbol | `price_date`, `open`, `high`, `low`, `close`, `volume`, `daily_return_pct`, `moving_avg_7d`, `moving_avg_30d`, `volatility_30d` | `{symbol}`, `{days}` |
| `top_movers.sql` | Latest biggest gainers or losers | `symbol`, `price_date`, `close`, `daily_return_pct` | `{order_dir}`, `{limit}` |
| `most_volatile.sql` | Latest symbols ordered by volatility | `symbol`, `price_date`, `close`, `volatility_30d` | `{limit}` |
| `download_symbol.sql` | CSV-ready history for one symbol | `price_date`, `open`, `high`, `low`, `close`, `volume`, `ingested_at`, `daily_return_pct`, `moving_avg_7d`, `moving_avg_30d`, `volume_avg_7d`, `volatility_30d`, `price_range_pct`, `computed_at` | `{symbol}`, `{days}` |

All statements use Athena's Presto/Trino-compatible SQL dialect and omit a
trailing semicolon so they can be formatted by the backend.