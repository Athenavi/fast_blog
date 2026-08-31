def get_client_ip(req):
    if 'X-Forwarded-For' in req.headers:
        ip = req.headers['X-Forwarded-For'].split(',')[0].strip()
    elif 'X-Real-IP' in req.headers:
        ip = req.headers['X-Real-IP'].strip()
    else:
        # For FastAPI, use req.client.host instead of req.remote_addr
        ip = getattr(req.client, 'host', '127.0.0.1') if hasattr(req, 'client') and req.client else '127.0.0.1'

    # 验证 IP 格式有效性
    if not _is_valid_ip(ip):
        return '127.0.0.1'

    return ip


def _is_valid_ip(ip: str) -> bool:
    """验证 IP 地址格式是否有效"""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def anonymize_ip_address(ip):
    # 将 IP 地址分割成四个部分
    parts = ip.split('.')
    if len(parts) == 4:
        # 隐藏最后两个部分
        masked_ip = f"{parts[0]}.{parts[1]}.***.***"
        return masked_ip
    return ip
