# -*- coding: utf-8 -*-
"""阶段 0：SAML 2.0 SP 断言校验（`src/api/v3/modules/system/integration/saml.py`）。

这份测试的重点不是"happy path 能过"，而是**每一种攻击/异常都必须被拒**。
所以除了正常断言，其余用例都是"把某个条件弄坏"：

  - 签名：内容被篡改、用错误的私钥签、签名指向另一个 ID（签名包装 XSW）
  - 时间：已过期、尚未生效、压根没有 `NotOnOrAfter`（= 永久有效，不可接受）
  - 归属性：受众不是本 SP（防"发给别家的断言被拿来登录本站"）、Issuer 与配置不符
  - 结构：没有 Conditions、没有 Subject、Response 里有两个 Assertion
  - 重放：同一个 AssertionID 第二次提交

**用的是真的 XMLDSig，不是桩**：证书由 `cryptography` 现场自签，签名与验签都走
`xmlsec`（与生产同一条代码路径）。否则"签名校验"这四个字就没有验证价值。

**不连真实数据库**：重放防护靠 `token_blacklist` 的唯一约束，这里用假会话喂
`IntegrityError` 来验证"第二次被拒"，不依赖 PG（CI 上也一样跑）。
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import xmlsec
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from sqlalchemy.exc import IntegrityError

from src.api.v3.modules.system.integration.saml import (
    NS_SAML,
    NS_SAMLP,
    SamlValidationError,
    build_sp_metadata,
    validate_saml_response,
)

IDP_ENTITY = "https://idp.example.com/metadata"
SP_ENTITY = "https://blog.example.com/saml"
NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------- 夹具


def _make_keypair(cn: str) -> tuple[bytes, bytes]:
    """自签证书：返回 (私钥 PEM, 证书 PEM)。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW - timedelta(days=1))
        .not_valid_after(NOW + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return priv, cert.public_bytes(serialization.Encoding.PEM)


IDP_KEY, IDP_CERT = _make_keypair("idp.example.com")
#: 攻击者自己的密钥：用来验证"用别的私钥签的断言一定过不了"
ATTACKER_KEY, _ = _make_keypair("attacker.example.com")


def _instant(offset_seconds: int) -> str:
    """相对**当前时刻**算，而不是模块导入时刻。

    全量测试里这个文件可能在几分钟后才被执行；若用导入时固定的 `NOW`，
    ±30s 这类边界用例会因为"实际时间已经过去几分钟"而失败 —— 这正是它第一次
    在全量跑里挂掉、单独跑却通过的原因（典型的时间脆弱性）。
    """
    base = datetime.now(timezone.utc)
    return (base + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sign(assertion: etree._Element, priv_pem: bytes, reference_id: str | None = None) -> None:
    """给 Assertion 加 enveloped 签名（exclusive C14N + RSA-SHA256），与生产同路径。"""
    sig = xmlsec.template.create(
        assertion, xmlsec.Transform.EXCL_C14N, xmlsec.Transform.RSA_SHA256
    )
    issuer = assertion.find(f"{{{NS_SAML}}}Issuer")
    if issuer is not None:
        # SAML 规范要求 Signature 紧跟 Issuer
        issuer.addnext(sig)
    else:
        assertion.insert(0, sig)

    uri = f"#{reference_id if reference_id is not None else assertion.get('ID')}"
    ref = xmlsec.template.add_reference(sig, xmlsec.Transform.SHA256, uri=uri)
    xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
    xmlsec.template.add_transform(ref, xmlsec.Transform.EXCL_C14N)
    xmlsec.template.ensure_key_info(sig)

    # 必须显式注册 `ID` 为 ID 属性：SAML 用大写 `ID` 而非 `xml:id`，
    # 不注册时 `#<id>` 形式的引用解析不到，签名会以 "failed to sign" 报错。
    xmlsec.tree.add_ids(assertion.getroottree().getroot(), ["ID"])

    ctx = xmlsec.SignatureContext()
    ctx.key = xmlsec.Key.from_memory(priv_pem, xmlsec.KeyFormat.PEM, None)
    ctx.sign(sig)


def _build_response(**over: object) -> str:
    """构造一个 SAML Response 并返回 base64。各参数用于把某个条件弄坏。

    注意**先构造完整内容、最后签名** —— 签名覆盖整个 Assertion，
    签名后再改内容就等于制造了一次篡改。
    """
    opts = {
        "assertion_id": "_assertion_1",
        "idp_entity": IDP_ENTITY,
        "sp_entity": SP_ENTITY,
        "name_id": "alice@example.com",
        "not_before": -60,
        "not_on_or_after": 300,
        "with_conditions": True,
        "with_subject": True,
        "with_not_on_or_after": True,
        "attributes": {"mail": ["alice@example.com"], "uid": ["alice"]},
        "sign": True,
        "sign_key": IDP_KEY,
        "reference_id": None,
        "tamper": False,
        "duplicate_assertion": False,
        "raw": None,
    }
    opts.update(over)

    if opts["raw"] is not None:
        return str(opts["raw"])

    resp = etree.Element(
        f"{{{NS_SAMLP}}}Response", nsmap={"samlp": NS_SAMLP, "saml": NS_SAML}
    )
    resp.set("ID", "_response_1")
    resp.set("Version", "2.0")
    resp.set("IssueInstant", _instant(0))
    etree.SubElement(resp, f"{{{NS_SAML}}}Issuer").text = str(opts["idp_entity"])
    status = etree.SubElement(resp, f"{{{NS_SAMLP}}}Status")
    etree.SubElement(status, f"{{{NS_SAMLP}}}StatusCode").set(
        "Value", "urn:oasis:names:tc:SAML:2.0:status:Success"
    )

    def _add_assertion(assertion_id: str) -> etree._Element:
        assertion = etree.SubElement(resp, f"{{{NS_SAML}}}Assertion")
        assertion.set("ID", assertion_id)
        assertion.set("Version", "2.0")
        assertion.set("IssueInstant", _instant(0))
        etree.SubElement(assertion, f"{{{NS_SAML}}}Issuer").text = str(opts["idp_entity"])

        if opts["with_subject"]:
            subject = etree.SubElement(assertion, f"{{{NS_SAML}}}Subject")
            etree.SubElement(subject, f"{{{NS_SAML}}}NameID").text = str(opts["name_id"])

        if opts["with_conditions"]:
            cond = etree.SubElement(assertion, f"{{{NS_SAML}}}Conditions")
            cond.set("NotBefore", _instant(int(opts["not_before"])))  # type: ignore[arg-type]
            if opts["with_not_on_or_after"]:
                cond.set("NotOnOrAfter", _instant(int(opts["not_on_or_after"])))  # type: ignore[arg-type]
            aud = etree.SubElement(cond, f"{{{NS_SAML}}}AudienceRestriction")
            etree.SubElement(aud, f"{{{NS_SAML}}}Audience").text = str(opts["sp_entity"])

        attrs = opts["attributes"] or {}
        for name, values in dict(attrs).items():  # type: ignore[union-attr]
            stmt = etree.SubElement(assertion, f"{{{NS_SAML}}}AttributeStatement")
            node = etree.SubElement(stmt, f"{{{NS_SAML}}}Attribute")
            node.set("Name", str(name))
            for value in values:
                etree.SubElement(node, f"{{{NS_SAML}}}AttributeValue").text = str(value)
        return assertion

    assertion = _add_assertion(str(opts["assertion_id"]))
    if opts["duplicate_assertion"]:
        _add_assertion("_assertion_2")

    if opts["sign"]:
        _sign(assertion, opts["sign_key"], reference_id=opts["reference_id"])  # type: ignore[arg-type]

    if opts["tamper"]:
        # 签名之后改内容 —— 这正是"篡改"
        subject = assertion.find(f"{{{NS_SAML}}}Subject/{{{NS_SAML}}}NameID")
        if subject is not None:
            subject.text = "attacker@example.com"

    return base64.b64encode(etree.tostring(resp)).decode()


def _db(flush_error: Exception | None = None) -> AsyncMock:
    """假会话。`in_transaction()` 是同步方法，显式给 False 走简单插入分支。"""
    db = AsyncMock()
    db.in_transaction = MagicMock(return_value=False)
    if flush_error is not None:
        db.flush = AsyncMock(side_effect=flush_error)
    return db


async def _validate(response: str, db: AsyncMock | None = None, **over):
    return await validate_saml_response(
        response,
        db=db or _db(),
        idp_cert_pem=IDP_CERT.decode(),
        idp_entity_id=IDP_ENTITY,
        sp_entity_id=SP_ENTITY,
        **over,
    )


def _conflict() -> IntegrityError:
    """模拟 `token_identifier` 唯一约束冲突。"""
    return IntegrityError("INSERT INTO token_blacklist", {}, Exception("duplicate key"))


# ---------------------------------------------------------------- 正常路径


class TestHappyPath:
    pytestmark = pytest.mark.asyncio

    async def test_valid_response_returns_identity(self):
        # 属性值**刻意与 NameID 不同**：否则即使属性收集坏掉，"回退到 NameID"
        # 也会给出同样结果，这条用例就验证不到属性映射真的生效。
        response = _build_response(
            name_id="alice@example.com",
            attributes={"mail": ["alice-contact@example.com"], "uid": ["alice-id"]},
        )
        identity = await _validate(response)
        assert identity.name_id == "alice@example.com"
        assert identity.assertion_id == "_assertion_1"
        assert identity.issuer == IDP_ENTITY
        # 来自 AttributeStatement 的 mail / uid，而不是 NameID 派生
        assert identity.email == "alice-contact@example.com"
        assert identity.username == "alice-id"

    async def test_attribute_mapping_overrides_defaults(self):
        response = _build_response(
            attributes={"emailAddress": ["bob@example.com"], "sAMAccountName": ["bob"]}
        )
        identity = await _validate(
            response, attribute_mapping={"email": "emailAddress", "username": "sAMAccountName"}
        )
        assert identity.email == "bob@example.com"
        assert identity.username == "bob"

    async def test_login_happens_once_per_assertion(self):
        db = _db()
        await _validate(_build_response(), db=db)
        # 重放记录确实写了一次（不是"没做检查"）
        assert db.add.called
        assert db.flush.await_count >= 1


# ---------------------------------------------------------------- 签名


class TestSignature:
    pytestmark = pytest.mark.asyncio

    async def test_tampered_content_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(tamper=True))

    async def test_signed_by_wrong_key_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(sign_key=ATTACKER_KEY))

    async def test_unsigned_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(sign=False))

    async def test_signature_wrapping_is_rejected(self):
        """签名有效、但它覆盖的不是我们读取的那个 Assertion（XSW），必须拒。

        构造贴近真实攻击：引用目标是**真实存在**的节点（Response 自身），
        所以签名能成功产生；只是它与待校验的 Assertion 不是同一个。
        引用一个不存在的 ID 属于另一种情况（签名阶段就崩），测不到这个分支。
        """
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(reference_id="_response_1"))


