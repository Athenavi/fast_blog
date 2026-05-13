# 读取生成的文件，提取 ROUTE_REGISTRY 部分
with open('new_route_registry.txt', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# 找到 ROUTE_REGISTRY 开始的位置
start_idx = None
for i, line in enumerate(lines):
    if 'ROUTE_REGISTRY = [' in line:
        start_idx = i
        break

if start_idx is None:
    print("未找到 ROUTE_REGISTRY")
    exit(1)

# 提取从 ROUTE_REGISTRY 开始的所有内容
route_config = ''.join(lines[start_idx:])

# 写入新文件
with open('route_registry_clean.txt', 'w', encoding='utf-8') as f:
    f.write(route_config)

print("已生成干净的路由配置: route_registry_clean.txt")
