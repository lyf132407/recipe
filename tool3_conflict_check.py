from tools.online_food_api import OnlineFoodAPI

class Tool3ConflictCheck:
    @staticmethod
    def run(food_list: list) -> str:
        # 全部联网查询，不再依赖本地静态相克库
        conflict_warn = OnlineFoodAPI.get_food_conflict(food_list)
        return conflict_warn
