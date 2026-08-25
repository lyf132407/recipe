import json
import os

SHORT_MEM_PATH = "cache/short_memory.json"

class ShortMemory:
    def __init__(self):
        self.default_data = {
            "diner_num": 1,
            "taste": "清淡"
        }
        self.load()

    def load(self):
        if not os.path.exists(SHORT_MEM_PATH):
            self.data = self.default_data
            self.save()
        else:
            with open(SHORT_MEM_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def save(self):
        with open(SHORT_MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_memory(self):
        return self.data

    def set_diner_num(self, num: int):
        self.data["diner_num"] = num
        self.save()

    def set_taste(self, taste: str):
        self.data["taste"] = taste
        self.save()

    @property
    def diner_num(self):
        return self.data.get("diner_num", 1)

    @property
    def taste(self):
        return self.data.get("taste", "清淡")

    def clear(self):
        self.data = self.default_data
        self.save()
