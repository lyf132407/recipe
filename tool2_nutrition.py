from tools.online_food_api import OnlineFoodAPI

class Tool2NutritionCalc:
    @staticmethod
    def run(food_list: list, people: int) -> dict:
        total_cal = 0.0
        # 循环联网查询每种食材热量并累加
        for food in food_list:
            cal = OnlineFoodAPI.get_food_calorie(food)
            total_cal += cal
        per_person = round(total_cal / people, 1)
        # 减脂、清淡判定逻辑不变
        return {
            "total_calorie": total_cal,
            "per_person_cal": per_person,
            "fit_fat_loss": total_cal < 600,
            "fit_light_crowd": total_cal < 400
        }
