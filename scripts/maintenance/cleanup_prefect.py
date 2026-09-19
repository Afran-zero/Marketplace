from datetime import datetime, timedelta, timezone

from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import FlowRunFilter, FlowRunFilterEndTime


async def cleanup(days: int = 30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    flow_run_filter = FlowRunFilter(
        end_time=FlowRunFilterEndTime(before_=cutoff),
    )

    async with get_client() as client:
        flow_runs = await client.read_flow_runs(flow_run_filter=flow_run_filter)
        for flow_run in flow_runs:
            await client.delete_flow_run(flow_run.id)

    print(f"Deleted {len(flow_runs)} flow runs older than {cutoff}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(cleanup())