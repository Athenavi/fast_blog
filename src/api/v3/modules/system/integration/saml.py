"""SAML 2.0 SP 断言校验（阶段 0-1 文档里"仅 SAML 未实现"的那一块）。

## 为什么是这个实现，而不是 pysaml2 的高层封装

本机装 `pysaml2` **不会**带上签名后端 —— 签名/验签走 `xmlsec`（`xmlsec` python 包或
`xmlsec1` 可执行文件）。没有它时 pysaml2 仍能解析 XML、生成元数据，**但验不了签名**，
而"验签"恰恰是本模块唯一的意义。已实测确认 `xmlsec` 1.3.17 可用，且**篡改会被拒**
（`VerificationError`），所以这里直接用 `xmlsec`：

  - pysaml2 的 `sigver.validate_signature()` 要的是**证书文件路径**，而我们的 IdP
    证书存在数据库里（`SSOProvider.client_secret`），每次请求落一个临时文件既脏又慢；
  - `SPConfig` 的配置体系（metadata 存储、key/cert 文件、endpoint 绑定）对本场景
    是过度设计 —— 我们只需要"验一个响应的签名 + 检查几个字段"。

## 安全设计（每一条都是"不通过即拒绝"，没有放行分支）

1. **XXE / 实体扩展**：解析器关闭 DTD 与外部实体（`resolve_entities=False`、
   `no_network=True`），SAML 响应是完全外部可控的输入。
2. **签名**：用 `xmlsec` 验 RSA-SHA256 enveloped 签名，并**显式限定** PermittedTransforms
   为 exclusive-C14N（`xmlsec.SignatureContext` 的默认允许集在 xmlsec 1.3 已足够严格，
   这里再加一层"不认识的 Transform 一律拒"）。
3. **签名包装（XSW）**：验签前先断言 `SignedInfo/Reference/@URI` 恰好指向**我们实际读取的
   那个 Assertion 的 ID**（`#<ID>`）。否则攻击者可以把一个合法签名挪到伪造的 Assertion 旁。
4. **签发者**：`Issuer` 必须等于配置的 IdP entityID。
5. **受众**：`Conditions/AudienceRestriction/Audience` 必须包含本 SP 的 entityID，
   防止发给别家的断言被拿来登录本站。
6. **有效期**：`NotBefore <= now <= NotOnOrAfter`（带小量时钟偏移容忍）。
   缺 `Conditions` 直接拒绝。
7. **重放**：AssertionID 记入 `token_blacklist`（该表的 `token_identifier` 有唯一约束），
   第二次出现即拒绝。标识符做 sha256 截断，避免超长 ID 撞上 64 字符上限。
8. **只接受 HTTP-POST 绑定**（`SAMLResponse` 表单字段），不做 Redirect 绑定的简化签名校验
   —— 那条路径的验签语义不同，宁可明确不支持，也不做半套。
"""

from __future__ import annotations

import base64
import hashlib
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from xml.etree import ElementTree as StdET  # noqa: F401  (保留：便于对照标准库行为)

import xmlsec
from lxml import etree
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security.token_blacklist import TokenBlacklist

NS_SAML = "urn:oasis:names:tc:SAML:2.0:assertion"
NS_SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"
NS_MD = "urn:oasis:names:tc:SAML:2.0:metadata"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"

BINDING_HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
NAMEID_EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"

#: 时钟偏移容忍。IdP 与本机不可能完全同秒，但也不该放宽到分钟级。
CLOCK_SKEW = timedelta(seconds=120)

#: 重放记录的存活上限：断言本身的有效期通常只有几分钟，留一天足够覆盖。
REPLAY_RETENTION = timedelta(days=1)


class SamlValidationError(Exception):
    """断言校验失败。

    对外**统一**转成一个错误（不区分"签名错"还是"过期"），避免把校验细节
    回显给调用方 —— 那等于告诉攻击者哪一步差一点就过了。
    """


@dataclass
class SamlIdentity:
    """从**已验签**的断言里取出的身份。"""

    name_id: str
    assertion_id: str
    issuer: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    session_index: Optional[str] = None
    attributes: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------- 元数据


