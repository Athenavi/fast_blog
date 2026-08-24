// FastBlog k6 压测基线脚本
// 用法:
//   k6 run --vus 20 --duration 60s tests/load/k6/benchmark.js
// 或带环境变量:
//   K6_BASE_URL=https://your-domain.com k6 run tests/load/k6/benchmark.js
//
// 覆盖路径: 首页聚合 / 文章列表 / 文章详情 / 搜索 / 前端首页HTML
// 阈值(默认): 首页 P95<200ms, 列表 P95<300ms, 详情 P95<250ms
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.K6_BASE_URL || 'http://localhost:9421';
const API = `${BASE_URL}/api/v2`;

// 随机客户端 IP（模拟反代后多真实客户端，规避单 IP 限流桶干扰端点性能测量）
function clientIp() {
  return `${Math.floor(Math.random() * 190) + 10}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`;
}

// 自定义指标（便于按路径查看分布）
const homeTrend = new Trend('home_p95');
const listTrend = new Trend('list_p95');
const detailTrend = new Trend('detail_p95');
const searchTrend = new Trend('search_p95');
const errorRate = new Rate('error_rate');

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // 爬坡
    { duration: '60s', target: 50 },  // 稳定并发
    { duration: '30s', target: 0 },   // 收尾
  ],
  thresholds: {
    // 100k stars 目标门槛（可随优化收紧）
    'http_req_duration{scenario:home}': ['p(95)<200'],
    'http_req_duration{scenario:list}': ['p(95)<300'],
    'http_req_duration{scenario:detail}': ['p(95)<250'],
    'error_rate': ['rate<0.01'],
  },
};

// setup: 拉一个真实文章 slug 供详情场景使用
export function setup() {
  const res = http.get(`${API}/articles?page=1&per_page=10`);
  let slug = null;
  try {
    const data = res.json();
    const items = data?.data || [];
    if (Array.isArray(items) && items.length) {
      slug = items[0].slug || items[0].id;
    }
  } catch (e) { /* 忽略 */ }
  return { slug: slug || '1' };
}

export default function (data) {
  const h = { 'X-Forwarded-For': clientIp() };

  // 1) 首页聚合数据
  let r = http.get(`${API}/home/data`, { headers: h, tags: { scenario: 'home' } });
  check(r, { 'home 200': (x) => x.status === 200 });
  errorRate.add(r.status >= 500);
  homeTrend.add(r.timings.duration);

  sleep(0.3);

  // 2) 文章列表（首页流 + 分页）
  r = http.get(`${API}/articles?page=1&per_page=10`, { headers: h, tags: { scenario: 'list' } });
  check(r, { 'list 200': (x) => x.status === 200 });
  errorRate.add(r.status >= 500);
  listTrend.add(r.timings.duration);

  sleep(0.3);

  // 3) 文章详情（列表页 -> 详情页 转换路径）
  r = http.get(`${API}/articles/p/${data.slug}`, { headers: h, tags: { scenario: 'detail' } });
  check(r, { 'detail 200': (x) => x.status === 200 });
  errorRate.add(r.status >= 500);
  detailTrend.add(r.timings.duration);

  sleep(0.3);

  // 4) 搜索（真实端点 /api/v2/articles/search；顶层 /api/v2/search 无此路由）
  r = http.get(`${API}/articles/search?q=fast`, { headers: h, tags: { scenario: 'search' } });
  check(r, { 'search 200/404': (x) => x.status === 200 || x.status === 404 });
  errorRate.add(r.status >= 500);
  searchTrend.add(r.timings.duration);

  sleep(0.5);
}

// 单独的前端首页 HTML 场景（真实用户首屏）
export function frontend_home() {
  const r = http.get(`${BASE_URL}/`, { tags: { scenario: 'frontend' } });
  check(r, { 'frontend 200': (x) => x.status === 200 });
  errorRate.add(r.status >= 500);
}
