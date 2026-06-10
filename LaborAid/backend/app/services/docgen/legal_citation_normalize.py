"""法条引用规范化 — 统一法律名称和条文号格式。"""

import re

# 常见法律简称 → 全称映射
LEGAL_NAME_MAP = {
    "劳动法": "中华人民共和国劳动法",
    "劳动合同法": "中华人民共和国劳动合同法",
    "劳动争议调解仲裁法": "中华人民共和国劳动争议调解仲裁法",
    "社会保险法": "中华人民共和国社会保险法",
    "工伤保险条例": "工伤保险条例",
    "失业保险条例": "失业保险条例",
    "民法典": "中华人民共和国民法典",
    "合同法": "中华人民共和国合同法",
    "公司法": "中华人民共和国公司法",
    "消费者权益保护法": "中华人民共和国消费者权益保护法",
    "产品质量法": "中华人民共和国产品质量法",
    "侵权责任法": "中华人民共和国侵权责任法",
    "婚姻法": "中华人民共和国婚姻法",
    "继承法": "中华人民共和国继承法",
    "物权法": "中华人民共和国物权法",
}

# 阿拉伯数字 → 中文数字映射
ARABIC_TO_CHINESE = {
    "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
    "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
    "10": "十", "11": "十一", "12": "十二", "13": "十三", "14": "十四",
    "15": "十五", "16": "十六", "17": "十七", "18": "十八", "19": "十九",
    "20": "二十", "21": "二十一", "22": "二十二", "23": "二十三", "24": "二十四",
    "25": "二十五", "26": "二十六", "27": "二十七", "28": "二十八", "29": "二十九",
    "30": "三十", "31": "三十一", "32": "三十二", "33": "三十三", "34": "三十四",
    "35": "三十五", "36": "三十六", "37": "三十七", "38": "三十八", "39": "三十九",
    "40": "四十", "41": "四十一", "42": "四十二", "43": "四十三", "44": "四十四",
    "45": "四十五", "46": "四十六", "47": "四十七", "48": "四十八", "49": "四十九",
    "50": "五十",
}


def _arabic_to_chinese(num_str: str) -> str:
    """将阿拉伯数字转换为中文数字（支持 0-50）。"""
    if num_str in ARABIC_TO_CHINESE:
        return ARABIC_TO_CHINESE[num_str]
    # 对于更大的数字，保持原样
    return num_str


def normalize_legal_names(text: str) -> str:
    """规范化法律名称：将简称替换为全称。"""
    result = text
    # 按长度降序排序，避免短名称覆盖长名称
    sorted_names = sorted(LEGAL_NAME_MAP.keys(), key=len, reverse=True)
    
    for short_name in sorted_names:
        full_name = LEGAL_NAME_MAP[short_name]
        # 匹配《简称》但不在《全称》中的情况
        pattern = rf"《{re.escape(short_name)}》"
        
        def replace_func(match):
            # 检查前面是否已经有"中华人民共和国"
            start = match.start()
            prefix = result[max(0, start - 9):start]
            if "中华人民共和国" in prefix:
                return match.group(0)  # 已经是全称，不替换
            return f"《{full_name}》"
        
        result = re.sub(pattern, replace_func, result)
    
    return result


def normalize_article_numbers(text: str) -> str:
    """规范化条文号：将阿拉伯数字转换为中文数字。"""
    # 匹配"第X条"、"第X款"、"第X项"
    pattern = r"第(\d+)([条款项])"
    
    def replace_func(match):
        num = match.group(1)
        unit = match.group(2)
        chinese_num = _arabic_to_chinese(num)
        return f"第{chinese_num}{unit}"
    
    return re.sub(pattern, replace_func, text)


def normalize_citation_format(text: str) -> str:
    """统一法条引用格式。"""
    result = text
    
    # 规范化法律名称
    result = normalize_legal_names(result)
    
    # 规范化条文号
    result = normalize_article_numbers(result)
    
    # 规范化括号：将英文括号替换为中文括号
    result = re.sub(r"\(([^)]+)\)", r"（\1）", result)
    
    # 规范化冒号：确保"规定："使用中文冒号
    result = re.sub(r"规定:", "规定：", result)
    
    return result


def normalize_markdown_citations(content: str) -> str:
    """对 Markdown 文书进行法条引用规范化。"""
    if not content or not content.strip():
        return content
    
    return normalize_citation_format(content)
