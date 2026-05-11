# 多阶段构建 - FastBlog
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 生产阶段
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' appuser

# 从builder阶段复制Python包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/media \
    /app/upload_chunks \
    /app/static \
    /app/themes \
    /app/plugins \
    /app/translations \
    /app/backups \
    /app/logs \
    /app/storage \
    && chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 9421

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9421/api/v1/health || exit 1

# 启动命令
CMD ["python", "main.py"]
