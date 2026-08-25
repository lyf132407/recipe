import json
import os

LONG_MEM_PATH = "database/long_user_memory.json"

class LongMemory:
    def __init__(self):
        self.default_data = {
            "taboo_foods": [],
            "favorite_taste": [],
            "need_fat_loss": False
        }
        self.load()

    def load(self):
        if not os.path.exists(LONG_MEM_PATH):
            self.data = self.default_data
            self.save()
        else:
            with open(LONG_MEM_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def save(self):
        with open(LONG_MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_all(self):
        return self.data

    # 更新忌口列表
    def update_taboo(self, food_list: list):
        raw = self.data["taboo_foods"]
        for food in food_list:
            if food.strip() and food not in raw:
                raw.append(food.strip())
        self.data["taboo_foods"] = raw
        self.save()

    # 开启/关闭减脂模式
    def set_fat_loss(self, status: bool):
        self.data["need_fat_loss"] = status
        self.save()
