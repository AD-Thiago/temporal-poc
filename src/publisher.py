from google.cloud import pubsub_v1
import os

PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
TOPIC_NAME = os.getenv("PUBSUB_TOPIC", "hello-topic")


def publish_message(message: str):
    if not PROJECT_ID:
        raise RuntimeError("GCP_PROJECT_ID not set in environment")
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)
    data = message.encode("utf-8")
    future = publisher.publish(topic_path, data)
    result = future.result()
    return result


if __name__ == "__main__":
    msg = "Hello from publisher"
    res = publish_message(msg)
    print("Published message id:", res)
