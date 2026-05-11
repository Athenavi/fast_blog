"""
页面性能追踪 API

提供前端性能数据的收集和查询功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.performance_tracker import performance_tracker
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.post("/record", summary="记录性能数据", description="记录页面加载性能数据")
async def record_performance(
        url: str = Body(..., description="页面URL"),
        user_agent: str = Body(..., description="用户代理"),
        load_time: float = Body(..., description="页面加载时间（毫秒）"),
        dom_content_loaded: float = Body(..., description="DOM加载完成时间（毫秒）"),
        first_paint: Optional[float] = Body(None, description="首次绘制时间（毫秒）"),
        fcp: Optional[float] = Body(None, description="首次内容绘制（毫秒）"),
        lcp: Optional[float] = Body(None, description="最大内容绘制（毫秒）"),
        fid: Optional[float] = Body(None, description="首次输入延迟（毫秒）"),
        cls: Optional[float] = Body(None, description="累积布局偏移"),
        custom_timings: Optional[dict] = Body(None, description="自定义计时"),
):
    """记录性能数据"""
    performance_metrics = {
        'loadTime': load_time,
        'domContentLoaded': dom_content_loaded,
    }

    if first_paint is not None:
        performance_metrics['firstPaint'] = first_paint

    core_web_vitals = {}
    if fcp is not None:
        core_web_vitals['fcp'] = fcp
    if lcp is not None:
        core_web_vitals['lcp'] = lcp
    if fid is not None:
        core_web_vitals['fid'] = fid
    if cls is not None:
        core_web_vitals['cls'] = cls

    record = performance_tracker.record_performance(
        url=url,
        user_agent=user_agent,
        performance_metrics=performance_metrics,
        core_web_vitals=core_web_vitals if core_web_vitals else None,
        custom_timings=custom_timings,
    )

    return ApiResponse(
        success=True,
        message="Performance data recorded",
        data={'recorded': True}
    )


@router.get("/page-stats", summary="获取页面统计", description="获取指定页面的性能统计")
async def get_page_stats(
        url: str = Query(..., description="页面URL"),
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        current_user=Depends(jwt_required),
):
    """获取页面统计"""
    stats = performance_tracker.get_page_stats(url=url, hours=hours)

    return ApiResponse(
        success=True,
        data=stats
    )


@router.get("/overall", summary="获取整体统计", description="获取所有页面的整体性能统计")
async def get_overall_stats(
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        current_user=Depends(jwt_required),
):
    """获取整体统计"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    stats = performance_tracker.get_overall_stats(hours=hours)

    return ApiResponse(
        success=True,
        data=stats
    )


@router.get("/slowest", summary="获取最慢页面", description="获取加载最慢的页面列表")
async def get_slowest_pages(
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        limit: int = Query(10, ge=1, le=50, description="返回数量"),
        current_user=Depends(jwt_required),
):
    """获取最慢页面"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    pages = performance_tracker.get_slowest_pages(hours=hours, limit=limit)

    return ApiResponse(
        success=True,
        data={
            'pages': pages,
            'count': len(pages),
        }
    )


@router.get("/trends", summary="获取性能趋势", description="获取页面性能趋势数据")
async def get_performance_trends(
        url: str = Query(..., description="页面URL"),
        days: int = Query(7, ge=1, le=30, description="统计天数"),
        current_user=Depends(jwt_required),
):
    """获取性能趋势"""
    trends = performance_tracker.get_performance_trends(url=url, days=days)

    return ApiResponse(
        success=True,
        data={
            'url': url,
            'trends': trends,
        }
    )


@router.get("/examples", summary="使用示例", description="获取性能追踪使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "frontend_integration": {
            'description': '前端集成示例',
            'code': '''
// 在页面加载完成后发送性能数据
window.addEventListener('load', () => {
  setTimeout(() => {
    const perfData = window.performance.timing;
    const paintEntries = performance.getEntriesByType('paint');
    
    // Core Web Vitals
    let fcp = 0, lcp = 0, fid = 0, cls = 0;
    
    // 获取FCP
    const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
    if (fcpEntry) {
      fcp = fcpEntry.startTime;
    }
    
    // 获取LCP（需要PerformanceObserver）
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length > 0) {
        lcp = entries[entries.length - 1].startTime;
      }
    }).observe({ type: 'largest-contentful-paint', buffered: true });
    
    // 获取FID
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length > 0) {
        fid = entries[0].processingStart - entries[0].startTime;
      }
    }).observe({ type: 'first-input', buffered: true });
    
    // 获取CLS
    let clsValue = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
        }
      }
    }).observe({ type: 'layout-shift', buffered: true });
    
    // 发送数据
    fetch('/api/v1/performance/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: window.location.href,
        user_agent: navigator.userAgent,
        load_time: perfData.loadEventEnd - perfData.navigationStart,
        dom_content_loaded: perfData.domContentLoadedEventEnd - perfData.navigationStart,
        first_paint: paintEntries[0]?.startTime || 0,
        fcp: fcp,
        lcp: lcp,
        fid: fid,
        cls: clsValue,
      })
    });
  }, 0);
});
            '''.strip()
        },
        "core_web_vitals": {
            'description': 'Core Web Vitals标准',
            'metrics': {
                'FCP (First Contentful Paint)': {
                    'good': '< 1.8s',
                    'needs_improvement': '1.8s - 3.0s',
                    'poor': '> 3.0s',
                    'description': '首次内容绘制时间',
                },
                'LCP (Largest Contentful Paint)': {
                    'good': '< 2.5s',
                    'needs_improvement': '2.5s - 4.0s',
                    'poor': '> 4.0s',
                    'description': '最大内容绘制时间',
                },
                'FID (First Input Delay)': {
                    'good': '< 100ms',
                    'needs_improvement': '100ms - 300ms',
                    'poor': '> 300ms',
                    'description': '首次输入延迟',
                },
                'CLS (Cumulative Layout Shift)': {
                    'good': '< 0.1',
                    'needs_improvement': '0.1 - 0.25',
                    'poor': '> 0.25',
                    'description': '累积布局偏移',
                },
            }
        },
        "monitoring_dashboard": {
            'description': '监控仪表板',
            'features': [
                '实时显示页面平均加载时间',
                'Core Web Vitals达标率',
                '最慢页面排行榜',
                '性能趋势图表',
                '设备和浏览器分布',
                '性能告警通知',
            ]
        },
        "optimization_tips": {
            'description': '优化建议',
            'tips': [
                '图片优化：使用WebP格式、懒加载、适当尺寸',
                '代码分割：按需加载JavaScript模块',
                '缓存策略：合理设置Cache-Control头',
                'CDN加速：静态资源使用CDN分发',
                '减少重排：避免频繁的DOM操作',
                '压缩资源：启用Gzip/Brotli压缩',
                '预加载关键资源：使用preload和prefetch',
                '优化字体加载：使用font-display: swap',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
