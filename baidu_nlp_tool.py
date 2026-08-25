import jieba

class BaiduNlpTool:
    @staticmethod
    def get_lexer_words(text: str):
        # jieba本地分词，简易词性模拟（够用做饮食意图识别）
        words = jieba.lcut(text)
        res = []
        for w in words:
            # 简单模拟词性，仅满足你的需求
            if w.isdigit():
                pos = "m"  # 数字（人数）
            elif w in ["辣","酸甜","咸鲜","清淡","麻辣"]:
                pos = "a"  # 形容词口味
            elif w in ["黄瓜","鸡蛋","番茄","西红柿","柿子","土豆","排骨","豆腐"]:
                pos = "n"  # 食材名词
            else:
                pos = "x"
            res.append({"word": w, "pos": pos})
        return res

    @staticmethod
    def extract_diet_intent(text: str):
        """纯本地分词，无网络依赖，替代百度云端API"""
        try:
            words = BaiduNlpTool.get_lexer_words(text)
            word_list = [w["word"] for w in words]
        except Exception as e:
            print(f"本地分词降级：{e}")
            word_list = text.replace("，"," ").split()

        # 1. 用餐人数识别
        num = None
        for w in word_list:
            if w.isdigit():
                num = int(w)
        if num and any(k in text for k in ["个人","人吃饭","一起吃"]):
            return ("set_person", num)

        # 2. 喜爱口味
        taste_pool = ["辣","酸甜","咸鲜","清淡","卤味","麻辣"]
        like_flag = any(k in text for k in ["爱吃","喜欢","想吃","偏爱"])
        if like_flag:
            for taste in taste_pool:
                if taste in word_list:
                    return ("add_taste", taste)

        # 3. 忌口食材
        taboo_flag = any(k in text for k in ["讨厌","不吃","忌口","过敏","不喜欢"])
        food_pool = ["黄瓜","鸡蛋","番茄","西红柿","柿子","土豆","排骨","豆腐","鸡胸肉","牛肉","猪肉","虾","鱼","青菜","生菜","菌菇","香菇","洋芋","青瓜"]
        if taboo_flag:
            for food in food_pool:
                if food in word_list:
                    real_food = "番茄" if food in ["柿子", "西红柿"] else food
                    return ("add_taboo", real_food)

        # 4. 显式退出编辑模式识别
        if "退出编辑" in text or "关闭编辑" in text or ("退出" in text and "编辑" in text):
            return ("exit_edit", True)

        # 5. 查询意图识别：优先识别菜谱、空气炸锅、减脂相关请求
        query_words = ["推荐", "菜谱", "美食", "吃什么", "吃啥", "能做啥", "做啥菜", "今天吃什么", "有什么好吃的", "要吃什么", "帮我做菜", "家常菜", "菜谱大全", "可以做什么", "能做什么", "做什么"]
        ingredient_query_phrases = ["家里有", "冰箱里有", "厨房里有", "手头有", "能做啥", "能做什么", "做啥", "做什么", "吃什么", "吃啥", "有什么"]
        air_fry_words = ["空气炸锅", "空气炸锅菜谱", "空气炸锅食谱", "炸锅"]
        fat_words = ["减脂", "减肥", "低卡", "低脂", "轻食", "瘦身", "健康餐"]
        normalized = text

        # 5.1 食材查询意图识别：例如“家里有鸡蛋土豆可以做什么”或“鸡蛋西红柿能做啥”
        ingredients = [food for food in food_pool if food in normalized]
        if ingredients and (any(k in normalized for k in ingredient_query_phrases) or len(ingredients) >= 2):
            normalized_ingredients = ["番茄" if food in ["柿子", "西红柿"] else food for food in ingredients]
            return ("query_normal", normalized_ingredients)

        if any(w in normalized for w in query_words):
            if any(w in normalized for w in air_fry_words):
                return ("query_airfryer", True)
            if any(w in normalized for w in fat_words):
                return ("query_fatloss", True)
            return ("query_normal", True)

        # 6. 减脂模式开关
        on_words = ["开启", "打开", "开始", "设置", "我要"]
        off_words = ["关闭", "取消", "结束", "不想", "不再"]
        if any(w in normalized for w in fat_words):
            if any(w in normalized for w in on_words):
                return ("fat_on", True)
            if any(w in normalized for w in off_words):
                return ("fat_off", False)

        return (None, None)
