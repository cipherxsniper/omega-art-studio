import redis
import json
import os

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

QUEUE_KEY = "omega:event_queue"

class Queue:

    def push(self, event: dict):
        r.lpush(QUEUE_KEY, json.dumps(event))

    def pop(self):
        item = r.rpop(QUEUE_KEY)
        return json.loads(item) if item else None


def publish_event_bus(event):
    # lazy import to avoid circular dependency
    from core.event_bus import EventBus
    bus = EventBus()
    return bus.publish("queue_event", event)
