"""
Consume Kafka task results and print them line by line.
"""

from __future__ import annotations

from confluent_kafka import Consumer

from common import logger
from common.config import kafka_config
from services.registry import ServiceManager


def _build_kafka_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": kafka_config.BOOTSTRAP_SERVERS,
            "group.id": f"{kafka_config.CONSUMER_GROUP}_result_viewer",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )


@ServiceManager.register_service(service_name="task_result_viewer")
def consume_kafka_results(
    consumer: Consumer | None = None,
    topic: str | None = None,
) -> None:
    kafka_consumer = consumer or _build_kafka_consumer()
    target_topic = topic or kafka_config.RESULT_TOPIC
    kafka_consumer.subscribe([target_topic])
    logger.info("start consume results from kafka topic: {}", target_topic)
    try:
        while True:
            message = kafka_consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                logger.error("kafka consume error: {}", message.error())
                continue
            payload = message.value()
            if payload is None:
                kafka_consumer.commit(message=message, asynchronous=False)
                continue
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                text = payload.decode("utf-8", errors="replace")
            print(text, flush=True)
            kafka_consumer.commit(message=message, asynchronous=False)
    except KeyboardInterrupt:
        pass
    finally:
        kafka_consumer.close()
