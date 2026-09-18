# ============================================================================
# FastBlog Frontend Dockerfile — Nuxt 4（前台 SSR + 后台 CSR 同工程）
# Multi-stage build: Node 构建（nuxt build）→ Node 运行时（.output server）
#
# 与「静态导出 + nginx」形态的区别：
#   - 前台保留 SSR（首屏直出 / SEO / routeRules 的 swr 缓存）
#   - 外部流量统一由独立 nginx 服务入口（见 nginx/conf.d/fastblog.conf），
#     本容器只在内网暴露 3000，不承担 TLS/限流/安全头
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1: 构建
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /app

# 依赖清单先拷贝，单独成层便于缓存
COPY package.json package-lock.json ./
# 与仓库 CI 保持一致：锁定版本安装（不跳过 optional 依赖，@nuxt/image 的 sharp 需要）
RUN npm ci

# 源码 + .env.production（nuxt build 会以 --dotenv .env.production 读取）
COPY . .

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: 运行时（只带 .output，不含源码与 devDependencies）
# ---------------------------------------------------------------------------
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

# 非 root 运行
RUN addgroup -g 1001 -S nodejs \
    && adduser -u 1001 -S nuxt -G nodejs

COPY --from=builder --chown=nuxt:nodejs /app/.output ./.output

USER nuxt

EXPOSE 3000

# 用 Node 自带 fetch 做探活，避免额外安装 curl/wget
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["node", ".output/server/index.mjs"]
