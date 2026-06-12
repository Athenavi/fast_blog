import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── 配置 ──────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const ADMIN_USER = __ENV.ADMIN_USER || 'admin';
const ADMIN_PASS = __ENV.ADMIN_PASS || 'admin123';

const PERMISSION_CHECK = new Trend('perm_check_ms');
const ERROR_RATE = new Rate('errors');

// 阶段: 预热 → 爬升 → 稳定 → 高峰
export const options = {
  stages: [
    { duration: '30s', target: 5 },    // 预热
    { duration: '30s', target: 20 },   // 爬升
    { duration: '1m', target: 50 },    // 稳定
    { duration: '30s', target: 100 },  // 高峰
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.05'],
  },
};

// ─── 登录获取 token ────────────────────────────────
function login() {
  const res = http.post(`${BASE_URL}/api/v2/auth/login`, JSON.stringify({
    username: ADMIN_USER, password: ADMIN_PASS,
  }), { headers: { 'Content-Type': 'application/json' } });

  check(res, { 'login success': (r) => r.status === 200 });
  if (res.status !== 200) return null;

  // 从 cookie 中获取 token
  const cookies = res.cookies;
  return cookies['access_token'] ? cookies['access_token'][0].value : null;
}

// ─── 测试场景 ──────────────────────────────────────
export default function () {
  const token = login();
  if (!token) {
    ERROR_RATE.add(1);
    return;
  }

  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  // 1. 权限检查 (最频繁)
  let start = Date.now();
  let res = http.post(`${BASE_URL}/api/v3/admin/check-permission`,
    JSON.stringify({ permission_code: 'article:view', user_id: 0 }),
    { headers }
  );
  PERMISSION_CHECK.add(Date.now() - start);
  check(res, { 'perm check ok': (r) => r.status === 200 });
  ERROR_RATE.add(res.status !== 200);

  sleep(0.3);

  // 2. 用户列表
  res = http.get(`${BASE_URL}/api/v3/admin/users?page=1&per_page=10`, { headers });
  check(res, { 'users list': (r) => r.status === 200 });
  ERROR_RATE.add(res.status !== 200);

  sleep(0.3);

  // 3. 文章列表
  res = http.get(`${BASE_URL}/api/v3/admin/articles?page=1&per_page=10`, { headers });
  check(res, { 'articles list': (r) => r.status === 200 });
  ERROR_RATE.add(res.status !== 200);

  sleep(0.5);

  // 4. 仪表盘统计
  res = http.get(`${BASE_URL}/api/v3/admin/dashboard/stats`, { headers });
  check(res, { 'dashboard stats': (r) => r.status === 200 });
  ERROR_RATE.add(res.status !== 200);

  sleep(0.3);

  // 5. 角色列表
  res = http.get(`${BASE_URL}/api/v3/admin/roles?include_system=true`, { headers });
  check(res, { 'roles list': (r) => r.status === 200 });
  ERROR_RATE.add(res.status !== 200);

  sleep(0.3);

  // 6. 缓存统计
  res = http.get(`${BASE_URL}/api/v3/admin/cache-stats`, { headers });
  check(res, { 'cache stats': (r) => r.status === 200 });

  sleep(1);
}
