import os
import sys
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 确保所有模型都被导入，以便Base.metadata包含所有表定义
from src.models import Article, ArticleContent, User, Category
import bcrypt


def get_password_from_user(interactive=True):
    """获取用户输入的密码并确认
    
    Args:
        interactive (bool): 是否在交互模式下运行，如果为False则使用默认密码
    """
    if not interactive:
        # 非交互模式，使用默认密码
        print("非交互式环境，使用默认密码: admin123")
        default_password = "admin123"
        hashed_password = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
        return hashed_password.decode('utf-8')

    while True:
        password = input("请输入密码（至少6位）: ")
        if len(password) < 6:
            print("密码长度至少需要6位，请重新输入。")
            continue

        confirm_password = input("请确认密码: ")

        if password == confirm_password:
            print("密码确认成功。")
            # 生成哈希密码
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            return hashed_password.decode('utf-8')
        else:
            print("两次输入的密码不一致，请重新输入。")


def check_and_initialize_db():
    """检查数据库内容，如果表不存在则创建表，如果为空则创建一些测试数据"""
    # 先初始化扩展
    from src.extensions import init_extensions
    from fastapi import FastAPI
    app = FastAPI()
    init_extensions(app)

    # 确保所有模型都已注册到metadata中
    from src.models import Base
    print(f"已注册的表: {list(Base.metadata.tables.keys())}")

    # 等待片刻让表创建完成
    import time
    time.sleep(3)

    # 从扩展中导入get_db（在初始化之后）
    from src.extensions import get_db

    # 尝试连接数据库并检查表是否可用
    max_retries = 5
    table_check_success = False

    for attempt in range(max_retries):
        try:
            with get_db() as session:
                # 尝试执行简单的查询来验证表是否存在
                user_count = session.query(User).count()
                article_count = session.query(Article).count()
                category_count = session.query(Category).count()

                print(f"用户数量: {user_count}")
                print(f"文章数量: {article_count}")
                print(f"分类数量: {category_count}")

                table_check_success = True
                # 如果所有查询都成功，跳出循环
                break

        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                print("等待片刻后重试...")
                time.sleep(3)
        except Exception as create_error:
            print(f"重新创建表时出错: {create_error}")

    if not table_check_success:
        print("警告: 无法验证数据库表的存在，但将继续初始化过程")
        return

    # 检查数据是否为空并添加测试数据
    if article_count == 0:
        print("数据库中没有文章，正在创建测试文章...")

        with get_db() as session:
            # 如果没有用户，创建一个测试用户
            try:
                user_count = session.query(User).count()
            except:
                user_count = 0

            if user_count == 0:
                # 获取用户输入的密码
                import sys
                interactive = sys.stdin.isatty()
                hashed_password = get_password_from_user(interactive=interactive)

                test_user = User(
                    username="testuser",
                    email="test@example.com",
                    hashed_password=hashed_password,
                    created_at=datetime.now(timezone.utc),
                    register_ip="127.0.0.1",
                    is_superuser=True
                )
                session.add(test_user)
                session.flush()  # 获取ID但不提交
                user_id = test_user.id
                print(f"创建了测试用户，ID: {user_id}")
            else:
                # 获取第一个用户
                try:
                    first_user = session.query(User).first()
                    user_id = first_user.id
                except:
                    # 如果查询失败，使用默认用户ID（例如1）
                    user_id = 1

            # 如果没有分类，创建一个测试分类
            try:
                category_count = session.query(Category).count()
            except:
                category_count = 0

            if category_count == 0:
                test_category = Category(
                    name="测试分类",
                    description="测试用的分类",
                    created_at=datetime.now(timezone.utc)
                )
                session.add(test_category)
                session.flush()  # 获取ID但不提交
                category_id = test_category.id
                print(f"创建了测试分类，ID: {category_id}")
            else:
                # 获取第一个分类
                try:
                    first_category = session.query(Category).first()
                    category_id = first_category.id
                except:
                    # 如果查询失败，使用默认分类ID（例如1）
                    category_id = 1

            # 创建测试文章
            test_article = Article(
                title="欢迎使用博客系统",
                slug="welcome-to-blog-system",
                user_id=user_id,
                category_id=category_id,
                excerpt="这是一个测试文章，用于验证博客系统是否正常工作。",
                status=1,  # 已发布
                tags="测试,博客",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(test_article)
            session.flush()  # 获取ID但不提交

            # 创建文章内容
            article_content = ArticleContent(
                aid=test_article.article_id,
                content="# 欢迎使用博客系统\n\n这是一篇测试文章，用于验证博客系统是否正常工作。\n\n## 特性\n\n- 支持Markdown格式\n- 响应式设计\n- 用户友好的界面",
                updated_at=datetime.now(timezone.utc)
            )
            session.add(article_content)

            session.commit()
            print(f"成功创建了测试文章，ID: {test_article.article_id}")

    # 再次检查文章数量
    try:
        with get_db() as session:
            article_count_after = session.query(Article).count()
            print(f"创建测试数据后文章数量: {article_count_after}")

            # 显示所有文章
            articles = session.query(Article).all()
            print("\n所有文章:")
            for article in articles:
                print(f"  ID: {article.article_id}, 标题: {article.title}, Slug: {article.slug}")
    except:
        print("无法查询文章列表，但数据可能已创建成功")

    print("数据库检查和初始化完成")


if __name__ == "__main__":
    # 使用锁机制执行数据库初始化
    from src.utils.database.migration_lock import run_migration_with_lock


    def _run_check_and_init():
        check_and_initialize_db()


    # 使用锁保护执行数据库初始化
    run_migration_with_lock(_run_check_and_init)