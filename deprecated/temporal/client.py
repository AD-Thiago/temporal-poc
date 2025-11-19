import asyncio
import os
from temporalio.client import Client

from deprecated.temporal.workflows import GreetingWorkflow


async def main() -> None:
    target = os.getenv("TEMPORAL_TARGET", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")

    print(f"Connecting to Temporal target={target} namespace={namespace}")
    api_key = os.getenv("TEMPORAL_API_KEY")
    connect_kwargs = {}
    if api_key:
        # Add Authorization header if API key is provided (Temporal Cloud)
        connect_kwargs["headers"] = {"authorization": f"Bearer {api_key}"}
        print("Using TEMPORAL_API_KEY for Authorization header")

    client = await Client.connect(target, namespace=namespace, **connect_kwargs)

    handle = await client.start_workflow(
        GreetingWorkflow.run,
        "World",
        id="greeting-workflow",
        task_queue="hello-task-queue",
    )
    print("Workflow started, waiting result...")
    result = await handle.result()
    print("Workflow result:", result)


if __name__ == "__main__":
    asyncio.run(main())
