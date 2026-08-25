import json
import os
from tools.online_food_api import OnlineFoodAPI
from tools.recipe_crud import RecipeCRUD
from dotenv import load_dotenv

load_dotenv()
USER_RECIPE_DB = os.getenv("USER_RECIPE_DB")

class Tool4RecipeSearch:
    @staticmethod
    def _get_user_custom_recipe(dish_name: str):
        if not os.path.exists(USER_RECIPE_DB):
            return None
        try:
            with open(USER_RECIPE_DB, "r", encoding="utf-8") as f:
                user_db = json.load(f)
            for item in user_db:
                if item["菜名"] == dish_name:
                    return item
        except:
            pass
        return None

    @staticmethod
    def search_recipe_detail(search_key: str) -> str:
        user_recipe = Tool4RecipeSearch._get_user_custom_recipe(search_key)
        if user_recipe:
            return f"✅ 你的自定义菜谱\n🥘 菜品：{search_key}\n食材：{','.join(user_recipe['食材'])}\n步骤：\n{user_recipe['详细步骤']}"

        online_data = OnlineFoodAPI.search_online_dish(search_key)
        if not online_data:
            return f"ℹ️ 未查询到【{search_key}】菜谱，可更换菜名或简化关键词"
        save_tips = ""
        show_content = ""
        for idx, item in enumerate(online_data[:2]):
            name = item.get("name", "").strip()
            material = item.get("material", "").strip()
            step = item.get("step", "").strip()
            if not name or not material or not step:
                continue
            try:
                ing_list = material.split("、")
                RecipeCRUD.add_recipe("家常菜", name, ing_list, step)
                save_tips += f"✅ 已缓存【{name}】到本地菜谱\n"
            except:
                pass
            show_content += f"\n===== 联网菜谱{idx+1}：{name} =====\n食材配比：{material}\n完整步骤：\n{step}\n"
        final_text = save_tips + show_content
        return final_text if final_text else f"ℹ️ 暂无【{search_key}】有效菜谱"
