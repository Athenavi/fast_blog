"""
报表管理 API
提供自定义报表生成和查询功能
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Body

from shared.services.report_generator import report_generator
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import admin_required as admin_required_api

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/content", summary="获取内容表现报表")
async def get_content_report(
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        group_by: str = Query('day', enum=['day', 'week', 'month'], description="分组方式"),
        current_user=Depends(admin_required_api)
):
    """
    获取内容表现报表
    
    仅管理员可访问。
    
    Args:
        days: 统计天数（7-90天）
        group_by: 分组方式
        
    Returns:
        内容报表数据
    """
    try:
        report = report_generator.generate_content_report(days, group_by)

        return ApiResponse(
            success=True,
            data=report
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成报表失败: {str(e)}")


@router.get("/user-activity", summary="获取用户活动报表")
async def get_user_activity_report(
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """
    获取用户活动报表
    
    仅管理员可访问。
    
    Args:
        days: 统计天数（7-90天）
        
    Returns:
        用户活动报表
    """
    try:
        report = report_generator.generate_user_activity_report(days)

        return ApiResponse(
            success=True,
            data=report
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成报表失败: {str(e)}")


@router.get("/traffic", summary="获取流量分析报表")
async def get_traffic_report(
        days: int = Query(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """
    获取流量分析报表
    
    仅管理员可访问。
    
    Args:
        days: 统计天数（7-90天）
        
    Returns:
        流量报表
    """
    try:
        report = report_generator.generate_traffic_report(days)

        return ApiResponse(
            success=True,
            data=report
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成报表失败: {str(e)}")


@router.post("/custom", summary="生成自定义报表")
async def generate_custom_report(
        metrics: List[str] = Body(..., description="要包含的指标列表"),
        days: int = Body(30, ge=7, le=90, description="统计天数"),
        filters: Optional[dict] = Body(None, description="过滤条件"),
        current_user=Depends(admin_required_api)
):
    """
    生成自定义报表
    
    支持选择多个指标组合生成报表。
    
    Args:
        metrics: 指标列表 (content/users/traffic/engagement)
        days: 统计天数（7-90天）
        filters: 过滤条件
        
    Returns:
        自定义报表
    """
    try:
        # 验证指标
        valid_metrics = ['content', 'users', 'traffic', 'engagement']
        invalid = [m for m in metrics if m not in valid_metrics]
        if invalid:
            return ApiResponse(
                success=False,
                error=f"无效的指标: {invalid}. 有效指标: {valid_metrics}"
            )

        report = report_generator.generate_custom_report(metrics, days, filters)

        return ApiResponse(
            success=True,
            data=report
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成报表失败: {str(e)}")


@router.post("/export", summary="导出报表")
async def export_report(
        report_type: str = Body(..., description="报表类型"),
        format: str = Body('json', enum=['json', 'csv'], description="导出格式"),
        days: int = Body(30, ge=7, le=90, description="统计天数"),
        current_user=Depends(admin_required_api)
):
    """
    导出报表为指定格式
    
    Args:
        report_type: 报表类型 (content/user-activity/traffic)
        format: 导出格式 (json/csv)
        days: 统计天数
        
    Returns:
        导出的报表内容
    """
    try:
        # 生成报表
        if report_type == 'content':
            report = report_generator.generate_content_report(days)
        elif report_type == 'user-activity':
            report = report_generator.generate_user_activity_report(days)
        elif report_type == 'traffic':
            report = report_generator.generate_traffic_report(days)
        else:
            return ApiResponse(
                success=False,
                error=f"不支持的报表类型: {report_type}"
            )

        # 导出
        exported = report_generator.export_report(report, format)

        return ApiResponse(
            success=True,
            data={
                'content': exported,
                'format': format,
                'type': report_type,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"导出报表失败: {str(e)}")


@router.get("/templates", summary="获取报表面板")
async def get_report_templates(current_user=Depends(admin_required_api)):
    """
    获取可用的报表面板和预设
    
    仅管理员可访问。
    
    Returns:
        报表面板列表
    """
    templates = [
        {
            'id': 'content-overview',
            'name': '内容概览',
            'description': '文章发布、浏览量、互动数据总览',
            'metrics': ['content'],
            'default_days': 30,
        },
        {
            'id': 'user-growth',
            'name': '用户增长',
            'description': '新用户、活跃用户、留存率分析',
            'metrics': ['users'],
            'default_days': 30,
        },
        {
            'id': 'traffic-analysis',
            'name': '流量分析',
            'description': '访问量、来源渠道、页面表现',
            'metrics': ['traffic'],
            'default_days': 30,
        },
        {
            'id': 'engagement-metrics',
            'name': '参与度分析',
            'description': '用户互动、停留时间、跳出率',
            'metrics': ['engagement'],
            'default_days': 30,
        },
        {
            'id': 'comprehensive',
            'name': '综合报表',
            'description': '包含所有指标的完整报表',
            'metrics': ['content', 'users', 'traffic', 'engagement'],
            'default_days': 30,
        },
    ]

    return ApiResponse(
        success=True,
        data={
            'templates': templates,
            'count': len(templates),
        }
    )