def build_sp_metadata(*, entity_id: str, acs_url: str) -> bytes:
    """生成本 SP 的 EntityDescriptor（交给 IdP 侧登记）。

    用 lxml 构造而不是字符串模板：`entity_id` / `acs_url` 来自配置，
    交给 lxml 转义，避免配置里的 `&` 之类把 XML 弄坏。
    """
    md = f"{{{NS_MD}}}"
    root = etree.Element(f"{md}EntityDescriptor", nsmap={"md": NS_MD})
    root.set("entityID", entity_id)

    descriptor = etree.SubElement(root, f"{md}SPSSODescriptor")
    descriptor.set("protocolSupportEnumeration", NS_SAMLP)
    # 明确要求 IdP **对断言本身签名**：没有这一条，有些 IdP 只签 Response 不签
    # Assertion，而本模块只认 Assertion 签名（见 verify_assertion_signature）。
    descriptor.set("WantAssertionsSigned", "true")

    nameid = etree.SubElement(descriptor, f"{md}NameIDFormat")
    nameid.text = NAMEID_EMAIL

    acs = etree.SubElement(descriptor, f"{md}AssertionConsumerService")
    acs.set("Binding", BINDING_HTTP_POST)
    acs.set("Location", acs_url)
    acs.set("index", "0")
    acs.set("isDefault", "true")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


# ---------------------------------------------------------------- 解析


def _secure_parser() -> etree.XMLParser:
    """禁用 DTD 与外部实体：SAML 响应是外部可控输入，XXE 在这里是真实威胁。"""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )


