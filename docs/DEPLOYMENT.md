# FastBlog 部署指南

## 📋 文档信息

**版本**：v2.1.0  
**更新时间**：2026年2月

## 🚀 Docker部署（推荐）

### 环境准备
``bash
# 系统要求: Ubuntu 20.04+/CentOS 8+
# 安装Docker和Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 部署步骤
```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 配置环境
cp .env.production.example .env
# 编辑.env文件配置生产环境

# 3. 启动服务
docker-compose up -d

# 4. 检查状态
docker-compose ps
```

## 🔧 传统部署

### 后端部署
```bash
# 1. 创建用户和目录
sudo useradd -r -s /bin/false fastblog
sudo mkdir -p /opt/fastblog
sudo chown fastblog:fastblog /opt/fastblog

# 2. 部署代码
cd /opt/fastblog
sudo -u fastblog python3 -m venv venv
sudo -u fastblog venv/bin/pip install -r requirements.txt

# 3. 配置Supervisor
sudo tee /etc/supervisor/conf.d/fastblog.conf << EOF
[program:fastblog]
command=/opt/fastblog/venv/bin/python main.py --mode supervisor
directory=/opt/fastblog
user=fastblog
autostart=true
autorestart=true
EOF
```

### 前端部署
```bash
cd /opt/fastblog/frontend-next
npm install
npm run build

# 配置Nginx反向代理
sudo tee /etc/nginx/sites-available/fastblog << EOF
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api/ {
        proxy_pass http://localhost:9421;
    }
}
EOF
```

## 🔒 安全配置

### SSL证书
```bash
# Let's Encrypt证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 防火墙
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
```

## 📊 监控和备份

### 监控配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastblog'
    static_configs:
      - targets: ['localhost:9421']
```

### 备份脚本
```bash
#!/bin/bash
# daily backup
DATE=$(date +%Y%m%d)
pg_dump -U fastblog fastblog > /backups/db_$DATE.sql
tar -czf /backups/app_$DATE.tar.gz /opt/fastblog
```

## 🆘 故障排除

### 常见问题
```bash
# 检查服务状态
sudo systemctl status fastblog
sudo journalctl -u fastblog -f

# 检查端口
sudo netstat -tuln | grep :9421

# 重启服务
sudo supervisorctl restart fastblog
```

## 📋 部署检查清单

### 部署前
- [ ] 服务器资源充足
- [ ] 域名解析完成
- [ ] SSL证书准备
- [ ] 环境变量配置

### 部署后
- [ ] 应用正常启动
- [ ] 数据库连接正常
- [ ] API接口可用
- [ ] 前端页面正常
- [ ] SSL证书生效
- [ ] 监控配置完成

---
*文档版本：v2.1.0 | 更新时间：2026年2月*