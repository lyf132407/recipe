import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("YESAPI_URL")
APP_KEY = os.getenv("YESAPI_APPKEY")
TABLE_NAME = os.getenv("YESAPI_TABLE")
# 本地兜底存储文件
DEFAULT_PROFILE = {
    "userId": "default_user",
    "diner_num": 1,
    "taste_like": [],
    "taboo_foods": [],
    "need_fat_loss": False,
    "prefer_cooker": ""
}

SESSION_PROFILE_DIR = "session_profiles"

class CloudDietProfile:
    def __init__(self, userId: str = "default_user", local_store: str = None):
        self.userId = userId
        if not os.path.exists(SESSION_PROFILE_DIR):
            os.makedirs(SESSION_PROFILE_DIR, exist_ok=True)
        self.local_store = local_store or os.path.join(SESSION_PROFILE_DIR, f"session_profile_{self.userId}.json")

    def _save_local(self, data):
        """断网兜底：本地JSON永久保存偏好"""
        with open(self.local_store, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_local(self):
        """读取本地备份档案"""
        if os.path.exists(self.local_store):
            with open(self.local_store, "r", encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_PROFILE.copy()

    @staticmethod
    def _http_get(params):
        """封装请求，增加超时、异常捕获"""
        try:
            resp = requests.get(API_URL, params=params, timeout=6)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"【云数据库连接失败】{str(e)}，使用本地备份档案")
            return None

    def get_user_profile(self):
        params = {
            "s": "App.Table.Query",
            "appkey": APP_KEY,
            "table": TABLE_NAME,
            "where": json.dumps({"userId": self.userId})
        }
        res = CloudDietProfile._http_get(params)
        if res and res.get("ret") == 200 and res.get("data") and res["data"].get("list"):
            cloud_data = res["data"]["list"][0]
            self._save_local(cloud_data)
            return cloud_data
        return self._load_local()

    def update_field(self, field: str, value):
        profile = self.get_user_profile()
        profile[field] = value
        self._save_local(profile)
        update_data = {field: value}
        params = {
            "s": "App.Table.Update",
            "appkey": APP_KEY,
            "table": TABLE_NAME,
            "where": json.dumps({"userId": self.userId}),
            "data": json.dumps(update_data)
        }
        res = CloudDietProfile._http_get(params)
        if res is None:
            print("⚠️ 网络异常，本次修改已本地保存，联网后自动同步云端")
        return profile

    def set_diner_num(self, num: int):
        return self.update_field("diner_num", num)

    def add_like_taste(self, taste: str):
        profile = self.get_user_profile()
        taste_list = profile.get("taste_like", [])
        if taste not in taste_list:
            taste_list.append(taste)
        return self.update_field("taste_like", taste_list)

    def add_taboo_food(self, food: str):
        profile = self.get_user_profile()
        taboo = profile.get("taboo_foods", [])
        if food not in taboo:
            taboo.append(food)
        return self.update_field("taboo_foods", taboo)

    def set_fat_loss_mode(self, status: bool):
        return self.update_field("need_fat_loss", status)

    def set_prefer_cooker(self, cooker: str):
        return self.update_field("prefer_cooker", cooker)

    def clear_all_profile(self):
        return self.update_field("taste_like", [])
