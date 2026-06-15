import re
with open('src/utils/cache_middleware.py', encoding='utf-8') as f:
    content = f.read()
old = """    @staticmethod
    def _calculate_age(cached_at) -> str:
        \"\"\"计算缓存年龄\"\"\"
        try:
            from datetime import datetime
            cached_time = datetime.fromisoformat(cached_at)
            age_seconds = (datetime.now() - cached_time).total_seconds()
            return f\"{int(age_seconds)}s\"
        except:
            return \"unknown\""""
new = """    @staticmethod
    def _calculate_age(cached_at) -> str:
        \"\"\"计算缓存年龄\"\"\"
        try:
            age_seconds = time.time() - float(cached_at)
            return f\"{int(age_seconds)}s\"
        except (ValueError, TypeError):
            return \"unknown\""""
content = content.replace(old, new)
with open('src/utils/cache_middleware.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed _calculate_age')
