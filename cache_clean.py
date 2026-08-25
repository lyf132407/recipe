import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
CACHE_EXPIRE_DAY = int(os.getenv("CACHE_EXPIRE_DAY"))
CACHE_PATH = os.getenv("CACHE_FILE")

def clear_expired_cache():
    """清理超过N天的缓存菜谱，程序启动自动执行"""
    if not os.path.exists(CACHE_PATH):
        # 不存在缓存文件则创建空文件
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            pass
        return

    valid_records = []
    expire_time = datetime.now() - timedelta(days=CACHE_EXPIRE_DAY)

    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                cache_time = datetime.fromtimestamp(item["cache_timestamp"])
                if cache_time >= expire_time:
                    valid_records.append(item)
            except Exception:
                continue

    # 重写有效缓存
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        for record in valid_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"缓存清理完成，保留{CACHE_EXPIRE_DAY}天内菜谱缓存")

if __name__ == "__main__":
    clear_expired_cache()
