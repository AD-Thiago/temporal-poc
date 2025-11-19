import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker

from deprecated.temporal.workflows import GreetingWorkflow, say_hello


async def main() -> None:
    target = os.getenv("TEMPORAL_TARGET", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")

    # Connect to Temporal server (local or cloud) using env vars
    print(f"Connecting to Temporal target={target} namespace={namespace}")
    api_key = os.getenv("TEMPORAL_API_KEY")
    connect_kwargs = {}
    if api_key:
        # Add Authorization header if API key is provided (Temporal Cloud)
        connect_kwargs["headers"] = {"authorization": f"Bearer {api_key}"}
        print("Using TEMPORAL_API_KEY for Authorization header")

    client = await Client.connect(target, namespace=namespace, **connect_kwargs)

    worker = Worker(
        client,
        task_queue="hello-task-queue",
        workflows=[GreetingWorkflow],
        activities=[say_hello],
    )
    print("Worker started. Listening for tasks...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
