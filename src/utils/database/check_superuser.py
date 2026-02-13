import getpass
import sys
from typing import Optional

from sqlalchemy.orm import Session

from src.models.user import User


def check_superuser_exists(session: Session) -> bool:
    """
    检查数据库中是否存在至少一个超级管理员用户
    
    Args:
        session: 数据库会话
        
    Returns:
        bool: 如果存在至少一个超级管理员用户则返回True，否则返回False
    """
    try:
        # 查询至少一个超级管理员用户
        superuser = session.query(User).filter(User.is_superuser == True).first()
        return superuser is not None
    except Exception as e:
        # 检查是否是表不存在的错误
        error_msg = str(e).lower()
        if "undefinedtable" in error_msg or "does not exist" in error_msg or "no such table" in error_msg:
            print("数据库表不存在，可能是首次运行，需要初始化数据库。")
        else:
            print(f"检查超级管理员用户时发生错误: {e}")
        return False


def get_password_from_user(prompt: str = "请输入密码: ") -> str:
    """
    获取用户输入的密码并确认
    
    Args:
        prompt: 密码输入提示文本
        
    Returns:
        str: 用户输入的密码
    """
    while True:
        password = getpass.getpass(prompt)
        if len(password) < 6:
            print("密码长度至少需要6位，请重新输入。")
            continue

        confirm_password = getpass.getpass("请确认密码: ")

        if password == confirm_password:
            print("密码确认成功。")
            return password
        else:
            print("两次输入的密码不一致，请重新输入。")


def create_superuser_interactive(session: Session) -> Optional[User]:
    """
    通过交互式命令行创建超级管理员用户
    
    Args:
        session: 数据库会话
        
    Returns:
        User: 创建的超级管理员用户对象，如果创建失败则返回None
    """
    print("\n检测到数据库中没有超级管理员用户，正在创建超级管理员账户...")
    print("请提供以下信息：")
    
    # 获取用户名
    while True:
        username = input("请输入用户名: ").strip()
        if not username:
            print("用户名不能为空，请重新输入。")
            continue
        
        # 检查用户名是否已存在
        existing_user = session.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"用户名 '{username}' 已存在，请使用其他用户名。")
            continue
        
        break
    
    # 获取邮箱
    while True:
        email = input("请输入邮箱地址: ").strip()
        if not email:
            print("邮箱不能为空，请重新输入。")
            continue
        
        # 简单验证邮箱格式
        if "@" not in email or "." not in email:
            print("邮箱格式不正确，请重新输入。")
            continue
        
        # 检查邮箱是否已存在
        existing_user = session.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"邮箱 '{email}' 已存在，请使用其他邮箱。")
            continue
        
        break
    
    # 获取密码
    password = get_password_from_user()
    
    try:
        # 创建超级管理员用户
        from datetime import datetime, timezone
        import bcrypt
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        superuser = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc),
            register_ip="127.0.0.1",  # 本地创建的用户使用本地IP
            is_superuser=True,
            is_active=True,
            is_verified=True  # 管理员账户默认已验证
        )
        
        session.add(superuser)
        session.commit()
        session.refresh(superuser)  # 刷新以获取ID等自动生成的字段
        
        print(f"\n成功创建超级管理员用户！")
        print(f"用户名: {superuser.username}")
        print(f"邮箱: {superuser.email}")
        print(f"用户ID: {superuser.id}")
        
        return superuser
    except Exception as e:
        session.rollback()
        print(f"创建超级管理员用户时发生错误: {e}")
        return None


