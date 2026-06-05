"""Test resolve_vision_llm / resolve_user_llm as the app does at runtime."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.services.llm_resolver import resolve_user_llm, resolve_vision_llm
from app.services.system_user import get_system_user


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = await get_system_user(db)
        text = await resolve_user_llm(db, user)
        vision = await resolve_vision_llm(db, user)

    print("=== 运行时模型解析（与证据 OCR / 文书生成一致）===\n")
    print("文本 LLM:")
    print(f"  名称: {text.config_name}")
    print(f"  来源: {text.source}")
    print(f"  模型: {text.model}")
    print(f"  Key: {'已配置 (' + text.api_key[:8] + '...)' if text.api_key else '未配置'}")
    print(f"  客户端: {'可用' if text.client else '不可用'}")

    print("\n视觉 OCR:")
    print(f"  名称: {vision.config_name}")
    print(f"  来源: {vision.source}")
    print(f"  模型: {vision.model}")
    print(f"  Key: {'已配置 (' + vision.api_key[:8] + '...)' if vision.api_key else '未配置'}")
    print(f"  客户端: {'可用' if vision.client else '不可用'}")


if __name__ == "__main__":
    asyncio.run(main())
