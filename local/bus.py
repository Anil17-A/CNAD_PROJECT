"""In-memory stand-in for Kafka/Redpanda: topics with synchronous pub/sub."""
import collections, threading

class Bus:
    def __init__(self):
        self._subs = collections.defaultdict(list)
        self._lock = threading.Lock()
        self.counts = collections.Counter()

    def subscribe(self, topic, fn):
        self._subs[topic].append(fn)

    def publish(self, topic, msg):
        with self._lock:
            self.counts[topic] += 1
        for fn in list(self._subs[topic]):
            try:
                fn(msg)
            except Exception as e:                      # one bad consumer must not kill the stream
                print(f"[bus] consumer error on {topic}: {e!r}")

bus = Bus()
