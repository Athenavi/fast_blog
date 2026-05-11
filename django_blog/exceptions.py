"""
自定义异常处理器
"""
import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    自定义 DRF 异常处理器
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If response is None, it means it's an unhandled exception
    if response is None:
        # Handle Django HTTP exceptions
        from django.http import Http404
        if isinstance(exc, Http404):
            return Response({
                'success': False,
                'error': '未找到请求的资源'
            }, status=404)

        # Log unexpected exceptions
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

        return Response({
            'success': False,
            'error': '服务器内部错误'
        }, status=500)

    # Customize the response format
    if response is not None:
        # Convert to our standard response format
        data = {
            'success': False,
            'error': response.data.get('detail', str(response.data)) if isinstance(response.data, dict) else str(
                response.data)
        }

        # Add validation errors if present
        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if key != 'detail':
                    data[key] = value

        return Response(data, status=response.status_code)

    return response


def api_response(success=True, data=None, error=None, pagination=None, **kwargs):
    """
    统一的 API 响应格式
    """
    response_data = {
        'success': success,
    }

    if data is not None:
        response_data['data'] = data

    if error is not None:
        response_data['error'] = error

    if pagination:
        response_data['pagination'] = pagination

    # Add any additional kwargs
    for key, value in kwargs.items():
        response_data[key] = value

    return response_data
