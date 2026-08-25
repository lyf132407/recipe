import re

LOCAL_RECIPES = [
    {
        "name": "番茄炒蛋",
        "materials": ["番茄", "鸡蛋", "葱"],
        "method": "清炒",
        "description": "番茄与鸡蛋同炒，清淡下饭。"
    },
    {
        "name": "番茄蛋汤",
        "materials": ["番茄", "鸡蛋", "姜"],
        "method": "清炖",
        "description": "清淡汤品，鸡蛋番茄营养均衡。"
    },
    {
        "name": "蒸蛋羹",
        "materials": ["鸡蛋", "水", "盐"],
        "method": "清蒸",
        "description": "嫩滑蒸蛋，简单省事。"
    },
    {
        "name": "鸡蛋豆腐汤",
        "materials": ["鸡蛋", "豆腐", "香葱"],
        "method": "炖",
        "description": "轻食汤品，低脂又营养。"
    },
    {
        "name": "凉拌黄瓜",
        "materials": ["黄瓜", "蒜", "香油"],
        "method": "凉拌",
        "description": "清爽小菜，夏天开胃。"
    },
    {
        "name": "清炒菠菜",
        "materials": ["菠菜", "蒜"],
        "method": "清炒",
        "description": "清淡蔬菜，搭配主食。"
    },
    {
        "name": "空气炸锅鸡胸肉",
        "materials": ["鸡胸肉", "黑胡椒", "橄榄油"],
        "method": "空气炸锅",
        "description": "低脂烤鸡胸，适合减脂。"
    },
    {
        "name": "清蒸鱼",
        "materials": ["鱼", "姜", "葱"],
        "method": "清蒸",
        "description": "健康清淡，保留鱼鲜味。"
    },
    {
        "name": "番茄炖牛腩",
        "materials": ["番茄", "牛肉", "土豆"],
        "method": "炖",
        "description": "家常炖菜，番茄酸甜。"
    },
    {
        "name": "土豆炖排骨",
        "materials": ["土豆", "排骨", "姜"],
        "method": "炖",
        "description": "经典家常菜，口味浓郁。"
    },
    {
        "name": "鸡胸肉沙拉",
        "materials": ["鸡胸肉", "生菜", "番茄"],
        "method": "凉拌",
        "description": "低脂轻食，适合减脂期。"
    },
    {
        "name": "香菇鸡胸肉",
        "materials": ["鸡胸肉", "香菇", "青菜"],
        "method": "清炒",
        "description": "低脂高蛋白，适合健身人群。"
    }
]

FAT_LOSS_METHODS = ["清蒸", "水煮", "凉拌", "空气炸锅", "清炒", "炖"]
BAD_FAT_METHODS = ["红烧", "油炸", "干锅", "卤制", "煎", "炸", "酱爆"]
GOOD_FAT_INGREDIENTS = ["鸡胸肉", "鱼", "虾", "鸡蛋", "番茄", "绿叶蔬菜", "生菜", "菠菜", "油麦菜", "菜花", "青菜", "菌菇", "香菇", "豆腐"]
BAD_FAT_INGREDIENTS = ["肥肉", "五花肉", "奶油", "黄油", "油炸", "炸"]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _score_recipe_by_query(recipe: dict, query: str) -> int:
    query_text = _normalize_text(query)
    score = 0
    if query_text in _normalize_text(recipe["name"]):
        score += 10
    for ing in recipe["materials"]:
        if _normalize_text(ing) in query_text:
            score += 3
    for term in [recipe["method"], recipe["description"]]:
        if _normalize_text(term) in query_text:
            score += 2
    for token in query_text.split():
        if token and token in _normalize_text(recipe["name"]):
            score += 1
    return score


def search_local_by_query(query: str) -> list:
    if not query:
        return []
    scored = []
    for recipe in LOCAL_RECIPES:
        score = _score_recipe_by_query(recipe, query)
        if score > 0:
            scored.append((score, recipe))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"name": r["name"], "material": "、".join(r["materials"]), "method": r["method"], "description": r["description"]} for _, r in scored]


def search_local_by_ingredients(ingredients: list) -> list:
    if not ingredients:
        return []
    normalized_ingredients = [ing.replace("西红柿", "番茄").strip() for ing in ingredients]
    exact_matches = []
    partial_matches = []
    for recipe in LOCAL_RECIPES:
        recipe_ings = [ing.replace("西红柿", "番茄") for ing in recipe["materials"]]
        if all(ing in recipe_ings for ing in normalized_ingredients):
            exact_matches.append(recipe)
        elif any(ing in recipe_ings for ing in normalized_ingredients):
            partial_matches.append(recipe)
    exact_matches = sorted(exact_matches, key=lambda r: len(r["materials"]))
    partial_matches = sorted(partial_matches, key=lambda r: -sum(ing in [i.replace("西红柿", "番茄") for i in r["materials"]] for ing in normalized_ingredients))
    results = exact_matches + partial_matches
    return [{"name": r["name"], "material": "、".join(r["materials"]), "method": r["method"], "description": r["description"]} for r in results]


def filter_fat_loss(recipes: list) -> list:
    filtered = []
    for item in recipes:
        text = "".join([item.get("name", ""), item.get("material", ""), item.get("method", ""), item.get("description", "")])
        if any(bad in text for bad in BAD_FAT_METHODS + BAD_FAT_INGREDIENTS):
            continue
        good_count = 0
        if any(method in text for method in FAT_LOSS_METHODS):
            good_count += 1
        if any(ing in text for ing in GOOD_FAT_INGREDIENTS):
            good_count += 1
        if any(season in text for season in ["少油", "少盐", "无糖", "无黄油", "低油", "低盐"]):
            good_count += 1
        if good_count >= 2:
            filtered.append(item)
    return filtered


def generate_ingredient_queries(ingredients: list) -> list:
    normalized = ["番茄" if ing in ["西红柿", "柿子"] else ing for ing in ingredients]
    name = " ".join(normalized)
    queries = [name]
    if len(normalized) > 1:
        queries.append("".join(normalized))
    common_names = []
    for recipe in LOCAL_RECIPES:
        if all(ing in [x.replace("西红柿", "番茄") for x in recipe["materials"]] for ing in normalized):
            common_names.append(recipe["name"])
    queries.extend(common_names)
    return list(dict.fromkeys([q for q in queries if q]))
