"""Tests for enterprise search key resolver."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.enterprise.query_resolver import (
    looks_like_credit_code,
    looks_like_full_company_name,
    needs_llm_resolution,
    resolve_enterprise_search_key,
)


def test_looks_like_credit_code():
    assert looks_like_credit_code("91110000MA01234567")
    assert not looks_like_credit_code("腾讯")


def test_looks_like_full_company_name():
    assert looks_like_full_company_name("深圳市腾讯计算机系统有限公司")
    assert looks_like_full_company_name("测试科技有限公司")
    assert not looks_like_full_company_name("腾讯")
    assert not looks_like_full_company_name("华为")


def test_needs_llm_resolution():
    assert needs_llm_resolution("腾讯")
    assert needs_llm_resolution("字节")
    assert not needs_llm_resolution("91110000MA01234567")
    assert not needs_llm_resolution("测试科技有限公司")


@pytest.mark.asyncio
async def test_resolve_skips_llm_for_full_name():
    llm = MagicMock()
    llm.client = AsyncMock()
    result = await resolve_enterprise_search_key("测试科技有限公司", llm=llm)
    assert result == "测试科技有限公司"
    llm.client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_skips_llm_for_credit_code():
    code = "91110000MA01234567"
    llm = MagicMock()
    llm.client = AsyncMock()
    result = await resolve_enterprise_search_key(code, llm=llm)
    assert result == code
    llm.client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_uses_llm_for_short_name():
    llm = MagicMock()
    llm.model = "test-model"
    llm.max_tokens = 4096
    llm.client = AsyncMock()
    llm.client.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[
                MagicMock(
                    text='{"search_key": "深圳市腾讯计算机系统有限公司", "reason": "腾讯品牌主体"}'
                )
            ]
        )
    )

    result = await resolve_enterprise_search_key("腾讯", llm=llm)
    assert result == "深圳市腾讯计算机系统有限公司"
    llm.client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_falls_back_when_llm_unavailable():
    result = await resolve_enterprise_search_key("腾讯", llm=None)
    assert result == "腾讯"


@pytest.mark.asyncio
async def test_resolve_falls_back_on_invalid_llm_output():
    llm = MagicMock()
    llm.model = "test-model"
    llm.max_tokens = 4096
    llm.client = AsyncMock()
    llm.client.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text='{"search_key": "腾讯", "reason": "不确定"}')])
    )

    result = await resolve_enterprise_search_key("腾讯", llm=llm)
    assert result == "腾讯"
