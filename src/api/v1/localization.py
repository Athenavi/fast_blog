"""
区域化设置 API
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from shared.services.localization import localization_service

router = APIRouter(prefix="/localization", tags=["localization"])


@router.get("/format-date")
async def format_date(
        timestamp: float = Query(..., description="Unix 时间戳"),
        locale: str = Query('zh-CN', description="语言代码"),
        format_type: str = Query('date', enum=['date', 'datetime', 'time'], description="格式类型")
):
    """
    格式化日期
    
    Args:
        timestamp: Unix 时间戳
        locale: 语言代码
        format_type: 格式类型
        
    Returns:
        格式化后的日期字符串
    """
    try:
        dt = datetime.fromtimestamp(timestamp)
        formatted = localization_service.format_date(dt, locale, format_type)

        return {
            'success': True,
            'data': {
                'original': dt.isoformat(),
                'formatted': formatted,
                'locale': locale,
                'format_type': format_type,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/format-number")
async def format_number(
        number: float = Query(..., description="数字"),
        locale: str = Query('zh-CN', description="语言代码"),
        decimals: int = Query(2, ge=0, le=10, description="小数位数")
):
    """
    格式化数字
    
    Args:
        number: 数字
        locale: 语言代码
        decimals: 小数位数
        
    Returns:
        格式化后的数字字符串
    """
    try:
        formatted = localization_service.format_number(number, locale, decimals)

        return {
            'success': True,
            'data': {
                'original': number,
                'formatted': formatted,
                'locale': locale,
                'decimals': decimals,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/format-currency")
async def format_currency(
        amount: float = Query(..., description="金额"),
        currency: str = Query('CNY', description="货币代码"),
        locale: str = Query('zh-CN', description="语言代码")
):
    """
    格式化货币
    
    Args:
        amount: 金额
        currency: 货币代码
        locale: 语言代码
        
    Returns:
        格式化后的货币字符串
    """
    try:
        formatted = localization_service.format_currency(amount, currency, locale)

        return {
            'success': True,
            'data': {
                'original': amount,
                'formatted': formatted,
                'currency': currency,
                'locale': locale,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert-timezone")
async def convert_timezone(
        timestamp: float = Query(..., description="Unix 时间戳"),
        from_tz: str = Query('UTC', description="源时区"),
        to_tz: Optional[str] = Query(None, description="目标时区"),
        locale: str = Query('zh-CN', description="语言代码")
):
    """
    时区转换
    
    Args:
        timestamp: Unix 时间戳
        from_tz: 源时区
        to_tz: 目标时区
        locale: 语言代码
        
    Returns:
        转换后的时间
    """
    try:
        dt = datetime.fromtimestamp(timestamp)
        converted = localization_service.convert_timezone(dt, from_tz, to_tz, locale)

        return {
            'success': True,
            'data': {
                'original': dt.isoformat(),
                'converted': converted.isoformat(),
                'from_tz': from_tz,
                'to_tz': to_tz or localization_service.get_locale_config(locale)['timezone'],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/{locale}")
async def get_locale_config(locale: str):
    """
    获取区域化配置
    
    Args:
        locale: 语言代码
        
    Returns:
        配置信息
    """
    try:
        config = localization_service.get_locale_config(locale)

        return {
            'success': True,
            'data': {
                'locale': locale,
                'config': config,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-locales")
async def get_supported_locales():
    """
    获取支持的语言列表
    
    Returns:
        语言代码列表
    """
    try:
        locales = localization_service.get_supported_locales()

        return {
            'success': True,
            'data': {
                'locales': locales,
                'count': len(locales),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