# ---------------------------------------------------------------- 时间


class TestTimeWindow:
    pytestmark = pytest.mark.asyncio

    async def test_expired_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(not_before=-600, not_on_or_after=-300))

    async def test_not_yet_valid_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(not_before=300, not_on_or_after=600))

    async def test_small_clock_skew_is_tolerated(self):
        """边界内的小偏移应放行，否则 IdP 与本机差几秒就登不上。"""
        identity = await _validate(_build_response(not_before=-30, not_on_or_after=30))
        assert identity.name_id == "alice@example.com"

    async def test_missing_not_on_or_after_is_rejected(self):
        """没有上界 = 断言永久有效，不能接受。"""
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(with_not_on_or_after=False))

    async def test_missing_conditions_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(with_conditions=False))


# ---------------------------------------------------------------- 归属性


class TestAttribution:
    pytestmark = pytest.mark.asyncio

    async def test_wrong_audience_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(sp_entity="https://other-sp.example.com"))

    async def test_wrong_issuer_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(idp_entity="https://evil-idp.example.com"))


# ---------------------------------------------------------------- 结构


class TestStructure:
    pytestmark = pytest.mark.asyncio

    async def test_missing_subject_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(with_subject=False))

    async def test_two_assertions_are_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(duplicate_assertion=True))

    async def test_bad_base64_is_rejected(self):
        with pytest.raises(SamlValidationError):
            await _validate("这显然不是 base64 的 XML")

    async def test_non_response_root_is_rejected(self):
        junk = base64.b64encode(b"<root><a/></root>").decode()
        with pytest.raises(SamlValidationError):
            await _validate(junk)

    async def test_xxe_is_not_expanded(self):
        """外部实体不该被解析（XXE）。即便解析成功，也绝不该出现文件内容。"""
        payload = (
            b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/hostname">]>'
            b'<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">'
            b"<x>&xxe;</x></samlp:Response>"
        )
        junk = base64.b64encode(payload).decode()
        try:
            await _validate(junk)
        except SamlValidationError:
            return  # 直接拒绝，正是期望
        raise AssertionError("含 DTD 的响应应当被拒绝")


