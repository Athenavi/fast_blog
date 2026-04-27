# 插件数据库使用指南

## 设计理念

1. **按需使用**：不是所有插件都需要数据库
2. **自治管理**：每个插件自行管理自己的数据库初始化
3. **自动触发**：插件激活时自动初始化数据库（如果需要）

## 如何为插件添加数据库支持

### 步骤 1: 在 metadata.json 中声明

```json
{
  "name": "Your Plugin",
  "slug": "your-plugin",
  "version": "1.0.0",
  "requires_database": true,
  "capabilities": [
    "access:database"
  ]
}
```

### 步骤 2: 创建数据库初始化函数

在 `plugin.py` 文件中添加初始化函数（命名约定：`init_{slug}_db`）：

```python
from shared.utils.plugin_database import plugin_db


def init_your_plugin_db():
    """初始化你的插件数据库"""
    slug = "your-plugin"

    # 创建表（如果不存在）
    if not plugin_db.table_exists(slug, "your_table"):
        plugin_db.execute_update(slug, """
            CREATE TABLE your_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print(f"[PluginDB] Your Plugin database initialized")


class YourPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="Your Plugin",
            slug="your-plugin",
            version="1.0.0"
        )

    def activate(self):
        """激活插件"""
        super().activate()
        # 数据库会自动初始化（因为 requires_database=true）
```

### 步骤 3: 在插件中使用数据库

```python
def save_data(self, data: dict):
    """保存数据到数据库"""
    plugin_db.execute_update(
        'your-plugin',
        "INSERT INTO your_table (name) VALUES (?)",
        (data.get('name'),)
    )


def get_all_data(self) -> list:
    """从数据库获取所有数据"""
    return plugin_db.execute_query(
        'your-plugin',
        "SELECT * FROM your_table ORDER BY created_at DESC"
    )
```

## 最佳实践

### 1. 表存在性检查

始终在创建表之前检查表是否存在：

```python
if not plugin_db.table_exists(slug, "my_table"):
# 创建表
```

### 2. 参数化查询

防止 SQL 注入：

```python
# ✓ 正确
plugin_db.execute_update(
    'your-plugin',
    "SELECT * FROM table WHERE id = ?",
    (user_id,)
)

# ✗ 错误
plugin_db.execute_update(
    'your-plugin',
    f"SELECT * FROM table WHERE id = {user_id}"  # SQL注入风险！
)
```

### 3. 错误处理

妥善处理数据库异常：

```python
try:
    result = plugin_db.execute_query('your-plugin', "SELECT ...")
except Exception as e:
    print(f"[YourPlugin] Database error: {e}")
    return []
```

## 数据库文件位置

所有插件数据库存储在 `plugins_data/` 目录：

```
plugins_data/
├── conversion-tracking.db
├── malware-scanner.db
├── email-marketing.db
└── ...
```

## 常见问题

### Q: 插件不需要数据库，但想存储少量配置怎么办？

A: 使用 `settings.json` 文件：

```python
self.settings = {'key': 'value'}
self.save_settings()  # 保存到 settings.json
```

### Q: 如何处理数据库版本升级？

A: 在初始化函数中检查表结构并升级：

```python
def init_your_plugin_db():
    slug = "your-plugin"

    if not plugin_db.table_exists(slug, "your_table"):
        # 创建新表
        ...
    else:
        # 检查是否需要升级
        columns = plugin_db.execute_query(
            slug,
            "PRAGMA table_info(your_table)"
        )
        column_names = [col['name'] for col in columns]

        if 'new_field' not in column_names:
            # 添加新字段
            plugin_db.execute_update(
                slug,
                "ALTER TABLE your_table ADD COLUMN new_field TEXT"
            )
```

## 总结

- ✅ 在 `metadata.json` 中声明 `requires_database: true`
- ✅ 提供 `init_{slug}_db()` 初始化函数
- ✅ 在插件激活时自动初始化
- ✅ 使用 `plugin_db` 工具类进行数据库操作
- ✅ 遵循最佳实践确保安全和性能
