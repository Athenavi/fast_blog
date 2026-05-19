# FastBlog Helm Chart

## 介绍

这是FastBlog的Kubernetes Helm Chart，用于在Kubernetes集群中快速部署FastBlog应用。

## 前置要求

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner支持（用于持久化存储）

## 安装

### 添加依赖仓库

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 安装Chart

```bash
# 使用默认配置
helm install fastblog ./k8s/helm

# 使用自定义配置
helm install fastblog ./k8s/helm -f custom-values.yaml

# 指定命名空间
helm install fastblog ./k8s/helm -n fastblog --create-namespace
```

## 配置

以下是可配置的参数及其默认值：

### 应用配置

| 参数                        | 描述    | 默认值                 |
|---------------------------|-------|---------------------|
| `replicaCount`            | 副本数量  | `1`                 |
| `image.repository`        | 镜像仓库  | `fastblog/fastblog` |
| `image.tag`               | 镜像标签  | `latest`            |
| `service.type`            | 服务类型  | `ClusterIP`         |
| `service.port`            | 服务端口  | `9421`              |
| `resources.limits.cpu`    | CPU限制 | `4`                 |
| `resources.limits.memory` | 内存限制  | `4Gi`               |

### PostgreSQL配置

| 参数                                    | 描述           | 默认值                 |
|---------------------------------------|--------------|---------------------|
| `postgresql.enabled`                  | 启用PostgreSQL | `true`              |
| `postgresql.auth.postgresPassword`    | PostgreSQL密码 | `fastblog_password` |
| `postgresql.auth.database`            | 数据库名称        | `fastblog`          |
| `postgresql.primary.persistence.size` | 存储大小         | `10Gi`              |

### Redis配置

| 参数                              | 描述      | 默认值    |
|---------------------------------|---------|--------|
| `redis.enabled`                 | 启用Redis | `true` |
| `redis.master.persistence.size` | 存储大小    | `2Gi`  |

### Meilisearch配置

| 参数                             | 描述            | 默认值                   |
|--------------------------------|---------------|-----------------------|
| `meilisearch.enabled`          | 启用Meilisearch | `true`                |
| `meilisearch.masterKey`        | Master密钥      | `fastblog_master_key` |
| `meilisearch.persistence.size` | 存储大小          | `5Gi`                 |

### Ingress配置

| 参数                      | 描述        | 默认值              |
|-------------------------|-----------|------------------|
| `ingress.enabled`       | 启用Ingress | `false`          |
| `ingress.hosts[0].host` | 主机名       | `fastblog.local` |
| `ingress.tls`           | TLS配置     | `[]`             |

## 示例配置

### 生产环境配置 (production-values.yaml)

```yaml
replicaCount: 3

image:
  repository: fastblog/fastblog
  tag: "1.0.0"

resources:
  limits:
    cpu: 4
    memory: 4Gi
  requests:
    cpu: 2
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: blog.example.com
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls:
    - secretName: fastblog-tls
      hosts:
        - blog.example.com

postgresql:
  primary:
    persistence:
      size: 50Gi
    resources:
      limits:
        cpu: 4
        memory: 4Gi

redis:
  master:
    persistence:
      size: 5Gi

config:
  secretKey: "your-secure-secret-key"
  debug: false
```

### 开发环境配置 (dev-values.yaml)

```yaml
replicaCount: 1

resources:
  limits:
    cpu: 2
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

postgresql:
  primary:
    persistence:
      size: 5Gi

config:
  debug: true
```

## 升级

```bash
# 升级Chart
helm upgrade fastblog ./k8s/helm -f production-values.yaml

# 查看历史版本
helm history fastblog

# 回滚到上一个版本
helm rollback fastblog
```

## 卸载

```bash
# 卸载Chart（保留PVC）
helm uninstall fastblog

# 完全卸载（包括PVC）
helm uninstall fastblog
kubectl delete pvc -l app.kubernetes.io/instance=fastblog
```

## 监控

### 查看Pod状态

```bash
kubectl get pods -l app.kubernetes.io/instance=fastblog
```

### 查看日志

```bash
kubectl logs -l app.kubernetes.io/instance=fastblog -f
```

### 查看服务

```bash
kubectl get svc -l app.kubernetes.io/instance=fastblog
```

### 端口转发（本地访问）

```bash
kubectl port-forward svc/fastblog 9421:9421
```

## 备份和恢复

### 备份数据库

```bash
kubectl exec -it $(kubectl get pod -l app.kubernetes.io/name=postgresql -o jsonpath="{.items[0].metadata.name}") -- pg_dump -U postgres fastblog > backup.sql
```

### 恢复数据库

```bash
cat backup.sql | kubectl exec -i $(kubectl get pod -l app.kubernetes.io/name=postgresql -o jsonpath="{.items[0].metadata.name}") -- psql -U postgres fastblog
```

## 故障排查

### Pod无法启动

```bash
# 查看Pod详情
kubectl describe pod <pod-name>

# 查看日志
kubectl logs <pod-name>
```

### 数据库连接失败

```bash
# 检查PostgreSQL服务
kubectl get svc -l app.kubernetes.io/name=postgresql

# 测试数据库连接
kubectl run -it --rm postgres-client --image=postgres:15 --restart=Never -- psql -h fastblog-postgresql -U postgres -d fastblog
```

### 存储空间不足

```bash
# 查看PVC使用情况
kubectl get pvc

# 扩展PVC
kubectl patch pvc <pvc-name> -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

## 最佳实践

1. **使用Secret管理敏感信息**
   ```bash
   kubectl create secret generic fastblog-secrets \
     --from-literal=db-password=your-password \
     --from-literal=secret-key=your-secret-key
   ```

2. **配置资源限制**
    - 始终设置requests和limits
    - 根据实际负载调整资源配额

3. **启用自动扩缩容**
    - 配置HPA以应对流量波动
    - 设置合理的min/max副本数

4. **定期备份**
    - 使用CronJob定时备份数据库
    - 将备份存储到外部存储（如S3）

5. **监控和告警**
    - 集成Prometheus监控
    - 配置告警规则

## 更多信息

- [FastBlog官方文档](https://github.com/yourusername/fast_blog)
- [Helm文档](https://helm.sh/docs/)
- [Kubernetes文档](https://kubernetes.io/docs/)
