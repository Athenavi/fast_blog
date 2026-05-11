# 外部资源转存系统

## 概述

外部资源转存系统允许用户将互联网上的资源（图片、视频、音频、文档等）下载到本地服务器存储，并自动创建媒体记录。

## 核心功能

### ✅ 已实现功能

1. **下载任务管理**
    - 创建单个/批量下载任务
    - 任务状态跟踪（pending/downloading/completed/failed/cancelled）
    - 优先级队列管理
    - 失败自动重试（最多3次）

2. **断点续传支持**
    - 检测未完成的下载
    - 从上次中断位置继续下载
    - 避免重复下载大文件

3. **进度跟踪**
    - 实时下载进度（0-100%）
    - 文件大小和已下载大小
    - 预计完成时间

4. **后台队列处理**
    - 自动处理待处理任务（每30秒检查）
    - 并发控制（默认3个并发）
    - 异步非阻塞执行

5. **资源类型支持**
    - 图片（JPG, PNG, GIF, WebP）
    - 视频（MP4, WebM）
    - 音频（MP3）
    - 文档（PDF）
    - 其他二进制文件

6. **智能文件处理**
    - SHA256哈希去重
    - MIME类型自动检测
    - 文件扩展名推断
    - 自动创建媒体记录

## API端点

### 创建下载任务

```http
POST /api/v1/resource-transfer/download
```

**参数:**

- `url` (required): 资源URL
- `resource_type`: 资源类型 (image/video/audio/document/other)，默认 image
- `priority`: 优先级，数字越小优先级越高，默认 0

**示例:**

```bash
curl -X POST "http://localhost:9421/api/v1/resource-transfer/download?url=https://example.com/image.jpg&resource_type=image" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 批量创建任务

```http
POST /api/v1/resource-transfer/download/batch
```

**参数:**

- `urls`: URL列表
- `resource_type`: 资源类型

**示例:**

```bash
curl -X POST "http://localhost:9421/api/v1/resource-transfer/download/batch?urls=https://example.com/img1.jpg&urls=https://example.com/img2.jpg" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 获取任务列表

```http
GET /api/v1/resource-transfer/tasks?status=pending&page=1&per_page=20
```

**参数:**

- `status`: 状态过滤（可选）
- `page`: 页码
- `per_page`: 每页数量

### 获取任务详情

```http
GET /api/v1/resource-transfer/tasks/{task_id}
```

### 取消任务

```http
POST /api/v1/resource-transfer/tasks/{task_id}/cancel
```

### 重试失败任务

```http
POST /api/v1/resource-transfer/tasks/{task_id}/retry
```

### 手动处理队列

```http
POST /api/v1/resource-transfer/process-queue?limit=5
```

**注意:** 此接口需要管理员权限

### 获取统计信息

```http
GET /api/v1/resource-transfer/stats
```

返回各状态任务数量和总下载量。

## 数据库模型

### DownloadTask

| 字段              | 类型           | 描述          |
|-----------------|--------------|-------------|
| id              | bigint       | 任务ID        |
| user_id         | bigint       | 用户ID        |
| source_url      | string(2048) | 源URL        |
| resource_type   | string(50)   | 资源类型        |
| filename        | string(255)  | 文件名         |
| total_size      | bigint       | 文件总大小       |
| downloaded_size | bigint       | 已下载大小       |
| progress        | integer      | 下载进度(0-100) |
| status          | string(50)   | 任务状态        |
| error_message   | text         | 错误信息        |
| media_id        | bigint       | 关联的媒体ID     |
| retry_count     | bigint       | 重试次数        |
| max_retries     | bigint       | 最大重试次数      |
| priority        | bigint       | 优先级         |
| created_at      | datetime     | 创建时间        |
| started_at      | datetime     | 开始时间        |
| completed_at    | datetime     | 完成时间        |

## 使用场景

### 1. 文章封面图片转存

用户在编辑器中输入外链图片URL，系统自动下载并设置为本地封面。

```javascript
// 前端示例
const response = await fetch('/api/v1/resource-transfer/download', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        url: 'https://example.com/cover.jpg',
        resource_type: 'image'
    })
});

const {data} = await response.json();
console.log('Task ID:', data.task_id);
```

### 2. 批量导入外部资源

从其他平台迁移内容时，批量下载所有引用的图片和视频。

```python
# Python示例
import requests

urls = [
    "https://old-site.com/image1.jpg",
    "https://old-site.com/image2.png",
    "https://old-site.com/video.mp4"
]

response = requests.post(
    "http://localhost:9421/api/v1/resource-transfer/download/batch",
    params={"urls": urls, "resource_type": "image"},
    headers={"Authorization": f"Bearer {token}"}
)
```

### 3. 监控下载进度

轮询任务状态，显示进度条。

```javascript
async function monitorProgress(taskId) {
    const interval = setInterval(async () => {
        const response = await fetch(`/api/v1/resource-transfer/tasks/${taskId}`);
        const {data} = await response.json();

        console.log(`Progress: ${data.progress}%`);

        if (data.status === 'completed') {
            clearInterval(interval);
            console.log('Download complete! Media ID:', data.media_id);
        } else if (data.status === 'failed') {
            clearInterval(interval);
            console.error('Download failed:', data.error_message);
        }
    }, 1000);
}
```

## 配置选项

在 `shared/services/download_queue_processor.py` 中可配置：

```python
download_queue_processor = DownloadQueueProcessor(
    max_concurrent=3,  # 最大并发下载数
    check_interval=30  # 检查间隔（秒）
)
```

## 性能考虑

1. **并发控制**: 默认最多3个并发下载，避免占用过多带宽
2. **超时设置**: 单个下载任务超时5分钟
3. **文件大小限制**: 最大100MB
4. **断点续传**: 大文件下载中断后可继续，无需重新开始
5. **哈希去重**: 相同内容的文件只存储一次

## 安全考虑

1. **URL验证**: 仅允许 http:// 和 https:// 协议
2. **文件大小限制**: 防止下载超大文件
3. **MIME类型检测**: 基于文件魔数而非扩展名
4. **用户权限**: 只能查看和管理自己的任务
5. **管理员权限**: 队列处理接口需要管理员权限

## 测试

运行测试脚本：

```bash
python test_resource_transfer.py
```

## 故障排除

### 任务一直处于 pending 状态

- 检查后台处理器是否启动（查看日志）
- 确认数据库连接正常
- 尝试手动触发队列处理：`POST /api/v1/resource-transfer/process-queue`

### 下载失败

- 检查网络连接
- 验证URL是否可访问
- 查看任务的 `error_message` 字段
- 检查文件大小是否超过限制（100MB）

### 文件保存失败

- 确认 `storage/objects` 目录存在且可写
- 检查磁盘空间
- 查看应用日志获取详细错误信息

## 未来增强

- [ ] 支持更多云存储后端（S3, OSS, etc.）
- [ ] 图片自动优化（压缩、格式转换）
- [ ] 视频缩略图生成
- [ ] 下载速度限制
- [ ] 更详细的进度报告（下载速度、ETA）
- [ ] Webhook通知（下载完成时触发）
- [ ] 集成到富文本编辑器（一键转存所有外链资源）
