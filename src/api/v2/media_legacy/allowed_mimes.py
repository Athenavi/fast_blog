"""
共享的允许 MIME 类型列表
用于避免 routes_upload.py 中两条定义不一致的问题
"""

# ===== 允许的 MIME 类型列表（作为 upload_media_file 的默认值）=====
ALLOWED_MIMES_LIST = [
    # ===== 图片 =====
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/svg+xml', 'image/tiff',
    'image/avif', 'image/heic', 'image/heif',
    # ===== 视频 =====
    'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska',
    'video/x-flv', 'video/x-ms-wmv', 'video/x-m4v', 'video/3gpp', 'video/x-ms-asf',
    # ===== 音频 =====
    'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/x-flac', 'audio/aac', 'audio/ogg',
    'audio/mp3', 'audio/x-wav', 'audio/x-m4a', 'audio/x-ms-wma', 'audio/opus', 'audio/webm', 'audio/x-aiff',
    # ===== Office Word =====
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
    'application/vnd.ms-word.document.macroEnabled.12',
    'application/vnd.ms-word.template.macroEnabled.12',
    # ===== Office Excel =====
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
    'application/vnd.ms-excel.sheet.macroEnabled.12',
    'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
    'application/vnd.ms-excel.template.macroEnabled.12',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/x-iwork-numbers-sffnumbers',
    'text/csv',
    # ===== Office PowerPoint =====
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.template',
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
    'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
    'application/vnd.ms-powerpoint.template.macroEnabled.12',
    'application/vnd.ms-powerpoint.slideshow.macroEnabled.12',
    # ===== 文档 & 文本（禁止 text/html / text/xml / application/xml，防止同源 XSS）=====
    'text/plain', 'text/markdown', 'text/csv',
    'application/json',
    # ===== 压缩包 & 归档 =====
    'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
    'application/gzip', 'application/x-tar', 'application/x-bzip2',
    'application/x-xz', 'application/zstd', 'application/x-lzma',
    'application/x-cab', 'application/x-cpio', 'application/x-iso9660-image',
    'application/x-lha', 'application/x-lzh',
    # ===== 电子书 =====
    'application/epub+zip',
    # ===== 邮件 =====
    'message/rfc822', 'application/vnd.ms-outlook',
    # ===== CAD & 设计 =====
    'image/vnd.dwg', 'image/vnd.dxf', 'application/dwf',
    'application/oxps', 'application/vnd.ms-xpsdocument',
    # ===== 3D 模型 =====
    'model/gltf-binary', 'model/gltf+json', 'model/obj', 'model/stl',
    'model/vnd.collada+xml', 'model/vrml', 'model/step',
    'model/step-xml', 'application/step', 'application/x-ifc',
    # ===== OFD & 国产格式 =====
    'application/ofd', 'application/vnd.ofd',
    # ===== Typst =====
    'text/typst', 'application/x-typst',
    # ===== Excalidraw & draw.io =====
    'application/x-excalidraw', 'application/x-drawio',
    # ===== 通用二进制（配合扩展名校验）=====
    'application/octet-stream',
]

# ===== 允许的 MIME 类型集合（作为 _process_single_file 的默认值）=====
ALLOWED_MIMES_SET = set(str(m) for m in ALLOWED_MIMES_LIST)
