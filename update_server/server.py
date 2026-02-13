#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新检查服务器
作为独立进程运行，提供版本检查服务
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 导入版本管理器（从更新器模块）
try:
    # 直接从updater.py文件导入，避免循环导入
    import sys
    from pathlib import Path
    updater_path = Path(__file__).parent.parent / 'updater' / 'updater.py'
    if updater_path.exists():
        # 动态执行updater.py文件来获取版本管理功能
        updater_globals = {}
        with open(updater_path, 'r', encoding='utf-8') as f:
            exec(f.read(), updater_globals)
        
        version_manager = updater_globals.get('version_manager')
        get_version_summary = updater_globals.get('get_version_summary')
        get_current_version_info = updater_globals.get('get_current_version_info')
        
        if version_manager and get_version_summary and get_current_version_info:
            VERSION_MANAGER_AVAILABLE = True
        else:
            VERSION_MANAGER_AVAILABLE = False
            logging.warning("版本管理器实例未正确加载")
    else:
        VERSION_MANAGER_AVAILABLE = False
        logging.warning("更新器文件不存在")
except Exception as e:
    logging.warning(f"版本管理模块导入失败: {e}")
    VERSION_MANAGER_AVAILABLE = False

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FastBlog Update Checker",
    description="独立的更新检查服务",
    version="1.0.0"
)

