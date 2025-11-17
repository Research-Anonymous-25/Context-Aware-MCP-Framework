import json
import os

class ContextStore:
    def __init__(self, filename: str):
        self.filename = filename
        if not os.path.exists(self.filename):
            self.write({})

    def read(self) -> dict:
        with open(self.filename, 'r') as f:
            return json.load(f)

    def write(self, data: dict):
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=2)