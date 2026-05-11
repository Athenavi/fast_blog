#!/bin/bash
# ============================================================================
# FastBlog 部署脚本
# ============================================================================
# 用途: 自动化部署 FastBlog 到生产环境
# 用法: ./deploy.sh [environment]
# 示例: ./deploy.sh production
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
ENVIRONMENT=${1:-production}
PROJECT_DIR="/opt/fastblog"
BACKUP_DIR="/opt/backups/fastblog"
LOG_FILE="/var/log/fastblog/deploy.log"

# ============================================================================
# 工具函数
# ============================================================================

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        STEP)
            echo -e "\n${BLUE}==>${NC} ${GREEN}$message${NC}"
            ;;
    esac
    
    # 写入日志文件
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log ERROR "请使用 root 权限运行此脚本"
        exit 1
    fi
}

check_dependencies() {
    log STEP "检查依赖..."
    
    local deps=("python3" "pip3" "git" "nginx" "postgresql")
    
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            log ERROR "$dep 未安装"
            exit 1
        fi
    done
    
    log INFO "所有依赖已安装"
}

backup_current() {
    log STEP "备份当前版本..."
    
    local backup_path="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_path"
    
    # 备份代码
    if [ -d "$PROJECT_DIR" ]; then
        cp -r "$PROJECT_DIR" "$backup_path/code"
        log INFO "代码备份完成: $backup_path/code"
    fi
    
    # 备份数据库
    if command -v pg_dump &> /dev/null; then
        pg_dump -U postgres fast_blog > "$backup_path/database.sql" 2>/dev/null || true
        log INFO "数据库备份完成: $backup_path/database.sql"
    fi
    
    # 保留最近 5 个备份
    ls -t "$BACKUP_DIR"/backup_* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true
    
    log INFO "备份完成"
}

update_code() {
    log STEP "更新代码..."
    
    cd "$PROJECT_DIR"
    
    # 拉取最新代码
    git pull origin main
    
    # 安装依赖
    pip3 install -r requirements.txt
    
    log INFO "代码更新完成"
}

migrate_database() {
    log STEP "执行数据库迁移..."
    
    cd "$PROJECT_DIR"
    
    # 运行 Alembic 迁移
    alembic upgrade head
    
    log INFO "数据库迁移完成"
}

restart_services() {
    log STEP "重启服务..."
    
    # 重启 FastAPI 应用
    systemctl restart fastblog
    
    # 重启 Nginx
    systemctl reload nginx
    
    log INFO "服务重启完成"
}

health_check() {
    log STEP "健康检查..."
    
    sleep 5
    
    # 检查应用是否运行
    if systemctl is-active --quiet fastblog; then
        log INFO "✅ FastBlog 服务运行正常"
    else
        log ERROR "❌ FastBlog 服务启动失败"
        exit 1
    fi
    
    # 检查 HTTP 响应
    local http_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9421/health)
    
    if [ "$http_status" = "200" ]; then
        log INFO "✅ HTTP 健康检查通过"
    else
        log ERROR "❌ HTTP 健康检查失败 (状态码: $http_status)"
        exit 1
    fi
    
    log INFO "健康检查完成"
}

cleanup() {
    log STEP "清理临时文件..."
    
    # 清理 Python 缓存
    find "$PROJECT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    
    # 清理旧日志
    find /var/log/fastblog -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
    
    log INFO "清理完成"
}

# ============================================================================
# 主流程
# ============================================================================

main() {
    log STEP "开始部署 FastBlog ($ENVIRONMENT)"
    
    # 前置检查
    check_root
    check_dependencies
    
    # 备份
    backup_current
    
    # 更新代码
    update_code
    
    # 数据库迁移
    migrate_database
    
    # 重启服务
    restart_services
    
    # 健康检查
    health_check
    
    # 清理
    cleanup
    
    log STEP "🎉 部署成功完成!"
    log INFO "访问地址: https://yourdomain.com"
    log INFO "管理后台: https://yourdomain.com/admin"
}

# 执行主流程
main "$@"
