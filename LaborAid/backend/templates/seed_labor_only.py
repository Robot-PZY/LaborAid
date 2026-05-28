"""劳动者维权文书模板种子（兼容入口，完整配置见 seed_platform_pack）。"""

from templates.seed_platform_pack import seed_platform_pack


def seed_labor_templates() -> dict:
    """同步劳动者相关及平台公开模板（按 type 幂等更新）。"""
    return seed_platform_pack()


if __name__ == "__main__":
    print(seed_labor_templates())
