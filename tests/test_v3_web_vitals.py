"""P6：前端 Web Vitals（RUM）上报接线

背景：前端 ``useWebVitals.ts`` 一直在采集 5 项核心指标，但因为没有接收端点，只把样本写进
sessionStorage；后端 ``performance_tracker`` 同样零引用。两边都「半成品」。
本批把 ``POST /api/v3/system/health/web-vitals`` 接到 ``PagePerformanceTracker``，
并在 nuxt.config 里把 ``rumEndpoint`` 默认指向它。

同时统一了 tracker 的 CWV 判定口径：原实现按「秒」判 FCP/LCP（<1.8/<2.5）却按「毫秒」判
FID（<100），与前端 web-vitals 上报的毫秒值混用会得出错误达标率。

覆盖：
  1. 上报端点公开可用（访客未登录也要能上报）
  2. 同一页面的多条指标聚合成一条记录，汇总能读回
  3. 达标率按毫秒阈值判定，且只判定「实际采集到的指标」
  4. 单次最多 50 条；非法指标名被 pydantic 拒绝
  5. 汇总端点需要鉴权
"""

import shared.services.performance.performance_tracker as tracker_module
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.services.performance.performance_tracker import PagePerformanceTracker
from src.api.v3 import register_v3_routes
from src.api.v3.modules.system.health.schema import WebVitalSample
from src.api.v3.modules.system.health.service import health_service

PATH = "/api/v3/system/health/web-vitals"
SUMMARY_PATH = f"{PATH}/summary"

SAMPLE = [
    {"name": "LCP", "value": 2100.0, "rating": "good", "path": "/articles/a", "sessionId": "s1"},
    {"name": "CLS", "value": 0.05, "rating": "good", "path": "/articles/a", "sessionId": "s1"},
    {"name": "INP", "value": 120.0, "rating": "good", "path": "/articles/a", "sessionId": "s1"},
]


def _client() -> TestClient:
    app = FastAPI()
    register_v3_routes(app)
    return TestClient(app, raise_server_exceptions=False)


def test_ingest_is_public_and_aggregates_per_path(monkeypatch):
    monkeypatch.setattr(tracker_module, "performance_tracker", PagePerformanceTracker())

    resp = _client().post(PATH, json=SAMPLE)

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"] == {"accepted": 3, "pages": 1}


def test_summary_reads_back_ingested_samples(monkeypatch):
    monkeypatch.setattr(tracker_module, "performance_tracker", PagePerformanceTracker())

    health_service.ingest_web_vitals([WebVitalSample(**item) for item in SAMPLE])
    summary = health_service.web_vitals_summary(hours=1)

    overall = summary["overall"]
    assert overall["total_samples"] == 1  # 同一页面的三条指标聚合成一条记录
    assert overall["total_pages"] == 1
    assert overall["avg_largest_contentful_paint"] == 2100.0
    assert overall["avg_interaction_to_next_paint"] == 120.0
    assert overall["cwv_pass_rate"] == 100.0  # 2100≤2500、120≤200、0.05≤0.1
    assert summary["slowest_pages"]


def test_cwv_pass_rate_uses_ms_thresholds():
    tracker = PagePerformanceTracker()

    # 毫秒口径：LCP 2500ms / CLS 0.1 都算达标
    assert tracker._calculate_cwv_pass_rate([{"core_web_vitals": {"lcp": 2500, "cls": 0.1}}]) == 100.0
    # 超过阈值即不达标（旧的「秒」口径会把 2600 判成超标得离谱）
    assert tracker._calculate_cwv_pass_rate([{"core_web_vitals": {"lcp": 2600}}]) == 0.0
    # 只采集了 LCP 的样本不应因为其它指标为 0 而被误判
    assert tracker._calculate_cwv_pass_rate([{"core_web_vitals": {"lcp": 1000}}]) == 100.0
    # 旧数据用 FID（阈值 100ms）
    assert tracker._calculate_cwv_pass_rate([{"core_web_vitals": {"fid": 150}}]) == 0.0
    # 完全没有指标的样本不参与判定
    assert tracker._calculate_cwv_pass_rate([{"core_web_vitals": {}}]) == 0.0


def test_oversized_batch_rejected(monkeypatch):
    monkeypatch.setattr(tracker_module, "performance_tracker", PagePerformanceTracker())

    payload = [dict(SAMPLE[0]) for _ in range(health_service.max_vitals_per_request + 1)]
    body = _client().post(PATH, json=payload).json()

    assert body["code"] == 400
    assert "最多" in body["msg"]


def test_unknown_metric_name_rejected(monkeypatch):
    monkeypatch.setattr(tracker_module, "performance_tracker", PagePerformanceTracker())

    resp = _client().post(PATH, json=[{"name": "FID", "value": 12.0}])
    assert resp.status_code == 422  # pydantic 只接受 LCP/INP/CLS/FCP/TTFB


def test_summary_requires_auth():
    assert _client().get(SUMMARY_PATH).status_code == 401
