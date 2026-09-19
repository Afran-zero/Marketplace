import os
import time
from pathlib import Path
from typing import Any

from prefect import flow, task

ATHENA_DB = "alphavantage_db"
ATHENA_RESULTS_LOCATION = "s3://alphavantage-medallion-kaif12589/athena-results/"
ATHENA_REGION = "us-east-1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_sql(name: str) -> str:
    sql_path = PROJECT_ROOT / "sql" / f"{name}.sql"
    return sql_path.read_text(encoding="utf-8").strip()


class AthenaQueryError(RuntimeError):
    """Raised when Athena query execution fails."""


def _coerce_value(raw_value: Any) -> Any:
    if raw_value is None:
        return None

    if isinstance(raw_value, dict):
        if raw_value.get("IsNull") is True:
            return None
        raw_value = raw_value.get("VarCharValue")

    if raw_value is None:
        return None

    if isinstance(raw_value, str):
        text = raw_value.strip()
        if text == "":
            return None
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    return raw_value


def _load_aws_credentials():
    """Load Prefect credentials only when the query path actually runs."""
    from prefect_aws import AwsCredentials

    os.environ.setdefault("PREFECT_SERVER_EPHEMERAL_ENABLED", "false")
    return AwsCredentials.load("aws-credentials")


@task(name="athena-query", retries=1, retry_delay_seconds=5)
def run_athena_query(query: str) -> list[dict[str, Any]]:
    """Execute a SQL query in Athena and return rows as a list of dicts."""
    print(f"Submitting Athena query: {query[:120]}...")
    creds = _load_aws_credentials()
    session = creds.get_boto3_session()
    athena_client = session.client("athena", region_name=ATHENA_REGION)

    execution = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": ATHENA_RESULTS_LOCATION},
    )
    execution_id = execution["QueryExecutionId"]
    print(f"Query execution ID: {execution_id}")

    for _ in range(60):
        status = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        print(f"Polling... state={state}")
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            break
        time.sleep(0.5)
    else:
        raise AthenaQueryError("Athena query timed out after 30 seconds")

    if state != "SUCCEEDED":
        reason = status["QueryExecution"]["Status"].get("StateChangeReason")
        message = reason or f"Athena query failed with state: {state}"
        raise AthenaQueryError(message)

    results = athena_client.get_query_results(QueryExecutionId=execution_id)
    rows = results.get("ResultSet", {}).get("Rows", [])
    if not rows:
        return []

    headers = [cell.get("VarCharValue", "") for cell in rows[0]["Data"]]
    data_rows = []

    for row in rows[1:]:
        values = row.get("Data", [])
        row_dict: dict[str, Any] = {}
        for idx, column_name in enumerate(headers):
            raw_value = values[idx].get("VarCharValue") if idx < len(values) else None
            row_dict[column_name] = _coerce_value(raw_value)
        data_rows.append(row_dict)

    print(f"Returning {len(data_rows)} rows")
    return data_rows


@flow(name="athena-query-flow", log_prints=True)
def query(sql: str) -> list[dict[str, Any]]:
    return run_athena_query(sql)