class UpdateChecker:
    """更新检查器类"""
    
    def __init__(self):
        self.base_dir = project_root
        self.version_file = self.base_dir / "version.txt"
        self.running = False
        self.start_time = time.time()
        
    def get_local_version_info(self) -> Dict[str, Any]:
        """获取本地版本信息"""
        try:
            # 读取版本文件
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 解析INI格式的版本信息
                version_info = {}
                current_section = None
                
                for line in content.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        version_info[current_section] = {}
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        version_info[current_section][key.strip()] = value.strip()
                
                return {
                    "backend_version": version_info.get("BACKEND", {}).get("version", "0.0.0"),
                    "frontend_version": version_info.get("FRONTEND", {}).get("version", "0.0.0"),
                    "build_time": version_info.get("BACKEND", {}).get("build_time", ""),
                    "framework": version_info.get("BACKEND", {}).get("framework", ""),
                    "status": "success"
                }
            
            # 如果版本文件不存在，返回默认值
            return {
                "backend_version": "0.0.0",
                "frontend_version": "0.0.0", 
                "build_time": "",
                "framework": "FastAPI",
                "status": "default"
            }
            
        except Exception as e:
            logger.error(f"读取版本信息失败: {e}")
            return {
                "backend_version": "0.0.0",
                "frontend_version": "0.0.0",
                "build_time": "",
                "framework": "FastAPI",
                "status": "error",
                "error": str(e)
            }
    
    def get_version_info(self) -> Dict[str, Any]:
        """获取完整的版本信息"""
        try:
            if VERSION_MANAGER_AVAILABLE:
                version_data = get_current_version_info()
                summary = get_version_summary()
                
                return {
                    'success': True,
                    'data': {
                        'versions': version_data,
                        'summary': summary,
                        'timestamp': datetime.now().isoformat()
                    }
                }
            else:
                # 兼容旧版本
                local_info = self.get_local_version_info()
                return {
                    'success': True,
                    'data': {
                        'backend_version': local_info.get('backend_version', 'unknown'),
                        'frontend_version': local_info.get('frontend_version', 'unknown'),
                        'timestamp': datetime.now().isoformat()
                    }
                }
        except Exception as e:
            logger.error(f"获取版本信息失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def get_frontend_version_info(self) -> Dict[str, Any]:
        """获取前端版本信息"""
        try:
            if VERSION_MANAGER_AVAILABLE:
                frontend_info = version_manager.get_frontend_version()
                return {
                    'success': True,
                    'data': {
                        'version': frontend_info.get('version', 'unknown'),
                        'build_time': frontend_info.get('build_time', ''),
                        'framework': frontend_info.get('framework', ''),
                        'node_version': frontend_info.get('node_version', '')
                    }
                }
            else:
                local_info = self.get_local_version_info()
                return {
                    'success': True,
                    'data': {
                        'version': local_info.get('frontend_version', 'unknown')
                    }
                }
        except Exception as e:
            logger.error(f"获取前端版本失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def get_backend_version_info(self) -> Dict[str, Any]:
        """获取后端版本信息"""
        try:
            if VERSION_MANAGER_AVAILABLE:
                backend_info = version_manager.get_backend_version()
                return {
                    'success': True,
                    'data': {
                        'version': backend_info.get('version', 'unknown'),
                        'build_time': backend_info.get('build_time', ''),
                        'framework': backend_info.get('framework', ''),
                        'python_version': backend_info.get('python_version', '')
                    }
                }
            else:
                local_info = self.get_local_version_info()
                return {
                    'success': True,
                    'data': {
                        'version': local_info.get('backend_version', 'unknown')
                    }
                }
        except Exception as e:
            logger.error(f"获取后端版本失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

# 创建更新检查器实例
update_checker = UpdateChecker()

@app.get("/")
async def root():
    """根路径，返回服务器状态"""
    return {
        "message": "FastBlog Update Checker is running",
        "service": "update-checker",
        "uptime": time.time() - update_checker.start_time
    }

@app.get("/api/v1/version")
async def get_version_info():
    """获取版本信息接口"""
    try:
        version_info = update_checker.get_local_version_info()
        return JSONResponse(content=version_info)
    except Exception as e:
        logger.error(f"获取版本信息异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "update-checker",
        "version": "1.0.0",
        "uptime": time.time() - update_checker.start_time
    }

@app.get("/api/v1/config")
async def get_config_info():
    """获取配置信息"""
    return {
        "auto_check_enabled": True,
        "check_interval": 3600,
        "server_info": {
            "name": "FastBlog Update Checker",
            "version": "1.0.0"
        }
    }

# ==================== 版本管理API ====================

@app.get("/api/v1/version/full")
async def get_full_version_info():
    """获取完整的版本信息"""
    result = update_checker.get_version_info()
    if result['success']:
        return JSONResponse(content=result['data'])
    else:
        raise HTTPException(status_code=500, detail=result['error'])

@app.get("/api/v1/version/frontend")
async def get_frontend_version_api():
    """获取前端版本信息"""
    result = update_checker.get_frontend_version_info()
    if result['success']:
        return JSONResponse(content=result['data'])
    else:
        raise HTTPException(status_code=500, detail=result['error'])

@app.get("/api/v1/version/backend")
async def get_backend_version_api():
    """获取后端版本信息"""
    result = update_checker.get_backend_version_info()
    if result['success']:
        return JSONResponse(content=result['data'])
    else:
        raise HTTPException(status_code=500, detail=result['error'])

# ==================== 基础更新状态API ====================

@app.get("/api/v1/update/status")
async def get_update_status():
    """获取基础更新状态信息"""
    try:
        # 获取当前版本信息
        version_info = update_checker.get_version_info()
        if not version_info['success']:
            raise HTTPException(status_code=500, detail=version_info['error'])
        
        return JSONResponse(content={
            'success': True,
            'data': {
                'current_version': version_info['data'].get('versions', {}).get('backend', {}).get('version', 'unknown'),
                'frontend_version': version_info['data'].get('versions', {}).get('frontend', {}).get('version', 'unknown'),
                'is_updating': False,  # 基础状态，实际更新状态由独立更新器管理
                'last_check': datetime.now().isoformat(),
                'update_server': 'running'
            }
        })
    except Exception as e:
        logger.error(f"获取更新状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def setup_signal_handlers():
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭更新检查服务器...")
        update_checker.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows特定信号
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

def main():
    """服务器入口函数"""
    import uvicorn
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/update_checker.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 默认配置
    host = "127.0.0.1"
    port = 8001  # 使用不同的端口避免冲突
    
    # 从环境变量获取配置
    host = os.getenv("UPDATE_CHECKER_HOST", host)
    port = int(os.getenv("UPDATE_CHECKER_PORT", port))
    
    logger.info("=== 更新检查服务器启动 ===")
    logger.info(f"监听地址: http://{host}:{port}")
    logger.info(f"API文档: http://{host}:{port}/docs")
    
    # 设置信号处理器
    setup_signal_handlers()
    update_checker.running = True
    
    try:
        uvicorn.run(
            "update_server.server:app",
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("更新检查服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)
    finally:
        update_checker.running = False
        logger.info("更新检查服务器已停止")

if __name__ == "__main__":
    main()