"""
安全管理 API
提供安全防护配置、监控和告警功能
"""

from typing import Optional

from fastapi import APIRouter, Depends

from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import  admin_required as admin_required_api as admin_required
from .security_service import (
    waf,
    login_protection,
    file_integrity_monitor,
    security_scanner
)

router = APIRouter(tags=["security-management"])


# ==================== WAF 管理 ====================

@router.get("/waf/stats")
async def get_waf_stats(current_user=Depends(admin_required)):
    """获取WAF统计信息"""
    try:
        stats = waf.get_stats()

        return ApiResponse(
            success=True,
            data={
                'waf': stats,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/waf/events")
async def get_waf_events(
        limit: int = 20,
        current_user=Depends(admin_required)
):
    """获取WAF安全事件"""
    try:
        events = waf.get_recent_events(limit)

        return ApiResponse(
            success=True,
            data={
                'events': events,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 登录保护 ====================

@router.get("/login-protection/stats")
async def get_login_protection_stats(current_user=Depends(admin_required)):
    """获取登录保护统计"""
    try:
        stats = login_protection.get_stats()

        return ApiResponse(
            success=True,
            data={
                'login_protection': stats,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/login-protection/unlock/{identifier}")
async def unlock_account(
        identifier: str,
        current_user=Depends(admin_required)
):
    """手动解锁账户"""
    try:
        if identifier in login_protection.locked_accounts:
            del login_protection.locked_accounts[identifier]
            login_protection.login_attempts[identifier] = []

            return ApiResponse(
                success=True,
                message=f"Account unlocked: {identifier}"
            )
        else:
            return ApiResponse(
                success=False,
                error="Account is not locked"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 文件完整性监控 ====================

@router.get("/file-integrity/check")
async def check_file_integrity(current_user=Depends(admin_required)):
    """检查文件完整性"""
    try:
        result = file_integrity_monitor.check_integrity()

        return ApiResponse(
            success=True,
            data={
                'integrity_check': result,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/file-integrity/snapshot")
async def update_file_snapshot(current_user=Depends(admin_required)):
    """更新文件快照"""
    try:
        file_integrity_monitor.update_snapshot()

        return ApiResponse(
            success=True,
            message="File integrity snapshot updated"
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 安全扫描 ====================

@router.get("/security/scan")
async def run_security_scan(current_user=Depends(admin_required)):
    """执行安全扫描"""
    try:
        result = security_scanner.run_full_scan()

        return ApiResponse(
            success=True,
            data={
                'scan_result': result,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 综合安全仪表板 ====================

@router.get("/security/dashboard")
async def get_security_dashboard(current_user=Depends(admin_required)):
    """获取安全仪表板数据"""
    try:
        dashboard = {
            'waf': waf.get_stats(),
            'login_protection': login_protection.get_stats(),
            'file_integrity': file_integrity_monitor.check_integrity(),
            'recent_threats': waf.get_recent_events(10),
        }

        return ApiResponse(
            success=True,
            data={
                'dashboard': dashboard,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== IP黑名单管理 ====================

@router.get("/security/ip-blacklist")
async def get_ip_blacklist(current_user=Depends(admin_required)):
    """获取IP黑名单"""
    try:
        # 从WAF获取被封禁的IP
        # 这里可以扩展为从数据库读取持久化的黑名单
        blacklisted_ips = []

        return ApiResponse(
            success=True,
            data={
                'blacklist': blacklisted_ips,
                'total': len(blacklisted_ips),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/security/ip-blacklist/add")
async def add_to_ip_blacklist(
        ip_address: str,
        reason: Optional[str] = None,
        current_user=Depends(admin_required)
):
    """添加IP到黑名单"""
    try:
        # 这里应该保存到数据库
        # 目前只是示例

        return ApiResponse(
            success=True,
            message=f"IP {ip_address} added to blacklist",
            data={
                'ip': ip_address,
                'reason': reason or "Manual addition",
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/security/ip-blacklist/remove/{ip_address}")
async def remove_from_ip_blacklist(
        ip_address: str,
        current_user=Depends(admin_required)
):
    """从黑名单移除IP"""
    try:
        # 这里应该从数据库删除
        # 目前只是示例

        return ApiResponse(
            success=True,
            message=f"IP {ip_address} removed from blacklist"
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 安全配置 ====================

@router.get("/security/config")
async def get_security_config(current_user=Depends(admin_required)):
    """获取安全配置"""
    try:
        config = {
            'waf_enabled': True,
            'xss_protection': True,
            'sql_injection_protection': True,
            'rate_limiting': True,
            'login_protection': {
                'max_attempts': login_protection.max_attempts,
                'lockout_duration': login_protection.lockout_duration,
            },
            'file_integrity_monitoring': True,
        }

        return ApiResponse(
            success=True,
            data={
                'config': config,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/security/config/update")
async def update_security_config(
        config: dict,
        current_user=Depends(admin_required)
):
    """更新安全配置"""
    try:
        # 更新登录保护配置
        if 'login_protection' in config:
            lp_config = config['login_protection']
            if 'max_attempts' in lp_config:
                login_protection.max_attempts = lp_config['max_attempts']
            if 'lockout_duration' in lp_config:
                login_protection.lockout_duration = lp_config['lockout_duration']

        return ApiResponse(
            success=True,
            message="Security configuration updated"
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
