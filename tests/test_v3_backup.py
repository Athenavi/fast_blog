"""ops/backup（备份统一 / 云存储）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import base64
import hashlib
import hmac
import os
import pytest
import shared.config.settings  # noqa: F401 - 触发 load_dotenv，让 DB_* 进入 os.environ
import shutil
import subprocess
import tarfile
import threading
import uuid
from datetime import datetime
from fastapi import FastAPI
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from shared.services.system.backup_service import BackupService
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ops.backup import cloud

# ============================================================ 来自 test_v3_backup.py（11 项）
BASE = "/api/v3/ops/backup"
PG_TOOLS = ("pg_dump", "pg_restore", "createdb", "dropdb", "psql")


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def _make_service(tmp_path: Path) -> BackupService:
    return BackupService(backup_dir=str(tmp_path / "backups"))


def _write_files_backup(service: BackupService, tmp_path: Path, name: str = "files_backup_t.tar.gz") -> str:
    """造一个**真实**的文件备份（tar.gz + 元数据）供校验用"""
    path = os.path.join(service.files_backup_dir, name)
    payload = tmp_path / "site.txt"
    payload.write_text("hello backup", encoding="utf-8")
    with tarfile.open(path, "w:gz") as archive:
        archive.add(payload, arcname="media/site.txt")
    service._save_metadata(
        path,
        {
            'type': 'files',
            'filename': os.path.basename(path),
            'path': path,
            'size': os.path.getsize(path),
            'created_at': datetime.now().isoformat(),
            'checksum': service._sha256_file(path),
            'status': 'completed',
        },
    )
    return path


# ---------------------------------------------------------------- 1. 路由与鉴权


# ---------------------------------------------------------------- 2. 路径收口
def test_resolve_backup_path_keeps_inside_and_rejects_outside(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    inside = _write_files_backup(service, tmp_path)

    assert service.resolve_backup_path(inside) == os.path.realpath(inside)
    assert service.resolve_backup_path(os.path.basename(inside)) == os.path.realpath(inside)
    # 越界：项目配置、系统文件、相对上跳
    assert service.resolve_backup_path("config/models.yaml") is None
    assert service.resolve_backup_path("../../etc/passwd") is None
    assert service.resolve_backup_path(str(Path(tmp_path).parent / "outside.tar.gz")) is None


@pytest.mark.asyncio
async def test_verify_rejects_path_outside_backup_dir(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    result = await service.verify_backup("config/models.yaml")
    assert result["valid"] is False
    assert result["checks"][0]["name"] == "path_within_backup_dir"


@pytest.mark.asyncio
async def test_verify_missing_backup(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    missing = os.path.join(service.files_backup_dir, "nope.tar.gz")
    result = await service.verify_backup(missing)
    assert result["valid"] is False
    assert result["checks"][0]["name"] == "exists"


# ---------------------------------------------------------------- 3. 校验（真读文件）
@pytest.mark.asyncio
async def test_verify_valid_files_backup(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    path = _write_files_backup(service, tmp_path)

    result = await service.verify_backup(path)

    assert result["valid"] is True, result
    names = {check["name"]: check for check in result["checks"]}
    assert names["exists"]["passed"] is True
    assert names["metadata"]["passed"] is True
    assert names["checksum"]["passed"] is True
    assert names["archive"]["passed"] is True
    assert result["checksum"]["matched"] is True
    assert result["size"] == os.path.getsize(path)


@pytest.mark.asyncio
async def test_verify_detects_tampered_backup(tmp_path: Path) -> None:
    """文件被追加内容 → sha256 与创建时不一致，必须报出来"""
    service = _make_service(tmp_path)
    path = _write_files_backup(service, tmp_path)
    with open(path, "ab") as handle:
        handle.write(b"tampered")

    result = await service.verify_backup(path)

    assert result["valid"] is False
    checksum = next(check for check in result["checks"] if check["name"] == "checksum")
    assert checksum["passed"] is False
    assert "不符" in checksum["detail"]


@pytest.mark.asyncio
async def test_verify_detects_corrupt_database_backup(tmp_path: Path) -> None:
    """数据库备份内容不是合法 gzip → 校验必须失败（不是"看着有文件就算过"）"""
    service = _make_service(tmp_path)
    path = os.path.join(service.database_backup_dir, "db_backup_broken.sql.gz")
    Path(path).write_bytes(b"this is not gzip at all")
    service._save_metadata(
        path,
        {
            'type': 'database',
            'filename': os.path.basename(path),
            'path': path,
            'checksum': service._sha256_file(path),
            'created_at': datetime.now().isoformat(),
        },
    )

    result = await service.verify_backup(path)

    assert result["valid"] is False
    failed = [check["name"] for check in result["checks"] if not check["passed"]]
    assert "pg_restore_list" in failed


@pytest.mark.asyncio
async def test_verify_full_backup_directory(tmp_path: Path) -> None:
    """全量备份是目录：校验目录内容 + 目录内文件非空"""
    service = _make_service(tmp_path)
    directory = os.path.join(service.full_backup_dir, "full_backup_t")
    os.makedirs(directory, exist_ok=True)
    Path(directory, "metadata.json").write_text('{"type": "full"}', encoding="utf-8")
    Path(directory, "db_backup_t.sql.gz").write_bytes(b"x")

    result = await service.verify_backup(directory)

    assert result["valid"] is True, result
    assert result["kind"] == "full"
    assert any(check["name"] == "content" for check in result["checks"])


# ---------------------------------------------------------------- 4. 增量 + 链式恢复（真实库）
def _pg_env() -> dict:
    env = os.environ.copy()
    password = os.getenv("DB_PASSWORD", "")
    if password:
        env["PGPASSWORD"] = password
    return env


def _db_args() -> list:
    return [
        "-h", os.getenv("DB_HOST", "localhost"),
        "-p", os.getenv("DB_PORT", "5432"),
        "-U", os.getenv("DB_USER", "postgres"),
    ]


def _sql(database: str, statement: str) -> str:
    result = subprocess.run(
        ["psql", *_db_args(), "-d", database, "-t", "-A", "-v", "ON_ERROR_STOP=1", "-c", statement],
        capture_output=True,
        text=True,
        env=_pg_env(),
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(f"psql 失败：{result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture()
def temp_database():
    """建一个临时 PostgreSQL 库（用完删掉）；工具或权限不可用则跳过"""
    if not all(shutil.which(tool) for tool in PG_TOOLS):
        pytest.skip("本机缺少 pg 客户端工具（pg_dump / pg_restore / createdb / dropdb / psql）")

    name = f"fb_backup_test_{uuid.uuid4().hex[:8]}"
    create = subprocess.run(
        ["createdb", *_db_args(), name], capture_output=True, text=True, env=_pg_env(), timeout=60
    )
    if create.returncode != 0:
        pytest.skip(f"无法创建临时数据库（权限或连接问题）：{create.stderr.strip()[:200]}")
    try:
        yield name
    finally:
        subprocess.run(
            ["dropdb", "--if-exists", *_db_args(), name],
            capture_output=True,
            text=True,
            env=_pg_env(),
            timeout=60,
        )


@pytest.mark.asyncio
async def test_incremental_backup_and_chain_restore_roundtrip(
    temp_database: str, monkeypatch, tmp_path: Path
) -> None:
    """真实往返：基准全量 → 只改一张表 → 增量只含它 → 改脏后按链恢复回正确状态"""
    monkeypatch.setenv("DB_NAME", temp_database)
    service = _make_service(tmp_path)

    _sql(temp_database, "CREATE TABLE t1(id int PRIMARY KEY, v text);")
    _sql(temp_database, "CREATE TABLE t2(id int PRIMARY KEY, v text);")
    _sql(temp_database, "INSERT INTO t1 VALUES (1, 'base'); INSERT INTO t2 VALUES (1, 'base');")

    base = await service.backup_database(backup_type="full")
    assert base["success"] is True, base
    fingerprints = base["metadata"]["table_fingerprints"]
    assert set(fingerprints) >= {"t1", "t2"}, fingerprints

    # 只改 t1 → 增量只应包含 t1
    _sql(temp_database, "UPDATE t1 SET v = 'after-change' WHERE id = 1;")
    incremental = await service.create_incremental_backup()
    assert incremental["success"] is True, incremental
    assert incremental["changed_tables"] == ["t1"], incremental

    # 增量必须能被列出（否则前端看不到、也无法触发链式恢复）
    listed = service.list_backups(backup_type="incremental")
    assert [item["filename"] for item in listed] == [os.path.basename(incremental["backup_path"])]
    assert service.list_backups(backup_type="differential") == []

    # 链：基准在前、增量在后
    chain = service.build_restore_chain(incremental["backup_path"])
    assert [item["type"] for item in chain] == ["database", "incremental"], chain

    # 再把两个表都改脏，然后按链恢复：t1 回到增量时的值，t2 回到基准时的值
    _sql(temp_database, "UPDATE t1 SET v = 'dirty'; UPDATE t2 SET v = 'dirty';")
    restored = await service.restore_backup_chain(incremental["backup_path"])
    assert restored["success"] is True, restored

    assert _sql(temp_database, "SELECT v FROM t1 WHERE id = 1;") == "after-change"
    assert _sql(temp_database, "SELECT v FROM t2 WHERE id = 1;") == "base"


@pytest.mark.asyncio
async def test_incremental_without_changes_is_skipped(
    temp_database: str, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DB_NAME", temp_database)
    service = _make_service(tmp_path)
    _sql(temp_database, "CREATE TABLE t1(id int PRIMARY KEY, v text);")
    _sql(temp_database, "INSERT INTO t1 VALUES (1, 'base');")
    assert (await service.backup_database())["success"] is True

    result = await service.create_incremental_backup()

    assert result["success"] is True
    assert result.get("skipped") is True
    assert result["changed_tables"] == []


@pytest.mark.asyncio
async def test_incremental_requires_base_with_fingerprints(tmp_path: Path) -> None:
    """没有基准（或基准没记表指纹）时如实报错，不假装备份成功"""
    service = _make_service(tmp_path)
    result = await service.create_incremental_backup()

    assert result["success"] is False
    assert "基准" in result["error"]


@pytest.mark.asyncio
async def test_chain_restore_rejects_unknown_backup(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    result = await service.restore_backup_chain("backups/incremental/nope.dump")

    assert result["success"] is False
    assert "恢复链" in result["error"]


# ============================================================ 来自 test_v3_backup_cloud.py（12 项）
BASE__backup_cloud = "/api/v3/ops/backup"
BUCKET = "my-bucket"
KEY = "backups/db_backup_test.sql.gz"
SECRET = "oss-secret-key"


# ---------------------------------------------------------------- 本地端点
class _Recorder:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.status = 200


def _handler_factory(recorder: _Recorder):
    class _Handler(BaseHTTPRequestHandler):
        def _record(self) -> None:
            length = int(self.headers.get('Content-Length') or 0)
            recorder.requests.append(
                {
                    'method': self.command,
                    'path': self.path,
                    'headers': {key: value for key, value in self.headers.items()},
                    'body': self.rfile.read(length) if length else b'',
                }
            )

        def _respond(self) -> None:
            self.send_response(recorder.status)
            self.send_header('ETag', '"d41d8cd98f00b204e9800998ecf8427e"')
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_PUT(self) -> None:  # noqa: N802 - http.server 约定
            self._record()
            self._respond()

        def do_POST(self) -> None:  # noqa: N802
            self._record()
            self._respond()

        def log_message(self, *args) -> None:
            return

    return _Handler


@pytest.fixture()
def cloud_endpoint():
    """本地 S3 / OSS 端点：返回 ``(endpoint, recorder)``"""
    recorder = _Recorder()
    server = HTTPServer(("127.0.0.1", 0), _handler_factory(recorder))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", recorder
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture()
def backup_file(tmp_path: Path) -> str:
    path = tmp_path / "db_backup_test.sql.gz"
    path.write_bytes(b"backup-content-bytes")
    return str(path)


def _app__backup_cloud() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ---------------------------------------------------------------- 1. 路由与鉴权


# ---------------------------------------------------------------- 2. OSS 签名（纯函数）
def test_oss_string_to_sign_shape() -> None:
    date = "Sun, 21 Sep 2026 12:00:00 GMT"
    sts = cloud.oss_string_to_sign(
        method="PUT",
        content_type="application/octet-stream",
        date=date,
        resource=f"/{BUCKET}/{KEY}",
    )
    assert sts == f"PUT\n\napplication/octet-stream\n{date}\n/{BUCKET}/{KEY}"


def test_oss_authorization_matches_documented_formula() -> None:
    """Authorization = ``OSS {AK}:{Base64(HMAC-SHA1(secret, StringToSign))}``"""
    date = "Sun, 21 Sep 2026 12:00:00 GMT"
    authorization = cloud.oss_authorization(
        access_key_id="ak-test",
        secret=SECRET,
        method="PUT",
        content_type="application/octet-stream",
        date=date,
        resource=f"/{BUCKET}/{KEY}",
    )
    expected_sts = f"PUT\n\napplication/octet-stream\n{date}\n/{BUCKET}/{KEY}"
    expected = base64.b64encode(
        hmac.new(SECRET.encode(), expected_sts.encode(), hashlib.sha1).digest()
    ).decode()
    assert authorization == f"OSS ak-test:{expected}"


def test_build_object_key_normalises_prefix() -> None:
    assert cloud.build_object_key("backups", "a.sql.gz") == "backups/a.sql.gz"
    assert cloud.build_object_key("/backups/", "a.sql.gz") == "backups/a.sql.gz"
    # 未配置 prefix 时用默认的 backups 前缀
    assert cloud.build_object_key("", "a.sql.gz") == "backups/a.sql.gz"


def test_mask_never_returns_secret() -> None:
    masked = cloud.mask({"provider": "oss", "bucket": BUCKET, "secret_encrypted": "cipher"})
    assert "secret_encrypted" not in masked
    assert masked["has_secret"] is True


def test_secret_is_encrypted_at_rest() -> None:
    """密钥必须加密存储：密文与明文不同、能解回，且脱敏后不回传"""
    from src.api.v3.core.secret_box import decrypt_secret, encrypt_secret

    cipher = encrypt_secret(SECRET)
    assert cipher != SECRET
    assert SECRET not in cipher
    assert decrypt_secret(cipher) == SECRET
    assert "secret_encrypted" not in cloud.mask({"secret_encrypted": cipher})


# ---------------------------------------------------------------- 3. 真实上传
@pytest.mark.asyncio
async def test_oss_upload_request_is_signed(cloud_endpoint, backup_file: str) -> None:
    endpoint, recorder = cloud_endpoint
    result = await cloud.upload_backup(
        provider="oss",
        config={
            "provider": "oss",
            "bucket": BUCKET,
            "region": "oss-cn-hangzhou",
            "endpoint": endpoint,
            "prefix": "backups",
            "access_key_id": "ak-test",
        },
        secret=SECRET,
        path=backup_file,
        key=KEY,
    )

    assert result["location"] == f"oss://{BUCKET}/{KEY}"
    sent = recorder.requests[0]
    assert sent['method'] == 'PUT'
    assert sent['path'] == f"/{BUCKET}/{KEY}"
    assert sent['body'] == Path(backup_file).read_bytes()

    headers = {key.lower(): value for key, value in sent['headers'].items()}
    assert headers['content-type'] == 'application/octet-stream'
    # 服务端会这样校验：用收到的 Date 与资源路径独立复算签名
    expected_sts = "\n".join(
        ["PUT", "", headers['content-type'], headers['date'], f"/{BUCKET}/{KEY}"]
    )
    expected = base64.b64encode(
        hmac.new(SECRET.encode(), expected_sts.encode(), hashlib.sha1).digest()
    ).decode()
    assert headers['authorization'] == f"OSS ak-test:{expected}"


@pytest.mark.asyncio
async def test_oss_upload_surfaces_remote_error(cloud_endpoint, backup_file: str) -> None:
    """云端拒绝时把状态码与原因带出来（不假装成功）"""
    endpoint, recorder = cloud_endpoint
    recorder.status = 403

    with pytest.raises(BadRequestError) as exc:
        await cloud.upload_backup(
            provider="oss",
            config={"bucket": BUCKET, "endpoint": endpoint, "access_key_id": "ak"},
            secret=SECRET,
            path=backup_file,
            key=KEY,
        )
    assert "403" in str(exc.value)


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


@pytest.mark.asyncio
async def test_s3_upload_request_is_signed(cloud_endpoint, backup_file: str) -> None:
    """S3（httpx + SigV4）：PUT 到 path-style 路径，签名可被独立复算"""
    endpoint, recorder = cloud_endpoint
    result = await cloud.upload_backup(
        provider="s3",
        config={
            "provider": "s3",
            "bucket": BUCKET,
            "region": "us-east-1",
            "endpoint": endpoint,
            "prefix": "backups",
            "access_key_id": "AKIDTEST",
        },
        secret="s3-secret",
        path=backup_file,
        key=KEY,
    )

    assert result["location"] == f"s3://{BUCKET}/{KEY}"
    sent = recorder.requests[0]
    assert sent['method'] == 'PUT'
    assert sent['path'] == f"/{BUCKET}/{KEY}"
    assert sent['body'] == Path(backup_file).read_bytes()

    headers = {key.lower(): value for key, value in sent['headers'].items()}
    authorization = headers['authorization']
    assert authorization.startswith('AWS4-HMAC-SHA256 Credential=AKIDTEST/')
    assert 'SignedHeaders=host;x-amz-content-sha256;x-amz-date' in authorization
    # payload 哈希必须与实际发出的 body 一致（服务端会这么校验）
    assert headers['x-amz-content-sha256'] == hashlib.sha256(sent['body']).hexdigest()

    # 独立复算：用收到的请求重建规范请求与 StringToSign
    scope = authorization.split('Credential=')[1].split(',')[0].split('/', 1)[1]
    signature = authorization.split('Signature=')[1]
    canonical_headers = (
        f"host:{headers['host']}\n"
        f"x-amz-content-sha256:{headers['x-amz-content-sha256']}\n"
        f"x-amz-date:{headers['x-amz-date']}\n"
    )
    canonical_request = "\n".join(
        [
            'PUT',
            f"/{BUCKET}/{KEY}",
            '',
            canonical_headers,
            'host;x-amz-content-sha256;x-amz-date',
            hashlib.sha256(sent['body']).hexdigest(),
        ]
    )
    string_to_sign = "\n".join(
        [
            'AWS4-HMAC-SHA256',
            headers['x-amz-date'],
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    date_stamp, region, service = scope.split('/')[:3]
    signing_key = _hmac(_hmac(_hmac(_hmac(b'AWS4s3-secret', date_stamp), region), service), 'aws4_request')
    expected = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    assert signature == expected


@pytest.mark.asyncio
async def test_s3_upload_surfaces_remote_error(cloud_endpoint, backup_file: str) -> None:
    """云端拒绝时带出状态码与响应体（不假装成功）"""
    endpoint, recorder = cloud_endpoint
    recorder.status = 403

    with pytest.raises(BadRequestError) as exc:
        await cloud.upload_backup(
            provider="s3",
            config={
                "provider": "s3",
                "bucket": BUCKET,
                "endpoint": endpoint,
                "access_key_id": "AK",
            },
            secret="s3-secret",
            path=backup_file,
            key=KEY,
        )
    assert "403" in str(exc.value)


# ---------------------------------------------------------------- 4. 拒绝路径
@pytest.mark.asyncio
async def test_upload_rejects_missing_configuration(backup_file: str) -> None:
    with pytest.raises(BadRequestError) as exc:
        await cloud.upload_backup(
            provider="s3",
            config={"provider": "s3", "bucket": BUCKET},
            secret="s",
            path=backup_file,
            key=KEY,
        )
    assert "access_key_id" in str(exc.value)

    with pytest.raises(BadRequestError) as exc2:
        await cloud.upload_backup(
            provider="s3",
            config={"provider": "s3", "access_key_id": "ak"},
            secret="s",
            path=backup_file,
            key=KEY,
        )
    assert "bucket" in str(exc2.value)

    with pytest.raises(BadRequestError) as exc3:
        await cloud.upload_backup(
            provider="oss",
            config={"provider": "oss", "bucket": BUCKET, "access_key_id": "ak"},
            secret="",
            path=backup_file,
            key=KEY,
        )
    assert "密钥" in str(exc3.value)


@pytest.mark.asyncio
async def test_upload_rejects_unknown_provider(backup_file: str) -> None:
    with pytest.raises(BadRequestError) as exc:
        await cloud.upload_backup(
            provider="gcs", config={"provider": "gcs"}, secret="s", path=backup_file, key=KEY
        )
    assert "不支持的云存储提供商" in str(exc.value)


# ---------------------------------------------------------------- 5. 上传留痕
@pytest.mark.asyncio
async def test_record_cloud_upload_writes_metadata(tmp_path: Path) -> None:
    """上传结果会写回备份元数据（列表里能看到"上传到哪"）"""
    from shared.services.system.backup_service import BackupService

    service = BackupService(backup_dir=str(tmp_path / "backups"))
    path = os.path.join(service.files_backup_dir, "files_backup_t.tar.gz")
    Path(path).write_bytes(b"x")
    service._save_metadata(
        path,
        {"type": "files", "filename": os.path.basename(path), "path": path,
         "created_at": datetime.now().isoformat()},
    )

    ok = service.record_cloud_upload(
        path, {"provider": "s3", "bucket": BUCKET, "key": KEY, "location": f"s3://{BUCKET}/{KEY}"}
    )

    assert ok is True
    stored = service._load_metadata(path)
    assert stored["cloud"]["bucket"] == BUCKET
    assert stored["cloud"]["key"] == KEY
    assert stored["cloud"]["uploaded_at"]
