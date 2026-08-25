class Tool1FoodQuery:
    # 简易食材-菜品映射库（仅兜底，联网为主）
    FOOD_DISH_MAP = {
        "鸡蛋": ["番茄炒蛋", "蒸蛋羹", "荷包蛋"],
        "番茄": ["番茄炒蛋", "番茄炖牛腩", "番茄蛋汤"],
        "西红柿": ["番茄炒蛋", "番茄炖牛腩", "番茄蛋汤"],
        "土豆": ["酸辣土豆丝", "土豆炖排骨", "空气炸锅烤土豆"],
        "鸡胸肉": ["香煎鸡胸肉", "减脂鸡胸沙拉", "空气炸锅鸡胸肉"],
        "排骨": ["土豆炖排骨", "红烧排骨", "电饭煲焖排骨"],
        "豆腐": ["红烧豆腐", "鸡蛋豆腐汤"],
        "黄瓜": ["凉拌黄瓜", "黄瓜炒鸡蛋"]
    }

    @staticmethod
    def run(food_list: list, taboo_list: list) -> list:
        if not food_list:
            return []

        mapped_lists = [set(Tool1FoodQuery.FOOD_DISH_MAP[food]) for food in food_list if food in Tool1FoodQuery.FOOD_DISH_MAP]
        if len(mapped_lists) > 1:
            common_dishes = set.intersection(*mapped_lists)
            if common_dishes:
                return [dish for dish in common_dishes if not any(taboo in dish for taboo in taboo_list)]

        res_set = set()
        for food in food_list:
            if food in Tool1FoodQuery.FOOD_DISH_MAP:
                for dish in Tool1FoodQuery.FOOD_DISH_MAP[food]:
                    if any(taboo in dish for taboo in taboo_list):
                        continue
                    res_set.add(dish)
        return list(res_set)
