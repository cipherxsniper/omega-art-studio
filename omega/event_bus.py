from queue import Queue
from core.event_log import EventLog

EVENT_QUEUE = Queue()
log = EventLog(db=None)

class EventBus:

    def publish(self, event: dict):
        log.append(event)
        EVENT_QUEUE.put(event)
        return event

    def consume(self):
        return EVENT_QUEUE.get()

    def replay_all(self):
        return log.replay()


def get_queue():
    from core.event_queue import EventQueue
    return EventQueue()


    def safe_write(self, event):
        if self.db is None:
            return None
        return self.db.insert(event)