# ---------------------------------------------------------------- 重放


class TestReplay:
    pytestmark = pytest.mark.asyncio

    async def test_replay_is_rejected(self):
        """第二次提交同一断言：唯一约束冲突 → 判定为重放。"""
        with pytest.raises(SamlValidationError):
            await _validate(_build_response(), db=_db(flush_error=_conflict()))

    async def test_replay_guard_uses_hashed_key(self):
        """标识符是 sha256 截断（`saml:` 前缀），不会因超长 ID 撞上 64 字符列宽。"""
        db = _db()
        await _validate(_build_response(assertion_id="_" + "x" * 200), db=db)
        record = db.add.call_args.args[0]
        assert record.token_identifier.startswith("saml:")
        assert len(record.token_identifier) <= 64


# ---------------------------------------------------------------- 元数据


class TestMetadata:
    def test_metadata_declares_sp_and_acs(self):
        xml = build_sp_metadata(entity_id=SP_ENTITY, acs_url=f"{SP_ENTITY}/acs")
        root = etree.fromstring(xml)
        assert root.get("entityID") == SP_ENTITY

        ns = {"md": "urn:oasis:names:tc:SAML:2.0:metadata"}
        descriptor = root.find("md:SPSSODescriptor", ns)
        assert descriptor is not None
        # 要求 IdP 对断言签名 —— 与本模块只认 Assertion 签名的实现一致
        assert descriptor.get("WantAssertionsSigned") == "true"

        acs = descriptor.find("md:AssertionConsumerService", ns)
        assert acs is not None
        assert acs.get("Location") == f"{SP_ENTITY}/acs"
        assert acs.get("Binding") == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"

    def test_metadata_escapes_special_chars(self):
        """entity_id 里有 `&` 时不能把 XML 弄坏（用 lxml 构造而不是字符串拼接）。"""
        xml = build_sp_metadata(entity_id="https://a.example.com/?x=1&y=2", acs_url="https://a/acs")
        root = etree.fromstring(xml)  # 能解析即说明转义正确
        assert root.get("entityID") == "https://a.example.com/?x=1&y=2"
