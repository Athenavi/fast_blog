"""
备份管理API v1版本
提供数据库备份相关的API接口
"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, FileResponse

from src.auth import jwt_required_dependency as admin_required
from src.extensions import engine  # 使用全局engine
from src.setting import app_config
# 导入数据库备份工具
from src.utils.database.backup import SQLAlchemyBackup

# 创建API路由器
router = APIRouter(tags=["backup-management"])


@router.get('/backup/list')
async def list_backups(
        request: Request,
        current_user_id: int = Depends(admin_required)
):
    """列出所有备份文件"""
    try:
        backup_dir = Path(getattr(app_config, 'BACKUP_DIR', 'backups'))
        backup_files = []

        if backup_dir.exists():
            for filename in backup_dir.iterdir():
                if filename.is_file() and filename.suffix in ['.sql', '.gz', '.zip']:
                    stat = filename.stat()
                    created_at = datetime.fromtimestamp(stat.st_mtime)

                    # 确定备份类型
                    name = filename.name
                    if name.startswith('schema_backup_'):
                        backup_type = 'schema'
                    elif name.startswith('data_backup_'):
                        backup_type = 'data'
                    elif name.startswith('full_backup_'):
                        backup_type = 'all'
                    else:
                        backup_type = 'unknown'

                    backup_files.append({
                        'name': name,
                        'size': stat.st_size,
                        'created_at': created_at.isoformat(),
                        'type': backup_type
                    })

        # 按创建时间倒序排列
        backup_files.sort(key=lambda x: x['created_at'], reverse=True)

        return JSONResponse({
            'success': True,
            'data': {
                'data': backup_files  # 符合前端期望的数据结构
            }
        })
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'获取备份列表失败: {str(e)}'
        }, status_code=500)


@router.post('/backup/create')
async def create_backup(
        request: Request,
        current_user: int = Depends(admin_required),
):
    """创建数据库备份"""
    try:
        data = await request.json()
        backup_type = data.get('backup_type', 'all')

        # 创建备份目录
        backup_dir = Path(getattr(app_config, 'BACKUP_DIR', 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 使用全局engine变量 - 这是正确的数据库引擎
        backup_tool = SQLAlchemyBackup(engine, str(backup_dir))

        if backup_type == 'schema':
            # 备份数据库结构
            filepath = backup_tool.backup_schema(compress=False)
        elif backup_type == 'data':
            # 备份数据库数据
            filepath = backup_tool.backup_data(compress=False)
        else:
            # 完整备份
            result = backup_tool.backup_all(clean_temp_files=False)
            if result:
                filepath = result['full']
            else:
                filepath = None

        if filepath:
            filename = Path(filepath).name
            return JSONResponse({
                'success': True,
                'message': f'数据库{backup_type}备份成功: {filename}',
                'filename': filename
            })
        else:
            return JSONResponse({
                'success': False,
                'message': f'数据库{backup_type}备份失败 - 请检查服务器日志获取详细信息'
            }, status_code=500)

    except Exception as e:
        import traceback
        error_msg = f'备份创建失败: {str(e)}'
        print(error_msg)  # 记录到服务器日志
        print(traceback.format_exc())  # 记录详细堆栈跟踪
        return JSONResponse({
            'success': False,
            'message': error_msg
        }, status_code=500)


@router.post('/backup/delete')
async def delete_backup(
        request: Request,
        current_user_id: int = Depends(admin_required)
):
    """删除备份文件"""
    try:
        data = await request.json()
        filename = data.get('filename')

        if filename and filename.endswith(('.sql', '.sql.gz', '.zip')):
            backup_dir = Path(getattr(app_config, 'BACKUP_DIR', 'backups'))
            filepath = backup_dir / filename

            if filepath.exists() and filepath.parent == backup_dir:
                filepath.unlink()
                return JSONResponse({
                    'success': True,
                    'message': f'备份文件已删除: {filename}'
                })

        return JSONResponse({
            'success': False,
            'message': '文件删除失败'
        })
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'删除备份失败: {str(e)}'
        }, status_code=500)


@router.get('/backup/download/{filename}')
async def download_backup(
        filename: str,
        current_user_id: int = Depends(admin_required)
):
    """下载备份文件"""
    try:
        backup_dir = Path(getattr(app_config, 'BACKUP_DIR', 'backups'))
        filepath = backup_dir / filename

        # 安全检查：确保文件在备份目录内
        if not filepath.exists() or filepath.parent != backup_dir:
            return JSONResponse({'success': False, 'message': '文件不存在'}, status_code=404)

        # 返回文件流，让前端处理下载
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/octet-stream'
        )
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': f'下载备份失败: {str(e)}'
        }, status_code=500)