def create_default_superuser(session: Session) -> Optional[User]:
    """
    自动创建默认的超级管理员用户
    
    Args:
        session: 数据库会话
        
    Returns:
        User: 创建的超级管理员用户对象，如果创建失败则返回None
    """
    print("\n正在自动创建默认超级管理员用户...")
    print("使用默认用户名: admin 和默认密码: admin123")
    
    # 默认用户名和邮箱
    default_username = "admin"
    default_email = "admin@example.com"
    default_password = "admin123"
    
    # 检查用户名是否已存在
    existing_user = session.query(User).filter(User.username == default_username).first()
    if existing_user:
        print(f"用户名 '{default_username}' 已存在，使用现有用户。")
        return existing_user
    
    # 检查邮箱是否已存在
    existing_email = session.query(User).filter(User.email == default_email).first()
    if existing_email:
        print(f"邮箱 '{default_email}' 已存在，使用现有用户。")
        return existing_email
    
    try:
        # 创建超级管理员用户
        from datetime import datetime, timezone
        import bcrypt
        
        hashed_password = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        superuser = User(
            username=default_username,
            email=default_email,
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc),
            register_ip="127.0.0.1",  # 自动创建的用户使用本地IP
            is_superuser=True,
            is_active=True,
            is_verified=True  # 管理员账户默认已验证
        )
        
        session.add(superuser)
        session.commit()
        session.refresh(superuser)  # 刷新以获取ID等自动生成的字段
        
        print(f"\n成功创建默认超级管理员用户！")
        print(f"用户名: {superuser.username}")
        print(f"邮箱: {superuser.email}")
        print(f"用户ID: {superuser.id}")
        
        return superuser
    except Exception as e:
        session.rollback()
        print(f"创建默认超级管理员用户时发生错误: {e}")
        return None

def ensure_superuser_exists(auto_create=True):
    """
    确保数据库中存在至少一个超级管理员用户
    如果不存在，根据auto_create参数决定是否自动创建
    
    Args:
        auto_create (bool): 是否自动创建超级管理员用户，如果为False则跳过创建
    """
    # 先初始化扩展
    from src.extensions import init_extensions
    from fastapi import FastAPI
    app = FastAPI()
    init_extensions(app)
    
    # 从扩展中导入get_db（在初始化之后）
    from src.extensions import get_db

    # 尝试检查是否存在超级管理员用户
    try:
        with get_db() as session:
            try:
                if check_superuser_exists(session):
                    print("数据库中已存在超级管理员用户，无需创建。")
                    return True
            except Exception as e:
                # 如果是表不存在的错误，说明需要先创建表
                error_msg = str(e).lower()
                if "undefinedtable" in error_msg or "does not exist" in error_msg or "no such table" in error_msg:
                    print("数据库表不存在，可能是首次运行，需要初始化数据库。")
                else:
                    # 其他错误，记录但继续执行
                    print(f"检查超级管理员用户时发生错误: {e}")
                    # 继续执行，因为可能只是暂时性错误
                    
    except Exception as e:
        print(f"无法建立数据库会话以检查超级管理员用户: {e}")
        return False
    
    print("数据库中没有超级管理员用户。")
    
    # 检查是否处于交互式环境
    import sys
    is_interactive = sys.stdin.isatty()

    if auto_create:
        # 检查是否在交互式环境中，如果是则允许交互式创建，否则自动创建默认用户
        if is_interactive:
            # 使用新的会话来创建用户
            with get_db() as session:
                # 询问用户是否要创建超级管理员用户
                while True:
                    create_option = input("是否要创建一个新的超级管理员用户？(y/n, 默认为 y): ").strip().lower()
                    if create_option in ['', 'y', 'yes']:
                        created_user = create_superuser_interactive(session)
                        return created_user is not None
                    elif create_option in ['n', 'no']:
                        print("您选择了不创建超级管理员用户。请注意，某些管理功能可能无法使用。")
                        return False
                    else:
                        print("请输入 'y' 表示是，'n' 表示否。")
        else:
            with get_db() as session:
                print("非交互式环境，自动创建默认超级管理员用户...")
                created_user = create_default_superuser(session)
                return created_user is not None
    else:
        print("自动创建被禁用，跳过超级管理员用户创建。")
        return False

if __name__ == "__main__":
    # 当作为独立脚本运行时，执行检查
    success = ensure_superuser_exists(auto_create=True)
    if success:
        print("超级管理员用户检查/创建完成。")
    else:
        print("超级管理员用户检查/创建失败。")
        sys.exit(1)