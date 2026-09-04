# FastBlog 部署指南

> 本文档包含各主流云平台的部署步骤、云平台对比和部署检查清单。

---

## 一、云平台部署指南

### 1. Amazon Web Services (AWS)

| 项目   | 详情                    |
|------|-----------------------|
| 覆盖范围 | Global                |
| 难度   | Medium                |
| 预估成本 | $50-200/month (中小型站点) |

#### 部署步骤

1. **创建 AWS 账户** — 注册 AWS 账户并设置账单提醒 ([aws.amazon.com](https://aws.amazon.com/))
2. **选择区域** — 选择离目标用户最近的区域（us-east-1, eu-west-1, ap-northeast-1），考虑延迟、数据主权和成本
3. **设置 VPC** — 创建虚拟私有云，配置子网和安全组
    - 创建公有和私有子网
    - 配置 NAT Gateway
    - 设置安全组规则（仅开放 80/443 端口）
4. **启动 EC2 实例** — 推荐 t3.medium 或 t3.large，使用 Amazon Linux 2 或 Ubuntu Server
5. **配置 RDS** — PostgreSQL 数据库
    - 选择 db.t3.small 或 db.t3.medium
    - 启用多可用区部署（生产环境）
    - 配置自动备份
    - 设置安全组仅允许 EC2 访问
6. **设置 ElastiCache** — Redis 缓存，推荐 cache.t3.micro 或 cache.t3.small
7. **配置 S3** — 对象存储
    - 创建存储桶，配置 CORS
    - 设置 CloudFront CDN
    - 启用版本控制
8. **设置 Route 53** — DNS 和域名
    - 注册或转移域名
    - 创建 A 记录指向 EC2 或 ALB
    - 配置 SSL 证书（Certificate Manager）
9. **部署应用**
    - Docker + ECS（推荐）
    - Kubernetes + EKS（大规模）
    - EC2 + Supervisor（简单部署）
10. **监控和告警** — CloudWatch
    - CPU、内存、磁盘监控
    - 设置告警阈值，配置 SNS 通知
    - 启用日志聚合

#### Terraform 示例

```hcl
provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "fastblog" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  vpc_security_group_ids = [aws_security_group.fastblog_sg.id]
  tags = { Name = "FastBlog" }
}

resource "aws_db_instance" "postgres" {
  allocated_storage = 20
  engine            = "postgres"
  engine_version    = "14"
  instance_class    = "db.t3.small"
  db_name           = "fastblog"
  username          = var.db_username
  password          = var.db_password
  skip_final_snapshot = true
}
```

#### 最佳实践

- 使用 Auto Scaling Group 实现弹性扩缩容
- 启用 CloudFront CDN 加速静态资源
- 使用 Secrets Manager 管理敏感信息
- 实施 Infrastructure as Code (Terraform/CloudFormation)
- 定期备份和测试恢复流程
- 使用 IAM Role 而非 Access Key
- 启用 VPC Flow Logs 进行网络监控

#### 成本优化

- 使用 Spot Instances 降低计算成本
- 购买 Reserved Instances（1年或3年）
- 使用 S3 Intelligent-Tiering
- 设置预算和成本告警
- 定期清理未使用的资源

---

### 2. Microsoft Azure

| 项目   | 详情                    |
|------|-----------------------|
| 覆盖范围 | Global                |
| 难度   | Medium                |
| 预估成本 | $50-200/month (中小型站点) |

#### 部署步骤

1. **创建 Azure 账户** — 注册 Azure 账户，新用户有 $200 免费额度 ([azure.microsoft.com](https://azure.microsoft.com/))
2. **创建资源组** — 按环境分离（dev/staging/prod）
3. **设置 Virtual Network** — 配置 VNet、子网和 NSG
4. **部署 Azure VM** — 推荐 Standard B2s 或 B2ms，使用 Ubuntu Server 20.04 LTS 或 CentOS
5. **配置 Azure Database for PostgreSQL** — Basic 或 General Purpose 层级，配置防火墙和备份
6. **设置 Azure Cache for Redis** — 推荐 C0 或 C1 层级
7. **配置 Azure Blob Storage** — 创建存储账户，配置 CDN
8. **设置 Azure DNS** — 创建 DNS 区域，配置 SSL 证书
9. **部署应用**
    - Azure App Service（PaaS，推荐）
    - Azure Kubernetes Service (AKS)
    - VM + Docker Compose
10. **监控和告警** — Azure Monitor + Application Insights

#### 最佳实践

- 使用 Availability Zones 提高可用性
- 实施 Azure Policy 进行治理
- 使用 Managed Identity 代替服务主体
- 启用 Azure Security Center
- 定期审查成本管理建议
- 使用 Azure DevOps 进行 CI/CD

> 可使用 ARM 模板或 Bicep 进行基础设施即代码部署

---

### 3. Google Cloud Platform (GCP)

| 项目   | 详情                    |
|------|-----------------------|
| 覆盖范围 | Global                |
| 难度   | Medium                |
| 预估成本 | $40-180/month (中小型站点) |

#### 部署步骤

1. **创建 GCP 项目** — ([cloud.google.com](https://cloud.google.com/))
2. **设置 VPC Network** — 创建 VPC、子网和防火墙规则
3. **创建 Compute Engine VM** — 推荐 e2-medium 或 e2-standard-2
4. **配置 Cloud SQL** — 托管 PostgreSQL
5. **设置 Memorystore** — Redis 缓存，推荐 basic_tier 1GB
6. **配置 Cloud Storage** — 设置对象存储和 Cloud CDN
7. **设置 Cloud DNS** — 创建托管区域
8. **部署应用**
    - Google Kubernetes Engine (GKE)
    - Cloud Run（无服务器容器）
    - Compute Engine（传统 VM）
9. **监控和日志** — Cloud Monitoring + Logging

#### 最佳实践

- 使用 Cloud Build 进行 CI/CD
- 实施 Organization Policies
- 使用 Service Accounts 最小权限原则
- 启用 Security Command Center
- 利用 Sustained Use Discounts

---

### 4. 阿里云

| 项目   | 详情                      |
|------|-------------------------|
| 覆盖范围 | 中国大陆为主，全球节点             |
| 难度   | Easy-Medium             |
| 预估成本 | ¥300-1500/month (中小型站点) |

#### 特殊说明

- 需要完成 ICP 备案才能在中国大陆提供服务
- 实名认证是必须的
- 中国大陆节点速度最优

#### 部署步骤

1. **注册阿里云账号** — 完成注册和实名认证 ([aliyun.com](https://www.aliyun.com/))，需要个人身份证或企业营业执照
2. **ICP 备案** — 使用中国大陆节点必须完成，通常需要 7-20 个工作日
3. **创建 VPC** — 设置专有网络，划分交换机，配置路由表和安全组
4. **购买 ECS 实例** — 推荐 ecs.t6.large 或 ecs.c6.large，使用 CentOS 7.9、Ubuntu 20.04 或 Alibaba Cloud Linux
5. **配置 RDS PostgreSQL** — 选择实例规格（pg.n2.small.1），设置白名单
6. **设置 KVStore for Redis** — 推荐社区版 1GB
7. **配置 OSS** — 创建 Bucket，设置 CDN 加速和防盗链
8. **配置域名和 SSL** — 在阿里云注册或转入域名，申请免费 SSL 证书
9. **部署应用**
    - ECS + Docker Compose
    - 容器服务 ACK（Kubernetes）
    - 函数计算 FC（无服务器）
10. **监控和告警** — 云监控

#### 最佳实践

- 使用 RAM 用户而非主账号
- 启用操作审计（ActionTrail）
- 使用 ROS（资源编排服务）
- 配置 DDoS 基础防护和 WAF
- 定期快照备份 ECS

#### 合规要求

- ICP 备案
- 公安联网备案
- 遵守《网络安全法》
- 数据存储在中国境内
- 内容审核机制

---

## 二、云平台对比

| 平台        | 优势                                 | 劣势                      | 适用场景                   | 计费模式            |
|-----------|------------------------------------|-------------------------|------------------------|-----------------|
| **AWS**   | 最全面的服务、全球覆盖最广、成熟生态、丰富文档            | 学习曲线陡峭、定价复杂、控制台复杂       | 大型企业、全球化应用、复杂架构        | 按使用量付费，预留实例折扣   |
| **Azure** | Microsoft 生态集成好、混合云方案强、企业级支持       | 部分服务不如 AWS 成熟、文档质量参差    | Microsoft 技术栈、企业客户、混合云 | 按使用量付费，预留实例折扣   |
| **GCP**   | Kubernetes 原生、AI/ML 能力强、网络性能优、定价透明 | 服务数量较少、企业支持不如 AWS/Azure | 数据驱动应用、AI/ML、初创公司      | 持续使用折扣，承诺使用折扣   |
| **阿里云**   | 中国大陆最快、本地化服务好、性价比高                 | 国际节点较少、英文文档不完善          | 面向中国用户的业务、电商、直播        | 按量付费、包年包月、抢占式实例 |

#### 选择标准

- 目标用户地理位置
- 预算和成本预期
- 技术栈兼容性
- 合规性要求
- 团队熟悉度
- 支持和服务质量

---

## 三、部署前检查清单

### 基础设施

- [ ] 选择合适的云平台和区域
- [ ] 配置 VPC/虚拟网络
- [ ] 设置安全组和防火墙规则
- [ ] 配置负载均衡器（如需要）
- [ ] 设置域名和 DNS
- [ ] 申请和配置 SSL 证书

### 数据库

- [ ] 选择数据库引擎和版本
- [ ] 配置数据库实例规格
- [ ] 设置备份策略
- [ ] 配置连接池
- [ ] 设置访问控制和白名单
- [ ] 启用慢查询日志

### 应用配置

- [ ] 设置环境变量
- [ ] 配置 SECRET_KEY
- [ ] 设置数据库连接字符串
- [ ] 配置 Redis 连接
- [ ] 设置邮件服务
- [ ] 配置文件存储（S3/OSS等）

### 安全

- [ ] 更新系统和依赖包
- [ ] 禁用 root SSH 登录
- [ ] 配置 SSH 密钥认证
- [ ] 设置 fail2ban
- [ ] 启用防火墙
- [ ] 配置速率限制
- [ ] 设置 CORS 策略
- [ ] 启用 HTTPS 强制跳转

### 监控

- [ ] 安装监控代理
- [ ] 配置 CPU/内存/磁盘告警
- [ ] 设置应用性能监控
- [ ] 配置日志聚合
- [ ] 设置错误追踪
- [ ] 配置 uptime 监控

### 备份

- [ ] 配置数据库自动备份
- [ ] 设置文件备份策略
- [ ] 测试恢复流程
- [ ] 配置备份保留策略
- [ ] 设置异地备份

### 性能优化

- [ ] 启用 Gzip/Brotli 压缩
- [ ] 配置浏览器缓存
- [ ] 设置 CDN
- [ ] 优化图片
- [ ] 启用 HTTP/2
- [ ] 配置数据库索引

### 合规性

- [ ] 隐私政策页面
- [ ] Cookie 同意横幅
- [ ] GDPR/CCPA 合规检查
- [ ] ICP 备案（如在中国）
- [ ] 数据保留策略
- [ ] 用户数据导出功能
