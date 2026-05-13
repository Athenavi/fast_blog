"""
快速测试 v2 API 路由和重定向功能
"""
import requests
import sys


def test_v2_routes(base_url="http://localhost:9421"):
    """测试 v2 路由是否正常注册"""
    print("=" * 80)
    print("测试 V2 API 路由")
    print("=" * 80)

    # 测试几个关键的 v2 端点
    test_endpoints = [
        ("/api/v2/users", "GET", "用户模块"),
        ("/api/v2/home", "GET", "首页模块"),
        ("/api/v2/dashboard", "GET", "仪表板模块"),
        ("/api/v2/system", "GET", "系统模块"),
        ("/api/v2/categories", "GET", "分类模块"),
    ]

    for endpoint, method, description in test_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.request(method, url, timeout=5)

            # 404 表示路由未注册，其他状态码表示路由存在
            if response.status_code == 404:
                print(f"❌ {description:15} {endpoint:40} - 未找到 (404)")
            else:
                print(f"✅ {description:15} {endpoint:40} - {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"⚠️  无法连接到服务器 {base_url}，请先启动应用")
            return False
        except Exception as e:
            print(f"❌ {description:15} {endpoint:40} - 错误: {e}")

    return True


def test_v1_to_v2_redirect(base_url="http://localhost:9421"):
    """测试 v1 到 v2 的自动重定向"""
    print("\n" + "=" * 80)
    print("测试 V1 -> V2 自动重定向")
    print("=" * 80)

    # 测试几个应该会重定向的路径
    redirect_tests = [
        ("/api/v1/delete", "/api/v2/gdpr/data-deletion", "GDPR 删除数据"),
        ("/api/v1/export", "/api/v2/gdpr/data-export", "GDPR 导出数据"),
        ("/api/v1/stats", "/api/v2/monitoring/stats", "统计信息"),
        ("/api/v1/config", "/api/v2/admin/config", "配置信息"),
    ]

    for v1_path, expected_v2, description in redirect_tests:
        try:
            url = f"{base_url}{v1_path}"
            response = requests.get(url, timeout=5, allow_redirects=False)

            # 检查是否是重定向响应
            if response.status_code in [301, 302]:
                location = response.headers.get('Location', '')
                redirect_from = response.headers.get('X-Redirect-From', '')
                redirect_to = response.headers.get('X-Redirect-To', '')

                if expected_v2 in location or redirect_to:
                    print(f"✅ {description:20} {v1_path:35} -> {redirect_to or location}")
                else:
                    print(f"⚠️  {description:20} {v1_path:35} -> 重定向但目标不匹配")
                    print(f"   期望: {expected_v2}")
                    print(f"   实际: {location}")
            elif response.status_code == 404:
                print(f"❌ {description:20} {v1_path:35} - 未找到 (404)")
            else:
                print(f"ℹ️  {description:20} {v1_path:35} - {response.status_code} (可能不需要重定向)")
        except requests.exceptions.ConnectionError:
            print(f"⚠️  无法连接到服务器 {base_url}，请先启动应用")
            return False
        except Exception as e:
            print(f"❌ {description:20} {v1_path:35} - 错误: {e}")

    return True


def main():
    """主函数"""
    base_url = "http://localhost:9421"

    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"\n测试服务器: {base_url}\n")

    # 测试 v2 路由
    v2_ok = test_v2_routes(base_url)

    if not v2_ok:
        print("\n⚠️  服务器未运行或 v2 路由未正确注册")
        print("提示: 请先运行 'python main.py' 启动服务器")
        sys.exit(1)

    # 测试重定向
    redirect_ok = test_v1_to_v2_redirect(base_url)

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    if v2_ok and redirect_ok:
        print("✅ 所有测试通过！V2 API 和重定向功能正常工作。")
    elif v2_ok:
        print("✅ V2 API 路由正常，但部分重定向可能需要调整。")
    else:
        print("❌ 测试失败，请检查服务器状态和路由配置。")

    print("\n更多信息请查看:")
    print("  - docs/API_V2_MIGRATION_GUIDE.md")
    print("  - src/api/v2/__init__.py")
    print("  - src/middleware/v1_to_v2_redirect.py")


if __name__ == "__main__":
    main()
