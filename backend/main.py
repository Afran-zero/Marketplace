import csv
import io
import time
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.athena_client import AthenaQueryError, load_sql, query

app = FastAPI(title="MarketPlus API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_TTL_SECONDS = 300
CACHE: dict[str, dict[str, Any]] = {}

def get_cached(key: str, loader: Callable[[], Any]) -> Any:
    now = time.time()
    cached_item = CACHE.get(key)
    if cached_item and cached_item["expires_at"] > now:
        return cached_item["value"]

    value = loader()
    CACHE[key] = {"expires_at": now + CACHE_TTL_SECONDS, "value": value}
    return value


def sanitize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().replace("'", "''")
    if not cleaned:
        raise HTTPException(status_code=400, detail="Symbol is required.")
    return cleaned


def parse_days(days: str | None, default: int = 30, max_days: int = 100) -> int:
    try:
        value = int(days) if days is not None else default
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="days must be an integer") from exc

    if value < 1:
        value = 1
    if value > max_days:
        value = max_days
    return value


def handle_athena_error(action: Callable[[], Any]) -> Any:
    try:
        return action()
    except AthenaQueryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/symbols")
def get_symbols() -> list[dict[str, Any]]:
    sql_query = load_sql("symbols_latest")

    return handle_athena_error(
        lambda: get_cached("symbols_latest", lambda: query(sql_query))
    )


@app.get("/api/symbol/{symbol}")
def get_symbol_history(
    symbol: str = Path(..., description="Ticker symbol"),
    days: str | None = None,
) -> dict[str, Any]:
    safe_symbol = sanitize_symbol(symbol)
    limit = parse_days(days, default=30, max_days=100)

    sql_query = load_sql("symbol_history").format(symbol=safe_symbol, days=limit)

    def fetch() -> list[dict[str, Any]]:
        rows = query(sql_query)
        return list(reversed(rows))

    return {
        "symbol": safe_symbol.upper(),
        "days": limit,
        "data": handle_athena_error(fetch),
    }


@app.get("/api/top-movers")
def get_top_movers(limit: str | None = None) -> dict[str, list[dict[str, Any]]]:
    max_items = 20
    requested = parse_days(limit, default=5, max_days=max_items)

    def build_latest_query(order_dir: str) -> str:
        return load_sql("top_movers").format(order_dir=order_dir, limit=requested)

    def fetch() -> dict[str, list[dict[str, Any]]]:
        gainers = query(build_latest_query("DESC"))
        losers = query(build_latest_query("ASC"))
        return {"gainers": gainers, "losers": losers}

    return handle_athena_error(lambda: get_cached("top_movers", fetch))


@app.get("/api/most-volatile")
def get_most_volatile(limit: str | None = None) -> list[dict[str, Any]]:
    max_items = 20
    requested = parse_days(limit, default=5, max_days=max_items)
    sql_query = load_sql("most_volatile").format(limit=requested)

    return handle_athena_error(
        lambda: get_cached("most_volatile", lambda: query(sql_query))
    )


@app.get("/api/download/{symbol}.csv")
def download_symbol_csv(
    symbol: str = Path(..., description="Ticker symbol"),
    days: str | None = None,
):
    safe_symbol = sanitize_symbol(symbol)
    limit = parse_days(days, default=100, max_days=100)

    sql_query = load_sql("download_symbol").format(symbol=safe_symbol, days=limit)

    def fetch() -> list[dict[str, Any]]:
        rows = query(sql_query)
        return list(reversed(rows))

    rows = handle_athena_error(fetch)
    output = io.StringIO()
    fieldnames = [
        "price_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ingested_at",
        "daily_return_pct",
        "moving_avg_7d",
        "moving_avg_30d",
        "volume_avg_7d",
        "volatility_30d",
        "price_range_pct",
        "computed_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})

    csv_content = output.getvalue()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_symbol.upper()}_history.csv"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
