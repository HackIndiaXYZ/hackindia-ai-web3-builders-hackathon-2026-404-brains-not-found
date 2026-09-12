"""Kafka event bus for TrafficGuard Pro.

The project keeps all legacy features and falls back gracefully when Kafka is not
configured. This makes Kafka a real optional integration instead of a hard
requirement.
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger("TrafficGuard.EventBus")

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except Exception:  # pragma: no cover - optional dependency
    KafkaProducer = None
    KafkaError = Exception


class TrafficGuardEventBus:
    def __init__(self):
        self.bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "").strip()
        self.topic = os.environ.get("KAFKA_TOPIC", "trafficguard.events").strip() or "trafficguard.events"
        self.producer = None
        if self.bootstrap_servers and KafkaProducer is not None:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=[server.strip() for server in self.bootstrap_servers.split(",") if server.strip()],
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",
                    retries=3,
                    linger_ms=10,
                )
                logger.info("Kafka producer initialized for topic %s", self.topic)
            except Exception as exc:  # pragma: no cover - runtime environment specific
                logger.warning("Kafka initialization failed: %s", exc)
                self.producer = None

    def publish(self, event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {"event": event_name, "payload": payload, "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"}
        if not self.bootstrap_servers or self.producer is None:
            return {"status": "SKIPPED", "reason": "Kafka not configured"}
        try:
            self.producer.send(self.topic, value=event)
            self.producer.flush(timeout=5)
            return {"status": "PUBLISHED", "topic": self.topic}
        except Exception as exc:  # pragma: no cover - broker may be down
            logger.warning("Kafka publish failed for %s: %s", event_name, exc)
            return {"status": "FAILED", "reason": str(exc)}


_bus = TrafficGuardEventBus()


def publish_event(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _bus.publish(event_name, payload)
