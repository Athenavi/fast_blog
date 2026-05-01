# 评论系统增强指南

## 📋 概述

FastBlog 实现了增强的评论系统，提供嵌套回复、点赞/反对、智能排序和通知功能。

**核心功能**:

- ✅ 评论树形结构（无限层级嵌套）
- ✅ 评论点赞/反对
- ✅ 三种排序方式（最新、最早、最热）
- ✅ 评论回复通知
- ✅ 用户投票状态追踪
- ✅ 分页支持

---

## 🏗️ 架构设计

### 数据模型

**Comment 表**:

```python
class Comment:
    id              # 评论ID
    article_id      # 文章ID
    user_id         # 用户ID（可选）
    parent_id       # 父评论ID（自引用，支持嵌套）
    content         # 评论内容
    author_name     # 作者名称
    likes           # 点赞数
    is_approved     # 是否审核通过
    created_at      # 创建时间
```

**CommentVote 表**:

```python
class CommentVote:
    id              # 投票ID
    comment_id      # 评论ID
    user_id         # 用户ID
    vote_type       # 投票类型 (like/dislike)
```

### 树形结构

```
根评论 1
├── 回复 1.1
│   ├── 回复 1.1.1
│   └── 回复 1.1.2
└── 回复 1.2
根评论 2
└── 回复 2.1
```

---

## 🚀 API 使用

### 1. 获取文章评论树

**Endpoint**: `GET /api/v1/comments-enhanced/article/{article_id}`

**Query Parameters**:

- `sort_by`: 排序方式 (`latest`, `oldest`, `popular`)
- `page`: 页码（默认 1）
- `per_page`: 每页数量（默认 20，最大 100）

**Response**:

```json
{
  "success": true,
  "data": {
    "comments": [
      {
        "id": 1,
        "content": "这是一条评论",
        "author_name": "张三",
        "likes": 10,
        "depth": 0,
        "children": [
          {
            "id": 2,
            "content": "这是回复",
            "author_name": "李四",
            "likes": 5,
            "depth": 1,
            "children": []
          }
        ]
      }
    ],
    "total": 50,
    "page": 1,
    "per_page": 20,
    "total_pages": 3
  }
}
```

**示例**:

```bash
# 获取最新评论
curl "http://localhost:9421/api/v1/comments-enhanced/article/123?sort_by=latest&page=1&per_page=20"

# 获取最热评论
curl "http://localhost:9421/api/v1/comments-enhanced/article/123?sort_by=popular"
```

### 2. 点赞评论

**Endpoint**: `POST /api/v1/comments-enhanced/{comment_id}/like`

**Headers**:

```
Authorization: Bearer YOUR_TOKEN
```

**Response**:

```json
{
  "success": true,
  "data": {
    "success": true,
    "action": "liked",
    "likes": 11
  }
}
```

**说明**:

- 如果已经点赞，再次调用会取消点赞
- `action` 可能是 `liked` 或 `unliked`

### 3. 反对评论

**Endpoint**: `POST /api/v1/comments-enhanced/{comment_id}/dislike`

**Headers**:

```
Authorization: Bearer YOUR_TOKEN
```

**Response**:

```json
{
  "success": true,
  "data": {
    "success": true,
    "action": "disliked",
    "likes": 9
  }
}
```

**说明**:

- 反对会减少点赞数（最低为 0）
- 如果已经反对，再次调用会取消反对

### 4. 获取用户投票状态

**Endpoint**: `GET /api/v1/comments-enhanced/{comment_id}/vote`

**Headers**:

```
Authorization: Bearer YOUR_TOKEN
```

**Response**:

```json
{
  "success": true,
  "data": {
    "vote_type": "like"
  }
}
```

**说明**:

- `vote_type` 可能是 `like`, `dislike`, 或 `null`

### 5. 通知评论回复

**Endpoint**: `POST /api/v1/comments-enhanced/{comment_id}/notify-reply`

**Headers**:

```
Authorization: Bearer YOUR_TOKEN
```

**Response**:

```json
{
  "success": true,
  "data": {
    "success": true,
    "notification_id": 456
  }
}
```

**说明**:

- 通常在创建回复评论后调用
- 会自动通知父评论的作者

---

## 💻 前端集成示例

