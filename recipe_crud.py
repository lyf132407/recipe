import json
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("USER_RECIPE_DB", "database/user_custom_recipe.json")

# 初始化数据库文件
def init_db():
    parent_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

init_db()

class RecipeCRUD:
    @staticmethod
    def _read_all():
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_all(data):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 添加菜谱
    @staticmethod
    def add_recipe(category: str, dish_name: str, materials: list, steps: str) -> str:
        data = RecipeCRUD._read_all()
        # 去重，同名覆盖
        new_item = {
            "分类": category,
            "菜名": dish_name,
            "食材": materials,
            "详细步骤": steps
        }
        # 删除同名旧菜谱
        data = [item for item in data if item["菜名"] != dish_name]
        data.append(new_item)
        RecipeCRUD._write_all(data)
        return f"成功添加菜谱：{dish_name}"

    # 删除菜谱
    @staticmethod
    def delete_recipe(dish_name: str) -> str:
        data = RecipeCRUD._read_all()
        old_len = len(data)
        data = [item for item in data if item["菜名"] != dish_name]
        RecipeCRUD._write_all(data)
        if len(data) < old_len:
            return f"已删除菜谱：{dish_name}"
        else:
            return f"未找到名为【{dish_name}】的菜谱"

    # 更新菜谱
    @staticmethod
    def update_recipe(dish_name: str, new_materials=None, new_steps=None) -> str:
        data = RecipeCRUD._read_all()
        hit = False
        for item in data:
            if item["菜名"] == dish_name:
                hit = True
                if new_materials is not None:
                    item["食材"] = new_materials
                if new_steps is not None:
                    item["详细步骤"] = new_steps
                break
        if not hit:
            return f"更新失败，不存在【{dish_name}】"
        RecipeCRUD._write_all(data)
        return f"菜谱【{dish_name}】修改完成"

    # 列出全部菜谱，支持分类筛选
    @staticmethod
    def list_all_recipe(filter_cate=None) -> str:
        data = RecipeCRUD._read_all()
        if filter_cate:
            data = [i for i in data if i["分类"] == filter_cate]
        if not data:
            return "暂无自定义菜谱"
        text = "=== 本地自定义菜谱库 ===\n"
        for idx, item in enumerate(data, 1):
            text += f"{idx}.【{item['菜名']}】分类：{item['分类']}\n"
        return text
