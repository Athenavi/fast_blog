import http from 'k6/http';
import {check, sleep} from 'k6';
import {Rate, Trend} from 'k6/metrics';

// ─── 配置 ──────────────────────────────────────────
// 默认直连后端（:9421）。若要压 nginx 入口（:4321），显式设置 BASE_URL：
//   BASE_URL=http://localhost:4321 k6 run tests/load/benchmark.js
// 注意 nginx 对 /api/ 有 30r/s、对登录有 5r/m 的限流，高并发下会拿到 503/429 ——
// 那是限流在生效，不是应用错误。
const BASE_URL = __ENV.BASE_URL || 'http://localhost:9421';
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

// ─── 响应约定 ──────────────────────────────────────
// v3 统一响应 {code, msg, data, pagination}，code === 200 才算成功。
function body(res) {
  try {
    return res.json();
  } catch (e) {
    return null;
  }
}

function ok(res) {
  const b = body(res);
  return res.status === 200 && b !== null && b.code === 200;
}

// ─── 登录获取 token ────────────────────────────────
// POST /api/v3/system/auth/login → data 内含 access_token，同时下发 access_token cookie
function login() {
  const res = http.post(
    `${BASE_URL}/api/v3/system/auth/login`,
    JSON.stringify({username: ADMIN_USER, password: ADMIN_PASS}),
    {headers: {'Content-Type': 'application/json'}},
  );

  if (!ok(res)) return null;

  const data = body(res).data || {};
  if (data.access_token) return data.access_token;

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

  // 1. 权限校验 (最频繁) —— 批量校验权限码
  let start = Date.now();
  let res = http.post(
    `${BASE_URL}/api/v3/system/permission/check`,
    JSON.stringify({codes: ['module_content:article:view']}),
    {headers},
  );
  PERMISSION_CHECK.add(Date.now() - start);
  check(res, {'perm check ok': (r) => ok(r)});
  ERROR_RATE.add(!ok(res));

  sleep(0.3);

  // 2. 用户列表
  res = http.get(`${BASE_URL}/api/v3/system/user?page=1&page_size=10`, {headers});
  check(res, {'users list': (r) => ok(r)});
  ERROR_RATE.add(!ok(res));

  sleep(0.3);

  // 3. 文章列表
  res = http.get(`${BASE_URL}/api/v3/content/article?page=1&page_size=10`, {headers});
  check(res, {'articles list': (r) => ok(r)});
  ERROR_RATE.add(!ok(res));

  sleep(0.5);

  // 4. 仪表盘统计
  res = http.get(`${BASE_URL}/api/v3/analytics/dashboard/overview`, {headers});
  check(res, {'dashboard overview': (r) => ok(r)});
  ERROR_RATE.add(!ok(res));

  sleep(0.3);

  // 5. 角色列表
  res = http.get(`${BASE_URL}/api/v3/system/role?page=1&page_size=10`, {headers});
  check(res, {'roles list': (r) => ok(r)});
  ERROR_RATE.add(!ok(res));

  sleep(0.3);

  // 6. 缓存统计
  res = http.get(`${BASE_URL}/api/v3/system/cache/stats`, {headers});
  check(res, {'cache stats': (r) => ok(r)});
  ERROR_RATE.add(!ok(res));

  sleep(1);
}
