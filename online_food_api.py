import re
import requests
import json
import time
import os
from tenacity import retry, stop_after_attempt, wait_fixed
from dotenv import load_dotenv
from utils.cache_clean import clear_expired_cache
from tools.local_recipe_fallback import search_local_by_query

load_dotenv()
# 菜谱基础API
TIANAPI_KEY = os.getenv("TIANAPI_KEY")
TIANAPI_URL = os.getenv("TIANAPI_URL")
# 新增API
NUTRIENT_API = os.getenv("TIANAPI_NUTRIENT")
HEALTH_API = os.getenv("TIANAPI_HEALTH")
CACHE_PATH = os.getenv("CACHE_FILE")

# 程序启动自动清理过期缓存
clear_expired_cache()

class OnlineFoodAPI:
    @staticmethod
    def _write_cache(dish_name: str, data_list: list):
        cache_item = {
            "query_name": dish_name,
            "cache_timestamp": time.time(),
            "recipe_data": data_list
        }
        try:
            with open(CACHE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(cache_item, ensure_ascii=False) + "\n")
        except:
            pass

    @staticmethod
    def _read_cache(dish_name: str):
        if not os.path.exists(CACHE_PATH):
            return []
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    if item["query_name"] == dish_name:
                        return item["recipe_data"]
        except:
            return []
        return []

    @staticmethod
    def _expand_search_queries(search_keyword: str) -> list:
        if not search_keyword:
            return []
        base = search_keyword.strip()
        queries = [base]
        fat_mode = any(tag in base for tag in ["减脂", "低卡", "低脂", "轻食", "健康"])
        if fat_mode:
            suffixes = ["菜谱", "做法", "食谱"]
        else:
            suffixes = ["菜谱", "做法", "家常菜", "食谱", "大全"]
        for suffix in suffixes:
            if suffix not in base:
                if base.endswith("菜") or base.endswith("谱") or base.endswith("做法") or base.endswith("食"):
                    queries.append(f"{base}{suffix}")
                else:
                    queries.append(f"{base} {suffix}")
        if "空气炸锅" in base:
            queries.extend(["空气炸锅菜谱", "空气炸锅食谱", "空气炸锅做法", "空气炸锅家常菜"])
        if fat_mode:
            queries.extend(["减脂菜谱", "低卡菜谱", "低脂菜谱", "健康轻食菜谱", "减肥菜谱"])
        # 去重并保留顺序
        seen = set()
        unique = []
        for q in queries:
            if q and q not in seen:
                seen.add(q)
                unique.append(q)
        return unique

    # 菜谱搜索 双层兜底
    @staticmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=False)
    def search_online_dish(search_keyword: str) -> list:
        queries = OnlineFoodAPI._expand_search_queries(search_keyword)
        for query in queries:
            params = {
                "key": TIANAPI_KEY,
                "word": query
            }
            try:
                resp = requests.get(TIANAPI_URL, params=params, timeout=10)
                resp.raise_for_status()
                res_json = resp.json()
                if res_json.get("code") == 200 and res_json.get("result") and res_json["result"].get("list"):
                    recipe_list = res_json["result"]["list"]
                    OnlineFoodAPI._write_cache(query, recipe_list)
                    return recipe_list
                if res_json.get("code") != 200 and res_json.get("msg"):
                    print(f"API返回无内容：{query} => {res_json.get('msg')}")
            except Exception as e:
                print(f"API请求异常：{query} => {str(e)}")

        # 在线 API 无结果时，本地语义检索兜底
        for query in queries:
            try:
                local_data = search_local_by_query(query)
                if local_data:
                    return local_data
            except Exception as e:
                print(f"本地语义检索异常：{query} => {str(e)}")
        # 联网失败或全部结果为空，读取缓存
        for query in queries:
            cache_data = OnlineFoodAPI._read_cache(query)
            if cache_data:
                return cache_data
        return []

    # 联网查询食材热量
    @staticmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=False)
    def get_food_calorie(food_name: str) -> float:
        params = {
            "key": TIANAPI_KEY,
            "word": food_name,
            "mode": 0
        }
        try:
            resp = requests.get(NUTRIENT_API, params=params, timeout=6)
            data = resp.json()
            if data["code"] == 200 and data["result"]["list"]:
                calorie = float(data["result"]["list"][0]["energy"])
                return calorie
        except:
            pass
        return 60.0

    # 联网查询食材相克
    @staticmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=False)
    def get_food_conflict(food_list: list) -> str:
        warn_text = ""
        for food in food_list:
            params = {
                "key": TIANAPI_KEY,
                "word": f"{food} 同食禁忌"
            }
            try:
                resp = requests.get(HEALTH_API, params=params, timeout=6)
                data = resp.json()
                if data["code"] == 200 and data["result"]["list"]:
                    desc = data["result"]["list"][0].get("content", "")
                    if desc:
                        warn_text += f"【{food}】{desc}\n"
            except Exception:
                continue
        return warn_text.strip()