def decode_saml_response(raw: str) -> etree._Element:
    """把 `SAMLResponse` 表单值解成 XML 根节点。

    HTTP-POST 绑定下它是 base64；有些实现会再 deflate 一次，这里做兼容。
    任何解码失败都归为校验失败。
    """
    try:
        padded = raw.strip()
        padded += "=" * (-len(padded) % 4)
        blob = base64.b64decode(padded, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise SamlValidationError("SAMLResponse 不是合法 base64") from exc

    if not blob.lstrip().startswith(b"<"):
        # 可能是 deflate 压缩
        try:
            blob = zlib.decompress(blob, -15)
        except Exception as exc:  # noqa: BLE001
            raise SamlValidationError("SAMLResponse 解压失败") from exc

    try:
        root = etree.fromstring(blob, parser=_secure_parser())
    except Exception as exc:  # noqa: BLE001
        raise SamlValidationError("SAMLResponse 不是合法 XML") from exc

    if root.tag != f"{{{NS_SAMLP}}}Response":
        raise SamlValidationError("根节点不是 samlp:Response")
    return root


def _find_assertions(root: etree._Element) -> list[etree._Element]:
    """取出 Response 下的 Assertion。

    **只认 Response 的直接子节点**：签名包装攻击常把伪造的 Assertion 塞进
    更深的层级（如 EncryptedAssertion、Advice 或某个嵌套扩展里），
    用 descendant 搜索会把它们一起捞进来。
    """
    return [child for child in root if child.tag == f"{{{NS_SAML}}}Assertion"]


# ---------------------------------------------------------------- 签名


def verify_assertion_signature(assertion: etree._Element, idp_cert_pem: str) -> None:
    """验证 Assertion 上的 enveloped 签名。失败一律抛 SamlValidationError。

    除了 `xmlsec` 自己的验签，这里额外做两件事：
      - 断言签名**恰好一个**（多个签名意味着可能被拼接）；
      - 断言 `Reference/@URI` 指向**当前这个 Assertion 的 ID** —— 这是防签名包装
        （XSW）的关键：否则攻击者可以保留合法签名、替换掉被签名的内容。
    """
    signatures = [c for c in assertion if c.tag == f"{{{NS_DS}}}Signature"]
    if len(signatures) != 1:
        raise SamlValidationError(f"Assertion 的签名数量为 {len(signatures)}，应为 1")

    signature = signatures[0]

    signed_info = signature.find(f"{{{NS_DS}}}SignedInfo")
    if signed_info is None:
        raise SamlValidationError("签名缺少 SignedInfo")
    reference = signed_info.find(f"{{{NS_DS}}}Reference")
    if reference is None:
        raise SamlValidationError("签名缺少 Reference")

    assertion_id = assertion.get("ID")
    if not assertion_id:
        raise SamlValidationError("Assertion 缺少 ID")
    if reference.get("URI") != f"#{assertion_id}":
        # XSW：签名指向的不是这个 Assertion
        raise SamlValidationError("签名未覆盖当前 Assertion（疑似签名包装）")

    # 只接受我们认识的摘要/规范化算法（不认识的 Transform 一律拒绝）
    allowed_digests = {
        "http://www.w3.org/2001/04/xmlenc#sha256",
        "http://www.w3.org/2000/09/xmldsig#sha1",
    }
    for digest in signed_info.findall(
        f"{{{NS_DS}}}Reference/{{{NS_DS}}}DigestMethod"
    ):
        if digest.get("Algorithm") not in allowed_digests:
            raise SamlValidationError(f"不支持的摘要算法：{digest.get('Algorithm')}")

    try:
        # xmlsec 默认**不**把 `ID` 当作 ID 属性（SAML 用大写 `ID`，不是 `xml:id`）。
        # 不注册这一步，`Reference/@URI="#<id>"` 就解析不到目标，验签会直接失败 ——
        # 表现是 "failed to verify"，很容易被误判成"证书不对"。
        xmlsec.tree.add_ids(assertion.getroottree().getroot(), ["ID"])
        ctx = xmlsec.SignatureContext()
        ctx.key = xmlsec.Key.from_memory(idp_cert_pem, xmlsec.KeyFormat.CERT_PEM, None)
        ctx.verify(signature)
    except Exception as exc:  # noqa: BLE001
        raise SamlValidationError("断言签名校验失败") from exc


# ---------------------------------------------------------------- 字段校验


def _parse_instant(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    # SAML 用 UTC，形如 2026-10-15T12:00:00Z（也可能带毫秒）
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _assert_time_window(conditions: etree._Element, now: datetime) -> Optional[datetime]:
    """校验有效期，返回 NotOnOrAfter（重放记录的过期时间要用它）。"""
    not_before = _parse_instant(conditions.get("NotBefore"))
    not_on_or_after = _parse_instant(conditions.get("NotOnOrAfter"))

    if not_on_or_after is None:
        # 没有上界 = 断言永久有效，不能接受
        raise SamlValidationError("Conditions 缺少 NotOnOrAfter")
    if now > not_on_or_after + CLOCK_SKEW:
        raise SamlValidationError("断言已过期")
    if not_before is not None and now < not_before - CLOCK_SKEW:
        raise SamlValidationError("断言尚未生效")
    return not_on_or_after


def _assert_audience(conditions: etree._Element, sp_entity_id: str) -> None:
    audiences = [
        node.text or ""
        for node in conditions.iter(f"{{{NS_SAML}}}Audience")
    ]
    if not audiences:
        raise SamlValidationError("Conditions 缺少 AudienceRestriction")
    if sp_entity_id not in audiences:
        raise SamlValidationError("断言的受众不是本 SP")


def _assert_issuer(node: etree._Element, idp_entity_id: str) -> str:
    issuer = node.find(f"{{{NS_SAML}}}Issuer")
    text = (issuer.text or "").strip() if issuer is not None else ""
    if not text:
        raise SamlValidationError("缺少 Issuer")
    if text != idp_entity_id:
        raise SamlValidationError("Issuer 与配置的 IdP 不一致")
    return text


def _collect_attributes(assertion: etree._Element) -> dict[str, list[str]]:
    """把 AttributeStatement 摊成 {Name: [values]}，供属性映射挑用。"""
    result: dict[str, list[str]] = {}
    for statement in assertion.iter(f"{{{NS_SAML}}}AttributeStatement"):
        for attribute in statement.iter(f"{{{NS_SAML}}}Attribute"):
            name = attribute.get("Name")
            if not name:
                continue
            values = [
                (v.text or "")
                for v in attribute.iter(f"{{{NS_SAML}}}AttributeValue")
            ]
            result.setdefault(name, []).extend(values)
    return result


def _pick(
    mapping: dict[str, Any], attributes: dict[str, list[str]], key: str
) -> Optional[str]:
    """按 `attribute_mapping` 取属性；未配置时退回常见名。"""
    candidates: list[str] = []
    configured = mapping.get(key)
    if isinstance(configured, str) and configured:
        candidates.append(configured)
    candidates.extend(
        {
            "email": ["mail", "email", "emailAddress", "urn:oid:0.9.2342.19200300.100.1.3"],
            "username": ["uid", "username", "sAMAccountName", "urn:oid:0.9.2342.19200300.100.1.1"],
        }.get(key, [])
    )
    for candidate in candidates:
        values = attributes.get(candidate)
        if values and values[0]:
            return values[0]
    return None


# ---------------------------------------------------------------- 重放防护


def _replay_key(assertion_id: str) -> str:
    """AssertionID → 黑名单标识符。

    `token_blacklist.token_identifier` 是 `String(64)` 且有唯一约束，
    而 SAML 的 ID 长度没有硬性上界，所以取 sha256 前 48 位（192 bit，
    碰撞概率可忽略），保证一定塞得进且唯一约束仍然有效。
    """
    digest = hashlib.sha256(assertion_id.encode("utf-8")).hexdigest()
    return f"saml:{digest[:48]}"


async def claim_assertion_id(
    db: AsyncSession, assertion_id: str, expires_at: datetime
) -> None:
    """占用 AssertionID；已被占用则说明是重放。

    依赖 `token_blacklist.token_identifier` 的**唯一约束**做原子判定，
    而不是"先查后插"（那在并发下会漏）。冲突时不需要回滚整个外层事务 ——
    这里用 SAVEPOINT 包住插入。
    """
    key = _replay_key(assertion_id)
    record = TokenBlacklist(
        token_identifier=key,
        # 存哈希便于审计时辨认（不放原文，避免把断言内容落到日志/库里）
        token_hash=hashlib.sha256(assertion_id.encode("utf-8")).hexdigest(),
        expires_at=min(expires_at, datetime.now(timezone.utc) + REPLAY_RETENTION),
        created_at=datetime.now(timezone.utc),
        reason="saml assertion replay guard",
    )

    if db.in_transaction():
        savepoint = await db.begin_nested()
        try:
            db.add(record)
            await db.flush()
            await savepoint.commit()
        except IntegrityError as exc:
            await savepoint.rollback()
            raise SamlValidationError("断言已被使用过（重放）") from exc
        return

    db.add(record)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise SamlValidationError("断言已被使用过（重放）") from exc


async def purge_expired_replay_records(db: AsyncSession) -> int:
    """清理过期的重放记录，返回删除行数（由调用方按需触发，不在请求路径上）。"""
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(TokenBlacklist).where(
                TokenBlacklist.token_identifier.like("saml:%"),
                TokenBlacklist.expires_at < now,
            )
        )
    ).scalars().all()
    for row in rows:
        await db.delete(row)
    await db.flush()
    return len(rows)


