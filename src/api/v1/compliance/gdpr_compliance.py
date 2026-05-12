"""
GDPR合规 API

提供数据导出、删除、同意管理等功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.gdpr_compliance import gdpr_service
from api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter()


@router.post("/export", summary="导出个人数据", description="导出用户的所有个人数据")
async def export_personal_data(
        include_articles: bool = Body(True, description="是否包含文章"),
        include_comments: bool = Body(True, description="是否包含评论"),
        include_media: bool = Body(True, description="是否包含媒体"),
        include_settings: bool = Body(True, description="是否包含设置"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db),
):
    """导出个人数据"""
    result = await gdpr_service.export_user_data(
        db=db,
        user_id=current_user.id,
        username=getattr(current_user, 'username', 'Unknown'),
        email=getattr(current_user, 'email', ''),
        include_articles=include_articles,
        include_comments=include_comments,
        include_media=include_media,
        include_settings=include_settings,
    )

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=result,
        headers={
            'Content-Disposition': f'attachment; filename="user_data_{current_user.id}.json"',
        }
    )


@router.post("/delete", summary="删除个人数据", description="匿名化或删除用户数据")
async def delete_personal_data(
        hard_delete: bool = Body(False, description="是否硬删除（否则匿名化）"),
        confirm: bool = Body(..., description="确认删除"),
        current_user=Depends(jwt_required),
):
    """删除个人数据"""
    if not confirm:
        return ApiResponse(
            success=False,
            error="Please confirm the deletion by setting confirm=true"
        )

    result = gdpr_service.anonymize_user_data(
        user_id=current_user.id,
        hard_delete=hard_delete
    )

    if result['status'] == 'completed':
        action = 'deleted' if hard_delete else 'anonymized'
        return ApiResponse(
            success=True,
            message=f"User data {action} successfully",
            data=result
        )
    else:
        return ApiResponse(
            success=False,
            error=result.get('error', 'Operation failed')
        )


@router.post("/consent", summary="记录同意", description="记录用户对数据处理的同意")
async def record_consent(
        consent_type: str = Body(..., description="同意类型 (analytics, marketing, cookies)"),
        granted: bool = Body(..., description="是否授予同意"),
        details: Optional[str] = Body(None, description="详细信息"),
        current_user=Depends(jwt_required),
):
    """记录同意"""
    result = gdpr_service.record_consent(
        user_id=current_user.id,
        consent_type=consent_type,
        granted=granted,
        details=details,
    )

    return ApiResponse(
        success=True,
        message="Consent recorded",
        data=result
    )


@router.get("/consent", summary="获取同意记录", description="获取用户的同意记录")
async def get_consents(
        current_user=Depends(jwt_required),
):
    """获取同意记录"""
    consents = gdpr_service.get_user_consents(current_user.id)

    return ApiResponse(
        success=True,
        data=consents
    )


@router.post("/consent/withdraw", summary="撤回同意", description="撤回对数据处理的同意")
async def withdraw_consent(
        consent_type: str = Body(..., description="同意类型"),
        current_user=Depends(jwt_required),
):
    """撤回同意"""
    result = gdpr_service.withdraw_consent(
        user_id=current_user.id,
        consent_type=consent_type,
    )

    return ApiResponse(
        success=True,
        message="Consent withdrawn",
        data=result
    )


@router.get("/privacy-report", summary="隐私报告", description="生成用户隐私报告")
async def get_privacy_report(
        current_user=Depends(jwt_required),
):
    """获取隐私报告"""
    report = gdpr_service.get_privacy_report(current_user.id)

    return ApiResponse(
        success=True,
        data=report
    )


@router.get("/rights", summary="用户权利", description="获取GDPR用户权利说明")
async def get_user_rights():
    """获取用户权利说明"""
    rights = {
        'right_of_access': {
            'article': 'Article 15',
            'title': '访问权',
            'description': '用户有权访问其个人数据，并获得有关数据处理的信息',
            'how_to_exercise': '使用"导出个人数据"功能',
        },
        'right_to_rectification': {
            'article': 'Article 16',
            'title': '更正权',
            'description': '用户有权更正不准确的个人数据',
            'how_to_exercise': '在个人资料页面编辑信息',
        },
        'right_to_erasure': {
            'article': 'Article 17',
            'title': '删除权（被遗忘权）',
            'description': '用户有权要求删除其个人数据',
            'how_to_exercise': '使用"删除个人数据"功能',
        },
        'right_to_restriction': {
            'article': 'Article 18',
            'title': '限制处理权',
            'description': '用户有权限制对其个人数据的处理',
            'how_to_exercise': '联系数据保护官',
        },
        'right_to_data_portability': {
            'article': 'Article 20',
            'title': '数据可携带权',
            'description': '用户有权以结构化、常用和机器可读的格式接收其个人数据',
            'how_to_exercise': '使用"导出个人数据"功能（JSON格式）',
        },
        'right_to_object': {
            'article': 'Article 21',
            'title': '反对权',
            'description': '用户有权反对基于合法利益的数据处理',
            'how_to_exercise': '撤回相关同意或使用"撤回同意"功能',
        },
        'rights_related_to_automated_decision_making': {
            'article': 'Article 22',
            'title': '自动化决策相关权利',
            'description': '用户有权不受仅基于自动化处理的决策约束',
            'how_to_exercise': '联系数据保护官',
        },
    }

    return ApiResponse(
        success=True,
        data=rights
    )


@router.get("/compliance-checklist", summary="合规检查清单", description="获取GDPR合规检查清单")
async def get_compliance_checklist():
    """获取合规检查清单"""
    checklist = {
        'data_protection': {
            'title': '数据保护',
            'items': [
                {'task': '实施数据加密', 'status': 'recommended'},
                {'task': '定期备份数据', 'status': 'required'},
                {'task': '实施访问控制', 'status': 'required'},
                {'task': '记录数据处理活动', 'status': 'required'},
            ]
        },
        'user_rights': {
            'title': '用户权利',
            'items': [
                {'task': '提供数据导出功能', 'status': 'completed'},
                {'task': '提供数据删除功能', 'status': 'completed'},
                {'task': '提供同意管理', 'status': 'completed'},
                {'task': '响应DSR请求（30天内）', 'status': 'required'},
            ]
        },
        'consent_management': {
            'title': '同意管理',
            'items': [
                {'task': '获取明确同意', 'status': 'required'},
                {'task': '记录同意历史', 'status': 'completed'},
                {'task': '允许撤回同意', 'status': 'completed'},
                {'task': '区分不同处理目的的同意', 'status': 'recommended'},
            ]
        },
        'transparency': {
            'title': '透明度',
            'items': [
                {'task': '提供隐私政策', 'status': 'required'},
                {'task': '说明数据收集目的', 'status': 'required'},
                {'task': '披露第三方共享', 'status': 'required'},
                {'task': '提供数据保留期限', 'status': 'required'},
            ]
        },
        'security': {
            'title': '安全性',
            'items': [
                {'task': '实施HTTPS', 'status': 'required'},
                {'task': '定期安全审计', 'status': 'recommended'},
                {'task': '员工培训', 'status': 'recommended'},
                {'task': '数据泄露响应计划', 'status': 'required'},
            ]
        },
    }

    return ApiResponse(
        success=True,
        data=checklist
    )


@router.get("/examples", summary="使用示例", description="获取GDPR合规使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "data_export": {
            'description': '数据导出流程',
            'steps': [
                '1. 用户请求导出个人数据',
                '2. 系统收集所有相关数据',
                '3. 生成JSON格式的导出文件',
                '4. 提供下载链接',
                '5. 记录导出请求',
            ],
            'example': '''
POST /api/v1/gdpr/export
{
  "include_articles": true,
  "include_comments": true,
  "include_media": true,
  "include_settings": true
}

# 返回JSON文件供下载
            '''.strip()
        },
        "data_deletion": {
            'description': '数据删除流程',
            'steps': [
                '1. 用户请求删除数据',
                '2. 系统确认用户身份',
                '3. 执行匿名化或删除',
                '4. 记录删除操作',
                '5. 通知相关方（如需要）',
            ],
            'example': '''
POST /api/v1/gdpr/delete
{
  "hard_delete": false,
  "confirm": true
}

# hard_delete=false: 匿名化处理
# hard_delete=true: 完全删除
            '''.strip()
        },
        "consent_banner": {
            'description': '同意横幅示例',
            'code_example': '''
// React组件示例
function ConsentBanner() {
  const [consents, setConsents] = useState({
    analytics: false,
    marketing: false,
    cookies: true,
  });
  
  const saveConsents = async () => {
    for (const [type, granted] of Object.entries(consents)) {
      await fetch('/api/v1/gdpr/consent', {
        method: 'POST',
        body: JSON.stringify({
          consent_type: type,
          granted: granted,
        })
      });
    }
  };
  
  return (
    <div className="consent-banner">
      <h3>Cookie和隐私设置</h3>
      
      <label>
        <input
          type="checkbox"
          checked={consents.analytics}
          onChange={e => setConsents({...consents, analytics: e.target.checked})}
        />
        分析Cookie（帮助我们改进网站）
      </label>
      
      <label>
        <input
          type="checkbox"
          checked={consents.marketing}
          onChange={e => setConsents({...consents, marketing: e.target.checked})}
        />
        营销Cookie（个性化广告）
      </label>
      
      <button onClick={saveConsents}>保存设置</button>
    </div>
  );
}
            '''.strip()
        },
        "best_practices": {
            'description': '最佳实践',
            'practices': [
                '默认隐私保护（Privacy by Default）',
                '设计阶段考虑隐私（Privacy by Design）',
                '最小化数据收集',
                '明确告知数据处理目的',
                '获得明确和具体的同意',
                '提供简单的同意撤回方式',
                '定期审查和更新隐私政策',
                '培训员工了解GDPR要求',
                '建立数据泄露响应流程',
                '任命数据保护官（如需要）',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
