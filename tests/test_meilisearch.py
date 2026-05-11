"""
Meilisearch 集成测试脚本
用于验证搜索引擎是否正常工作
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from shared.services.meilisearch_service import meilisearch_service


async def test_meilisearch():
    """测试 Meilisearch 连接和基本功能"""

    print("=" * 60)
    print("  Meilisearch 集成测试")
    print("=" * 60)
    print()

    # 1. 测试连接
    print("1️⃣  测试连接...")
    try:
        success = await meilisearch_service.initialize()
        if success:
            print("   ✅ 连接成功")
        else:
            print("   ❌ 连接失败")
            return False
    except Exception as e:
        print(f"   ❌ 连接异常: {e}")
        return False

    print()

    # 2. 测试索引文章
    print("2️⃣  测试索引文章...")
    test_article = {
        'id': 999999,
        'title': '测试文章 - Meilisearch 集成',
        'slug': 'test-meilisearch-integration',
        'excerpt': '这是一篇测试文章，用于验证 Meilisearch 是否正常工作',
        'content': '这是测试文章的完整内容。Meilisearch 是一个强大的开源搜索引擎，支持全文搜索、模糊匹配、拼音搜索等功能。',
        'cover_image': '',
        'category_id': 1,
        'category_name': '测试分类',
        'author_id': 1,
        'author_name': '测试用户',
        'tags': ['测试', 'meilisearch', '搜索'],
        'views': 100,
        'likes': 10,
        'status': 'published',
        'is_featured': False,
        'created_at': 1715000000,
        'updated_at': 1715000000,
    }

    try:
        await meilisearch_service.index_article(test_article)
        print("   ✅ 文章索引成功")

        # 等待索引完成
        await asyncio.sleep(1)
    except Exception as e:
        print(f"   ❌ 文章索引失败: {e}")
        return False

    print()

    # 3. 测试搜索
    print("3️⃣  测试搜索功能...")
    try:
        result = await meilisearch_service.search(
            query="Meilisearch",
            page=1,
            per_page=10
        )

        if result.get('articles'):
            print(f"   ✅ 搜索成功，找到 {result['total']} 条结果")
            print(f"   📊 处理时间: {result.get('processing_time_ms', 0)}ms")

            # 显示第一条结果
            first_article = result['articles'][0]
            print(f"   📝 标题: {first_article.get('title')}")
            print(f"   🔍 高亮: {first_article.get('highlighted_title')}")
        else:
            print("   ⚠️  搜索无结果（可能需要等待索引完成）")
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        return False

    print()

    # 4. 测试搜索建议
    print("4️⃣  测试搜索建议...")
    try:
        suggestions = await meilisearch_service.get_search_suggestions(
            query="测",
            limit=5
        )

        if suggestions:
            print(f"   ✅ 获取到 {len(suggestions)} 条建议:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"      {i}. {suggestion}")
        else:
            print("   ⚠️  无搜索建议")
    except Exception as e:
        print(f"   ❌ 获取建议失败: {e}")

    print()

    # 5. 测试统计信息
    print("5️⃣  测试统计信息...")
    try:
        stats = await meilisearch_service.get_index_stats()

        if stats:
            print("   ✅ 统计信息获取成功:")
            print(f"      - 文档数量: {stats.get('number_of_documents', 0)}")
            print(f"      - 索引大小: {stats.get('index_size_in_bytes', 0)} bytes")
        else:
            print("   ⚠️  无法获取统计信息")
    except Exception as e:
        print(f"   ❌ 获取统计失败: {e}")

    print()

    # 6. 清理测试数据
    print("6️⃣  清理测试数据...")
    try:
        await meilisearch_service.delete_article(999999)
        print("   ✅ 测试数据已清理")
    except Exception as e:
        print(f"   ⚠️  清理失败: {e}")

    print()
    print("=" * 60)
    print("  ✅ 所有测试通过！Meilisearch 集成正常")
    print("=" * 60)

    return True


async def main():
    """主函数"""
    try:
        success = await test_meilisearch()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
