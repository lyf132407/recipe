from tools.tool1_food_query import Tool1FoodQuery
from tools.tool2_nutrition import Tool2NutritionCalc
from tools.tool3_conflict_check import Tool3ConflictCheck
from tools.tool4_recipe_search import Tool4RecipeSearch
from tools.recipe_crud import RecipeCRUD
from tools.online_food_api import OnlineFoodAPI
from database.cloud_profile import CloudDietProfile
import re
from tools.baidu_nlp_tool import BaiduNlpTool
import jieba
from fuzzywuzzy import fuzz
from tools.local_recipe_fallback import search_local_by_query, search_local_by_ingredients, filter_fat_loss, generate_ingredient_queries

class RecipeReActAgent:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or "default"
        # 云端档案实例，可按会话区分本地记忆文件
        self.cloud_db = CloudDietProfile(userId=self.session_id)
        self.edit_profile_mode = False  # 档案编辑会话开关
        # 食材别名映射（柿子=番茄，纯文本映射不依赖本地库）
        self.FOOD_ALIAS = {"柿子": "番茄", "西红柿": "番茄", "洋芋": "土豆", "青瓜": "黄瓜"}
        # 偏好识别关键词库
        self.taste_keywords = ["辣", "酸甜", "清淡", "重口", "咸鲜", "清淡", "卤味"]
        self.taboo_keywords = ["讨厌", "不吃", "忌口", "过敏", "不喜欢"]
        self.person_keywords = ["个人", "两个人", "三个人", "四人", "几个人吃饭"]
        self.fat_loss_keywords = ["减脂", "减肥", "低卡", "控热量"]

        # 原有搜索/厨具/菜谱关键词保留
        self.cook_query_words = {"怎么做", "做法", "食谱", "教程"}
        self.recommend_key = {"减脂":["减脂","低卡"], "空气炸锅":["空气炸锅"]}
        self.cooker_words = {"空气炸锅":["空气炸锅"]}

    def refresh_profile_view(self):
        """获取格式化档案文本，用于GUI左侧实时展示"""
        p = self.cloud_db.get_user_profile()
        text = f"""===== 个人饮食档案（云端实时同步）=====
🍚 用餐人数：{p['diner_num']}人
🌶️ 喜爱口味：{','.join(p['taste_like']) if p['taste_like'] else '无'}
🚫 忌口食材：{','.join(p['taboo_foods']) if p['taboo_foods'] else '无'}
🔥 减脂模式：{"开启" if p['need_fat_loss'] else "关闭"}
🔧 常用厨具：{p['prefer_cooker'] if p['prefer_cooker'] else '无'}
指令：开启档案编辑 / 退出编辑
"""
        return text

    def parse_diet_edit_intent(self, text: str):
       # 调用百度NLP，打印调试信息，方便查看是否识别成功
        intent, val = BaiduNlpTool.extract_diet_intent(text)
        print(f"【意图识别日志】输入文本：{text}，识别结果：{intent}，参数：{val}")
        return (intent, val)



    def get_all_taboo(self):
        return self.cloud_db.get_user_profile().get("taboo_foods", [])

    def handle_edit_profile_session(self, user_input: str):
        """专属档案编辑会话逻辑"""
        if user_input in ["退出编辑", "关闭档案", "exit"]:
            self.edit_profile_mode = False
            return f"✅ 已退出饮食档案编辑模式\n当前档案：\n{self.refresh_profile_view()}"
        # 解析修改指令
        intent, val = self.parse_diet_edit_intent(user_input)
        # 原有档案修改逻辑
        if intent == "set_person":
            self.cloud_db.set_diner_num(val)
            return f"已更新用餐人数：{val}人"
        elif intent == "add_taste":
            self.cloud_db.add_like_taste(val)
            return f"已添加喜爱口味：{val}"
        elif intent == "add_taboo":
            self.cloud_db.add_taboo_food(val)
            return f"已添加忌口食材：{val}"
        elif intent == "fat_on":
            self.cloud_db.set_fat_loss_mode(True)
            return "已开启减脂推荐模式，后续推荐自动筛选低卡低脂菜品"
        elif intent == "fat_off":
            self.cloud_db.set_fat_loss_mode(False)
            return "已关闭减脂模式，恢复普通家常菜推荐"

        # =========新增查询、退出编辑分支========
        elif intent == "exit_edit":
            self.edit_profile_mode = False
            return "已退出饮食档案编辑模式，可正常查询菜谱"
        elif intent == "query_airfryer":
            taboo = self.get_all_taboo()
            return self.condition_recommend_dish(user_input, taboo, cooker="空气炸锅")
        elif intent == "query_fatloss":
            self.cloud_db.set_fat_loss_mode(True)
            taboo = self.get_all_taboo()
            return self.condition_recommend_dish(user_input, taboo, cooker=None)
        elif intent == "query_normal":
            taboo = self.get_all_taboo()
            return self.condition_recommend_dish(user_input, taboo, cooker=None)

        # 无匹配意图，走通用对话/通用菜谱
        else:
            taboo = self.get_all_taboo()
            return self.condition_recommend_dish(user_input, taboo, cooker=None)


    def extract_food_list(self, text: str) -> list:
        """从自然语言中提取常见食材，支持‘西红柿鸡蛋能做啥菜’等问法"""
        food_candidates = ["西红柿", "柿子", "番茄", "鸡蛋", "土豆", "黄瓜", "豆腐", "排骨", "鸡胸肉", "牛肉", "猪肉", "虾", "鱼", "洋芋", "青瓜"]
        found = []
        for food in food_candidates:
            if food in text:
                real_food = self.FOOD_ALIAS.get(food, food)
                if real_food not in found:
                    found.append(real_food)
        return found

    def extract_valid_food(self, text: str) -> list:
        """食材提取，云端API兼容别名"""
        if "有" in text:
            raw_part = text.split("有")[-1]
            raw_items = re.split(r"[，、,\s]+", raw_part)
            raw_list = [f.strip() for f in raw_items if f.strip()]
            if not raw_list:
                raw_list = self.extract_food_list(raw_part)
        else:
            raw_list = self.extract_food_list(text)
        valid = []
        for food in raw_list:
            real_food = self.FOOD_ALIAS.get(food, food)
            if real_food not in valid:
                valid.append(real_food)
        return valid

    def search_by_ingredients(self, food_list: list, taboo_list: list) -> list:
        """只按食材组合搜索，优先在线检索并用本地候选项兜底。"""
        if not food_list:
            return []
        normalized = [self.FOOD_ALIAS.get(food, food) for food in food_list]
        candidate_queries = [" ".join(normalized), " ".join(reversed(normalized))]
        candidate_queries += [f"{' '.join(normalized)} 菜谱", f"{' '.join(normalized)} 做法", f"{' '.join(normalized)} 低脂", f"{' '.join(normalized)} 低卡"]

        for query in candidate_queries:
            online_results = OnlineFoodAPI.search_online_dish(query)
            if online_results:
                return online_results

        local_results = search_local_by_ingredients(normalized)
        if local_results:
            return local_results

        candidate_dishes = Tool1FoodQuery.run(normalized, taboo_list)
        if not candidate_dishes:
            return []
        ranked = sorted(candidate_dishes, key=lambda dish: -sum(1 for food in normalized if food in dish))
        return [{"name": dish, "material": "、".join(normalized)} for dish in ranked]

    def extract_dish_name(self, text: str) -> str:
        """完整保留修饰菜名（蓑衣黄瓜不丢失）"""
        dish_text = text
        for word in self.cook_query_words:
            dish_text = dish_text.replace(word, "").strip()
        return dish_text

    def condition_recommend_dish(self, user_input: str, taboo_list: list, cooker=None):
        """修复完整版：读取档案减脂标记 + 多同义词搜索 + 修复过滤逻辑"""
        # 1. 读取用户完整饮食档案（包含是否减脂）
        profile = self.cloud_db.get_user_profile()
        like_tastes = profile["taste_like"]
        is_fat_loss = profile["need_fat_loss"]  # 读取全局减脂开关

        # 2. 构建搜索关键词池
        search_keywords = ["家常菜", "家常菜谱", "菜谱大全", "家常菜做法", "家庭食谱"]
        fat_words = ["减脂", "减肥", "瘦身", "低卡", "低脂", "轻食", "健康餐"]
        input_need_fat = any(word in user_input for word in fat_words)
        if input_need_fat or is_fat_loss:
            method_tags = ["清蒸", "水煮", "凉拌", "空气炸锅", "清炒"]
            ingredient_tags = ["鸡胸肉", "鱼", "虾", "鸡蛋", "番茄", "绿叶蔬菜", "菌菇", "豆腐"]
            search_keywords = []
            for method in method_tags:
                search_keywords.extend([f"{method} 低脂", f"{method} 低卡", f"{method} 菜谱"])
            for ingredient in ingredient_tags:
                search_keywords.extend([f"{ingredient} 低脂", f"{ingredient} 低卡", f"{ingredient} 菜谱"])
            for method in method_tags:
                for ingredient in ingredient_tags:
                    search_keywords.append(f"{method} {ingredient}")
            search_keywords.extend(["减脂菜谱", "低卡菜谱", "低脂菜谱", "健康轻食菜谱", "减肥菜谱"])
            if cooker == "空气炸锅":
                search_keywords = [kw for kw in search_keywords if "空气炸锅" in kw or "低脂" in kw or "低卡" in kw]
        else:
            search_keywords.extend(["轻食菜谱", "清淡菜谱", "低油菜谱"])

        # 拼接用户喜爱口味
        taste_str = " ".join(like_tastes) if like_tastes else ""
        full_search_list = [f"{kw} {taste_str}".strip() for kw in search_keywords]
        if user_input and user_input not in full_search_list:
            full_search_list.append(user_input)

        ingredient_foods = self.extract_food_list(user_input)
        candidate_queries = []
        if ingredient_foods:
            candidate_queries.extend(generate_ingredient_queries(ingredient_foods))
            if cooker == "空气炸锅":
                candidate_queries.extend([f"空气炸锅 {' '.join(ingredient_foods)}", f"空气炸锅 {ingredient_foods[0]} 菜谱"])
            if input_need_fat or is_fat_loss:
                candidate_queries.extend([f"低脂 {' '.join(ingredient_foods)}", f"低卡 {' '.join(ingredient_foods)}"])

        if not candidate_queries:
            candidate_queries = full_search_list
        else:
            candidate_queries += full_search_list

        raw_recipes = []
        for search_word in candidate_queries:
            if not search_word:
                continue
            results = OnlineFoodAPI.search_online_dish(search_word)
            if results:
                raw_recipes = results
                break

        if not raw_recipes:
            for query in candidate_queries:
                local_results = search_local_by_query(query)
                if local_results:
                    raw_recipes = local_results
                    break

        if not raw_recipes and ingredient_foods:
            raw_recipes = search_local_by_ingredients(ingredient_foods)

        if not raw_recipes and user_input not in candidate_queries:
            raw_recipes = OnlineFoodAPI.search_online_dish(user_input)

        if not raw_recipes:
            if input_need_fat or is_fat_loss:
                raw_recipes = search_local_by_query("低脂")
            else:
                raw_recipes = search_local_by_query("家常菜")

        if not raw_recipes:
            local_recipes = []
            if cooker == "空气炸锅":
                local_recipes = [
                    {"name": "空气炸锅烤土豆", "material": "土豆、盐、橄榄油"},
                    {"name": "空气炸锅鸡胸肉", "material": "鸡胸肉、黑胡椒、橄榄油"},
                    {"name": "空气炸锅香菇", "material": "香菇、酱油、糖"}
                ]
            elif input_need_fat or is_fat_loss:
                local_recipes = [
                    {"name": "减脂鸡胸沙拉", "material": "鸡胸肉、生菜、番茄"},
                    {"name": "清蒸鱼片", "material": "鱼片、生姜、葱"},
                    {"name": "番茄鸡蛋汤", "material": "番茄、鸡蛋、葱"}
                ]
            else:
                if ingredient_foods:
                    local_dishes = Tool1FoodQuery.run(ingredient_foods, taboo_list)
                    local_recipes = [{"name": dish, "material": "、".join(ingredient_foods)} for dish in local_dishes]
                if not local_recipes:
                    local_recipes = [
                        {"name": "番茄炒蛋", "material": "番茄、鸡蛋、葱"},
                        {"name": "清炒时蔬", "material": "青菜、蒜"},
                        {"name": "土豆炖排骨", "material": "土豆、排骨、姜"}
                    ]
            raw_recipes = local_recipes

        # 4. 修复忌口过滤逻辑
        def has_taboo(ingredient_text):
            return any(taboo in ingredient_text for taboo in taboo_list)
        safe_recipes = [d for d in raw_recipes if not has_taboo(d["material"])]

        # 5. 减脂规则过滤：同时满足 2 条以上判定为减脂菜
        def is_fat_loss_item(item):
            text = "\n".join([str(item.get("name", "")), str(item.get("material", "")), str(item.get("step", ""))])
            good_tags = 0

            cook_methods = ["清蒸", "水煮", "凉拌", "空气炸锅", "清炒"]
            bad_methods = ["红烧", "油炸", "干锅", "卤制", "煎", "炸", "酱爆", "蒜蓉" ]
            ingredient_good = ["鸡胸肉", "鱼", "虾", "鸡蛋", "西红柿", "蔬菜", "绿叶", "生菜", "菠菜", "油麦菜", "菜花", "青菜", "菌菇", "香菇", "金针菇", "豆腐"]
            ingredient_bad = ["肥肉", "五花肉", "奶油", "黄油", "油炸", "炸" ]
            seasoning_good = ["少油", "少盐", "无糖", "无黄油", "不加糖", "低油", "低盐", "健康" ]

            if any(w in text for w in cook_methods):
                good_tags += 1
            if any(w in text for w in seasoning_good):
                good_tags += 1
            if any(w in text for w in ingredient_good):
                good_tags += 1
            if any(w in text for w in bad_methods + ingredient_bad):
                return False
            return good_tags >= 2

        tag_text = ""
        if input_need_fat or is_fat_loss:
            filtered = [d for d in safe_recipes if is_fat_loss_item(d)]
            if filtered:
                safe_recipes = filtered
            else:
                # 如果线上数据无法完全匹配减脂规则，保留原始可用结果但标记提示
                tag_text = "减脂模式开启（未完全命中减脂规则，以下为近似结果）"

        # 过滤后为空，直接返回全部菜品，不空白
        if not safe_recipes:
            safe_recipes = raw_recipes

        # 6. 组装输出文本
        if not tag_text:
            tag_text = "减脂模式开启" if is_fat_loss else ""
        taste_text = f"偏好口味：{','.join(like_tastes)}" if like_tastes else "大众口味"
        output = f"{tag_text} {taste_text}\n共匹配{len(safe_recipes)}道菜品（已过滤忌口食材）\n"
        for idx, dish in enumerate(safe_recipes[:10], 1):
            output += f"{idx}.【{dish['name']}】食材：{dish['material']}\n"
        return output


    def react_thought_action(self, user_input: str):
        """主推理入口"""
        # 分支1：档案编辑会话优先拦截
        if self.edit_profile_mode:
            return self.handle_edit_profile_session(user_input)
        # 分支2：用户主动开启编辑模式
        if user_input in ["开启档案编辑", "修改饮食偏好"]:
            self.edit_profile_mode = True
            return f"📝 已进入饮食档案专属编辑模式\n{self.refresh_profile_view()}\n请输入修改指令，输入【退出编辑】结束"

        profile = self.cloud_db.get_user_profile()
        taboo_list = profile["taboo_foods"]
        diner_num = profile["diner_num"]
        response_log = []

        # 自动识别普通对话里的偏好修改、菜谱推荐请求（无需开启编辑面板）
        intent, val = self.parse_diet_edit_intent(user_input)
        if intent is not None:
            if intent == "set_person":
                self.cloud_db.set_diner_num(val)
                response_log.append(f"自动识别：更新用餐人数为{val}人")
                return "\n".join(response_log + [self.refresh_profile_view()])
            elif intent == "add_taste":
                self.cloud_db.add_like_taste(val)
                response_log.append(f"自动识别：添加喜爱口味 {val}")
                return "\n".join(response_log + [self.refresh_profile_view()])
            elif intent == "add_taboo":
                self.cloud_db.add_taboo_food(val)
                response_log.append(f"自动识别：添加忌口食材 {val}")
                return "\n".join(response_log + [self.refresh_profile_view()])
            elif intent == "fat_on":
                self.cloud_db.set_fat_loss_mode(True)
                return "已开启减脂模式，后续推荐自动筛选低卡低脂菜品"
            elif intent == "fat_off":
                self.cloud_db.set_fat_loss_mode(False)
                return "已关闭减脂模式，恢复普通家常菜推荐"
            elif intent == "query_airfryer":
                rec_text = self.condition_recommend_dish(user_input, taboo_list, cooker="空气炸锅")
                return rec_text
            elif intent == "query_fatloss":
                rec_text = self.condition_recommend_dish(user_input, taboo_list, cooker=None)
                return rec_text
            elif intent == "query_normal":
                if isinstance(val, list) and val:
                    ingredients = val
                    raw_recipes = self.search_by_ingredients(ingredients, taboo_list)
                    if raw_recipes:
                        response = [f"识别食材：{ingredients}", f"匹配到{len(raw_recipes)}道食材匹配菜品"]
                        response.extend([f"【{dish['name']}】 食材：{dish.get('material','')}" for dish in raw_recipes[:8]])
                    else:
                        dish_list = Tool1FoodQuery.run(ingredients, taboo_list)
                        response = [f"识别食材：{ingredients}", "未找到在线完整菜品，已使用本地候选", f"适配菜品：{dish_list}"]
                    conflict = Tool3ConflictCheck.run(ingredients)
                    response.append("同食禁忌：" + (conflict if conflict else "无"))
                    nutrition = Tool2NutritionCalc.run(ingredients, diner_num)
                    response.append(f"人均热量：{nutrition['per_person_cal']}千卡")
                    return "\n".join(response)
                return self.condition_recommend_dish(user_input, taboo_list, cooker=None)

        # 分支3：菜品推荐（减脂/空气炸锅按钮）
        need_match = any(any(k in user_input for k in v) for v in self.recommend_key.values())
        if need_match:
            cooker = None
            for ck, kw_list in self.cooker_words.items():
                if any(kw in user_input for kw in kw_list):
                    cooker = ck
            rec_text = self.condition_recommend_dish(user_input, taboo_list, cooker)
            response_log.append(rec_text)
            return "\n".join(response_log)

        # 分支4：现有食材查询（家里有鸡蛋柿子）
        if "家里有" in user_input:
            food_list = self.extract_valid_food(user_input)
            response_log.append(f"识别食材：{food_list}")
            # 联网匹配菜品、热量、相克，无本地静态库
            dish_list = Tool1FoodQuery.run(food_list, taboo_list)
            response_log.append(f"适配全部菜品：{dish_list}")
            conflict = Tool3ConflictCheck.run(food_list)
            response_log.append("同食禁忌："+(conflict if conflict else "无"))
            nutrition = Tool2NutritionCalc.run(food_list, diner_num)
            response_log.append(f"人均热量：{nutrition['per_person_cal']}千卡")
            return "\n".join(response_log)

        if any(kw in user_input for kw in ["能做啥", "做啥菜", "吃什么", "吃啥", "有什么菜"]):
            food_list = self.extract_valid_food(user_input)
            if food_list:
                response_log.append(f"识别食材：{food_list}")
                dish_list = Tool1FoodQuery.run(food_list, taboo_list)
                response_log.append(f"适配全部菜品：{dish_list}")
                conflict = Tool3ConflictCheck.run(food_list)
                response_log.append("同食禁忌："+(conflict if conflict else "无"))
                nutrition = Tool2NutritionCalc.run(food_list, diner_num)
                response_log.append(f"人均热量：{nutrition['per_person_cal']}千卡")
                return "\n".join(response_log)

        # 分支5：查询菜做法（蓑衣黄瓜怎么做）
        if any(w in user_input for w in self.cook_query_words):
            dish = self.extract_dish_name(user_input)
            detail = Tool4RecipeSearch.search_recipe_detail(f"{dish}完整做法 克数")
            response_log.append(f"【{dish}菜谱】\n{detail}")
            return "\n".join(response_log)

        return "\n".join(response_log + ["未识别需求，请输入菜谱、食材或偏好修改指令"])