### React/Next.js 示例

#### 1. 获取评论树

```tsx
import { useState, useEffect } from 'react';

interface Comment {
  id: number;
  content: string;
  author_name: string;
  likes: number;
  depth: number;
  children: Comment[];
}

function CommentsSection({ articleId }: { articleId: number }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [sortBy, setSortBy] = useState('latest');
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchComments();
  }, [articleId, sortBy, page]);

  const fetchComments = async () => {
    const response = await fetch(
      `/api/v1/comments-enhanced/article/${articleId}?sort_by=${sortBy}&page=${page}`
    );
    const data = await response.json();
    setComments(data.data.comments);
  };

  return (
    <div>
      {/* 排序选择 */}
      <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
        <option value="latest">最新评论</option>
        <option value="oldest">最早评论</option>
        <option value="popular">最热评论</option>
      </select>

      {/* 评论列表 */}
      <div>
        {comments.map(comment => (
          <CommentItem key={comment.id} comment={comment} />
        ))}
      </div>
    </div>
  );
}
```

#### 2. 评论组件（支持嵌套）

```tsx
function CommentItem({ comment }: { comment: Comment }) {
  const [likes, setLikes] = useState(comment.likes);
  const [userVote, setUserVote] = useState<'like' | 'dislike' | null>(null);

  // 获取用户投票状态
  useEffect(() => {
    fetchUserVote();
  }, []);

  const fetchUserVote = async () => {
    try {
      const response = await fetch(`/api/v1/comments-enhanced/${comment.id}/vote`, {
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      });
      const data = await response.json();
      setUserVote(data.data.vote_type);
    } catch (error) {
      console.error('Failed to fetch vote:', error);
    }
  };

  // 点赞
  const handleLike = async () => {
    try {
      const response = await fetch(`/api/v1/comments-enhanced/${comment.id}/like`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      });
      const data = await response.json();
      setLikes(data.data.likes);
      setUserVote(data.data.action === 'liked' ? 'like' : null);
    } catch (error) {
      console.error('Failed to like:', error);
    }
  };

  // 反对
  const handleDislike = async () => {
    try {
      const response = await fetch(`/api/v1/comments-enhanced/${comment.id}/dislike`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      });
      const data = await response.json();
      setLikes(data.data.likes);
      setUserVote(data.data.action === 'disliked' ? 'dislike' : null);
    } catch (error) {
      console.error('Failed to dislike:', error);
    }
  };

  return (
    <div style={{ marginLeft: `${comment.depth * 20}px` }}>
      <div className="comment">
        <p>{comment.content}</p>
        <div className="comment-author">{comment.author_name}</div>
        
        {/* 点赞/反对按钮 */}
        <div className="comment-actions">
          <button 
            onClick={handleLike}
            className={userVote === 'like' ? 'active' : ''}
          >
            👍 {likes}
          </button>
          <button 
            onClick={handleDislike}
            className={userVote === 'dislike' ? 'active' : ''}
          >
            👎
          </button>
          <button>回复</button>
        </div>
      </div>

      {/* 递归渲染子评论 */}
      {comment.children && comment.children.length > 0 && (
        <div className="comment-children">
          {comment.children.map(child => (
            <CommentItem key={child.id} comment={child} />
          ))}
        </div>
      )}
    </div>
  );
}
```

#### 3. 创建回复评论

```tsx
function ReplyForm({ parentId, onSuccess }: { parentId: number, onSuccess: () => void }) {
  const [content, setContent] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      // 创建评论（假设已有创建评论的 API）
      const response = await fetch('/api/v1/comments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          article_id: articleId,
          parent_id: parentId,
          content: content,
        }),
      });

      const data = await response.json();

      // 发送通知
      await fetch(`/api/v1/comments-enhanced/${data.data.id}/notify-reply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      });

      setContent('');
      onSuccess();
    } catch (error) {
      console.error('Failed to create reply:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="写下你的回复..."
      />
      <button type="submit">提交回复</button>
    </form>
  );
}
```

---

## 📊 排序策略

### 1. 最新评论 (latest)

**适用场景**: 讨论活跃的 articles
**优点**: 用户能看到最新的讨论
**缺点**: 优质老评论可能被淹没

### 2. 最早评论 (oldest)

**适用场景**: 按时间顺序阅读
**优点**: 保持对话的连贯性
**缺点**: 新评论不容易被发现

### 3. 最热评论 (popular)

**适用场景**: 突出优质内容
**优点**: 高质量评论排在前面
**缺点**: 新评论需要时间积累点赞

---

## 🔧 配置选项

### 修改每页数量

编辑 API 端点：

```python
per_page: int = Query(default=20, ge=1, le=100)  # 修改最大值
```

### 添加新的排序方式

在 `CommentEnhancedService.get_comments_tree` 中添加：

```python
elif sort_by == 'random':
    query = query.order_by(func.random())