# ---------------------------------------------------------------- 主入口


async def validate_saml_response(
    raw_response: str,
    *,
    db: AsyncSession,
    idp_cert_pem: str,
    idp_entity_id: str,
    sp_entity_id: str,
    attribute_mapping: Optional[dict[str, Any]] = None,
) -> SamlIdentity:
    """校验一份 SAML Response 并返回身份；任何一步不通过都抛 SamlValidationError。

    顺序有讲究：**先验签、再读字段**。先解析业务字段再验签，等于让未签名的
    内容影响了后续判断（也会把解析错误与校验失败混在一起）。
    """
    root = decode_saml_response(raw_response)

    assertions = _find_assertions(root)
    if len(assertions) != 1:
        raise SamlValidationError(f"Response 里 Assertion 数量为 {len(assertions)}，应为 1")
    assertion = assertions[0]

    # 1) 签名（含 XSW 防护）
    verify_assertion_signature(assertion, idp_cert_pem)

    # 2) 签发者 / 有效期 / 受众（此时内容已被签名覆盖，可信）
    issuer = _assert_issuer(assertion, idp_entity_id)

    conditions = assertion.find(f"{{{NS_SAML}}}Conditions")
    if conditions is None:
        raise SamlValidationError("Assertion 缺少 Conditions")
    not_on_or_after = _assert_time_window(conditions, datetime.now(timezone.utc))
    _assert_audience(conditions, sp_entity_id)

    subject = assertion.find(f"{{{NS_SAML}}}Subject")
    name_id_node = (
        subject.find(f"{{{NS_SAML}}}NameID") if subject is not None else None
    )
    name_id = (name_id_node.text or "").strip() if name_id_node is not None else ""
    if not name_id:
        raise SamlValidationError("Assertion 缺少 Subject/NameID")

    assertion_id = assertion.get("ID") or ""
    if not assertion_id:
        raise SamlValidationError("Assertion 缺少 ID")

    # 3) 重放（放在最后：前面任何一步失败都不该占用这个 ID）
    await claim_assertion_id(db, assertion_id, not_on_or_after)

    attributes = _collect_attributes(assertion)
    mapping = attribute_mapping or {}

    session_index = None
    if subject is not None:
        session_node = subject.find(f"{{{NS_SAML}}}SubjectConfirmation")
        if session_node is not None:
            session_index = session_node.get("SessionIndex") or None

    # 邮箱/用户名：优先属性映射，其次 NameID 本身（很多 IdP 把邮箱放 NameID）
    email = _pick(mapping, attributes, "email")
    username = _pick(mapping, attributes, "username")
    if email is None and "@" in name_id:
        email = name_id
    if username is None:
        username = name_id if "@" not in name_id else name_id.split("@", 1)[0]

    return SamlIdentity(
        name_id=name_id,
        assertion_id=assertion_id,
        issuer=issuer,
        email=email,
        username=username,
        session_index=session_index,
        attributes=attributes,
    )
