import threading
import json
import os

class ContextStore:
    def __init__(self, path="context.json"):
        self.path = path
        self.lock = threading.RLock() 
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save(self):
        with self.lock:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=2)

    def get(self, key, default=None):
        with self.lock:
            return self.data.get(key, default)

    def set(self, key, value):
        with self.lock:
            self.data[key] = value
            self.save()

    def get_all(self):
        with self.lock:
            return dict(self.data)