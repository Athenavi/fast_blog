"""
代码分割优化 API
提供bundle分析、分割建议等功能
"""

from fastapi import APIRouter, Depends, Query

from shared.services.performance.code_splitting_service import code_splitting_optimizer
from api.v1.core.responses import ApiResponse
from src.auth.auth_deps import admin_required

router = APIRouter(prefix="/code-splitting", tags=["code-splitting"])


@router.get("/analysis", summary="获取Bundle分析报告")
async def get_bundle_analysis(current_user=Depends(admin_required)):
    """
    获取完整的Bundle分析报告
    
    Returns:
        Bundle分析数据
    """
    try:
        analysis = code_splitting_optimizer.analyze_bundle()

        return ApiResponse(
            success=True,
            data=analysis
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"分析失败: {str(e)}")


@router.get("/recommendations", summary="获取代码分割建议")
async def get_split_recommendations(
        threshold_kb: int = Query(100, ge=50, le=1000, description="阈值(KB)"),
        current_user=Depends(admin_required)
):
    """
    获取代码分割建议
    
    Args:
        threshold_kb: 建议分割的大小阈值
        
    Returns:
        分割建议列表
    """
    try:
        recommendations = code_splitting_optimizer.generate_split_recommendations(threshold_kb)

        return ApiResponse(
            success=True,
            data={
                'recommendations': recommendations,
                'count': len(recommendations),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取建议失败: {str(e)}")


@router.get("/prefetch-hints", summary="获取预加载提示")
async def get_prefetch_hints(current_user=Depends(admin_required)):
    """
    获取资源预加载提示
    
    Returns:
        预加载资源配置
    """
    try:
        hints = code_splitting_optimizer.generate_prefetch_hints()

        return ApiResponse(
            success=True,
            data={
                'hints': hints,
                'count': len(hints),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取提示失败: {str(e)}")


@router.get("/dynamic-imports", summary="获取动态导入映射")
async def get_dynamic_import_map(current_user=Depends(admin_required)):
    """
    获取动态导入配置建议
    
    Returns:
        动态导入映射
    """
    try:
        import_map = code_splitting_optimizer.generate_dynamic_import_map()

        return ApiResponse(
            success=True,
            data=import_map
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取映射失败: {str(e)}")


@router.get("/report", summary="获取完整优化报告")
async def get_optimization_report(current_user=Depends(admin_required)):
    """
    获取完整的代码分割优化报告
    
    Returns:
        包含所有分析和建议的完整报告
    """
    try:
        report = code_splitting_optimizer.get_optimization_report()

        return ApiResponse(
            success=True,
            data=report
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"生成报告失败: {str(e)}")


@router.post("/analyze", summary="重新分析Bundle")
async def reanalyze_bundle(current_user=Depends(admin_required)):
    """
    重新分析Bundle（清除缓存）
    
    Returns:
        最新的分析结果
    """
    try:
        # 清除缓存
        code_splitting_optimizer.bundle_analysis = {}
        code_splitting_optimizer.split_recommendations = []

        # 重新分析
        analysis = code_splitting_optimizer.analyze_bundle()

        return ApiResponse(
            success=True,
            data=analysis
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"重新分析失败: {str(e)}")


@router.get("/config", summary="获取代码分割配置")
async def get_config(current_user=Depends(admin_required)):
    """
    获取代码分割配置信息
    
    Returns:
        配置信息
    """
    try:
        config = {
            'build_dir': code_splitting_optimizer.build_dir,
            'default_threshold_kb': 100,
            'supported_strategies': [
                'route-based',
                'component-based',
                'library-based',
                'conditional',
            ],
        }

        return ApiResponse(
            success=True,
            data=config
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取配置失败: {str(e)}")
