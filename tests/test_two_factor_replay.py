"""TOTP 重放防护回归测试

`_claim_totp_step` 在 Redis 可用时走 ``SADD`` 原子占用，不可用时降级为进程内集合。
两种路径的**对外语义一致**：同一个时间步只能被占用一次。这里用随机 step，
避免测试之间以及与真实登录流程互相干扰（Redis 侧键 300s 后自然过期）。
"""
import random

import pytest

from shared.services.security.two_factor_service import TwoFactorService

_service = TwoFactorService()


def _step() -> int:
    return random.randint(10 ** 9, 10 ** 9 + 100_000)


@pytest.mark.asyncio
async def test_same_step_cannot_be_claimed_twice():
    step = _step()
    assert await _service._claim_totp_step(1, step) is True
    # 第二次占用同一个时间步 = 重放，必须被拒
    assert await _service._claim_totp_step(1, step) is False


@pytest.mark.asyncio
async def test_different_users_do_not_share_steps():
    step = _step()
    assert await _service._claim_totp_step(1, step) is True
    assert await _service._claim_totp_step(2, step) is True


@pytest.mark.asyncio
async def test_adjacent_step_is_a_different_claim():
    base = _step()
    assert await _service._claim_totp_step(1, base) is True
    assert await _service._claim_totp_step(1, base + 1) is True