```

### 调整通知逻辑

编辑 `notify_comment_reply` 方法：

```python
# 可以添加邮件通知、推送通知等
if should_send_email:
    send_email_notification(parent_comment.user_id, new_comment)
```

---

## ⚠️ 注意事项

### 1. 性能优化

**问题**: 深层嵌套可能导致性能问题

**解决方案**:

- 限制嵌套深度（建议最多 5-10 层）
- 使用懒加载（点击"加载更多回复"）
- 缓存评论树

```python
# 限制嵌套深度
def _build_comment_tree(self, comments, max_depth=5):
    # ...
    if comment_dict['depth'] >= max_depth:
        comment_dict['children'] = []  # 不再嵌套
```

### 2. 防刷机制

**问题**: 用户可能恶意点赞/反对

**解决方案**:

- 限制投票频率
- 检测异常行为
- 使用 Redis 缓存投票记录

```python
# 检查投票频率
last_vote_time = await cache.get(f"user_vote_time:{user_id}")
if last_vote_time and time.time() - last_vote_time < 1:
    raise ValueError("操作太频繁")
```

### 3. 数据一致性

**问题**: 点赞数和实际投票可能不一致

**解决方案**:

- 使用事务确保一致性
- 定期同步点赞数
- 提供手动修复工具

---

## 🔍 测试方法

### 1. 单元测试

```python
async def test_like_comment():
    # 创建测试数据
    comment = create_test_comment()
    user = create_test_user()

    # 点赞
    result = await comment_enhanced_service.like_comment(db, comment.id, user.id)
    assert result['action'] == 'liked'
    assert result['likes'] == 1

    # 再次点赞（应取消）
    result = await comment_enhanced_service.like_comment(db, comment.id, user.id)
    assert result['action'] == 'unliked'
    assert result['likes'] == 0
```

### 2. API 测试

```bash
# 测试获取评论树
curl "http://localhost:9421/api/v1/comments-enhanced/article/1?sort_by=latest"

# 测试点赞
curl -X POST "http://localhost:9421/api/v1/comments-enhanced/1/like" \
  -H "Authorization: Bearer TOKEN"

# 测试获取投票状态
curl "http://localhost:9421/api/v1/comments-enhanced/1/vote" \
  -H "Authorization: Bearer TOKEN"
```

---

## 📈 监控与分析

### 跟踪评论活动

```python
# 在点赞/反对时记录日志
logger.info(f"User {user_id} {action} comment {comment_id}")

# 发送到分析平台
analytics.track('Comment Liked', {
    'comment_id': comment_id,
    'user_id': user_id,
    'article_id': article_id,
})
```

### 监控热门评论

```python
# 定期查询最热评论
async def get_trending_comments():
    stmt = select(Comment).order_by(desc(Comment.likes)).limit(10)
    result = await db.execute(stmt)
    return result.scalars().all()
```

---

## 🎯 最佳实践

### 1. 用户体验

- 显示点赞动画反馈
- 实时更新点赞数
- 提供"加载中"状态
- 错误提示友好

### 2. 性能优化

- 缓存评论树（Redis）
- 懒加载深层嵌套
- 分页加载评论
- 预取用户投票状态

### 3. 安全性

- 验证用户权限
- 防止 SQL 注入
- 过滤敏感内容
- 限制评论长度

---

## 🚀 未来增强

### 计划功能

- [ ] 评论编辑/删除
- [ ] @提及用户
- [ ] 评论表情反应
- [ ] 评论举报
- [ ] 管理员审核界面
- [ ] 垃圾评论过滤
- [ ] 评论导出

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
