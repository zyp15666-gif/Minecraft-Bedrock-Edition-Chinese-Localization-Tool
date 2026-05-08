#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译一致性检查工具
检查同一英文术语在不同上下文中的中文翻译是否一致
"""

import os
import re
from typing import Dict, List


def parse_lang_file(file_path: str) -> Dict[str, str]:
    """解析.lang文件，返回键值对字典

    Args:
        file_path: .lang文件路径

    Returns:
        键值对字典 {key: value}
    """
    entries = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        entries[key] = value
    except Exception as e:
        print(f"❌ 解析文件失败 {file_path}: {e}")

    return entries

def extract_english_terms(text: str) -> List[str]:
    """从文本中提取英文术语

    Args:
        text: 文本内容

    Returns:
        提取的英文术语列表
    """
    # 移除颜色代码
    clean_text = re.sub(r'§[0-9a-fklmnor]', '', text)
    # 移除占位符
    clean_text = re.sub(r'%[0-9]*\$?[sdf]', '', clean_text)
    # 移除其他特殊字符
    clean_text = re.sub(r'[\[\]{}()<>]', ' ', clean_text)

    # 提取英文单词（至少2个字符，包含字母）
    # 匹配首字母大写的单词（可能为术语）
    titlecase_words = re.findall(r'\b[A-Z][a-z]+\b', clean_text)
    # 匹配全大写单词（缩写）
    uppercase_words = re.findall(r'\b[A-Z]{2,}\b', clean_text)
    # 匹配复合术语（如 Laser Saber）
    compound_terms = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', clean_text)

    all_terms = titlecase_words + uppercase_words + compound_terms

    # 过滤掉常见非术语单词
    common_words = {
        'The', 'And', 'For', 'With', 'This', 'That', 'You', 'Your', 'Have',
        'From', 'Will', 'Not', 'Are', 'But', 'Can', 'Was', 'Were', 'Has',
        'Had', 'Been', 'More', 'Most', 'Some', 'Such', 'Only', 'Just',
        'Like', 'Then', 'Than', 'Now', 'How', 'What', 'When', 'Where',
        'Which', 'Who', 'Why', 'Into', 'Upon', 'About', 'After', 'Before',
        'Between', 'Under', 'Over', 'Through', 'During', 'Without', 'Within'
    }

    filtered_terms = []
    for term in all_terms:
        if len(term) > 2 and term not in common_words:
            filtered_terms.append(term)

    return filtered_terms

def analyze_translation_consistency(en_file: str, zh_file: str) -> Dict[str, Dict]:
    """分析翻译一致性

    Args:
        en_file: 英文.lang文件路径
        zh_file: 中文.lang文件路径

    Returns:
        一致性分析结果
    """
    print("🔍 分析翻译一致性...")
    print(f"   英文文件: {en_file}")
    print(f"   中文文件: {zh_file}")

    # 解析文件
    en_entries = parse_lang_file(en_file)
    zh_entries = parse_lang_file(zh_file)

    print(f"   英文条目: {len(en_entries)}")
    print(f"   中文条目: {len(zh_entries)}")

    # 构建英文术语到中文翻译的映射
    term_translations = {}

    for key, en_value in en_entries.items():
        if key not in zh_entries:
            continue

        zh_value = zh_entries[key]

        # 从英文值中提取术语
        english_terms = extract_english_terms(en_value)

        for term in english_terms:
            if term not in term_translations:
                term_translations[term] = {
                    'translations': set(),
                    'contexts': [],
                    'count': 0
                }

            # 从中文翻译中提取对应部分（如果存在）
            # 简单检查：如果英文术语在中文翻译中未出现，则可能已翻译
            if term.lower() not in zh_value.lower():
                # 术语可能已被翻译，记录中文翻译
                # 这里我们记录整个中文翻译作为参考
                term_translations[term]['translations'].add(zh_value)
                term_translations[term]['contexts'].append(f"{key}: {en_value} → {zh_value}")
                term_translations[term]['count'] += 1

    # 找出不一致的术语（多个不同翻译）
    inconsistent_terms = {}
    for term, data in term_translations.items():
        if len(data['translations']) > 1:
            inconsistent_terms[term] = data

    # 按出现频率排序
    sorted_inconsistent = sorted(
        inconsistent_terms.items(),
        key=lambda x: (x[1]['count'], len(x[1]['translations'])),
        reverse=True
    )

    return {
        'inconsistent_terms': dict(sorted_inconsistent),
        'total_terms': len(term_translations),
        'total_inconsistent': len(inconsistent_terms)
    }

def generate_fix_suggestions(inconsistent_terms: Dict[str, Dict]) -> List[Dict]:
    """生成修复建议

    Args:
        inconsistent_terms: 不一致术语字典

    Returns:
        修复建议列表
    """
    suggestions = []

    # 加载术语词典，获取官方翻译
    try:
        with open('resources/api/minecraft_terms.json', 'r', encoding='utf-8') as f:
            import json
            term_dict = json.load(f)
    except:
        term_dict = {}

    for term, data in inconsistent_terms.items():
        translations = list(data['translations'])
        contexts = data['contexts'][:3]  # 只显示前3个上下文

        # 检查术语词典中是否有官方翻译
        official_translation = term_dict.get(term, None)

        # 选择最常见的翻译作为建议
        # 这里简单选择第一个翻译作为建议（实际应分析上下文）
        suggested_translation = translations[0] if translations else term

        # 如果术语词典中有官方翻译，使用官方翻译
        if official_translation and official_translation not in translations:
            suggested_translation = official_translation
            source = "术语词典"
        elif official_translation:
            suggested_translation = official_translation
            source = "术语词典（已存在）"
        else:
            # 分析哪个翻译更常见（这里简化处理）
            # 实际应该分析上下文和翻译质量
            source = "首次出现"

        suggestions.append({
            'term': term,
            'translations': translations,
            'translation_count': len(translations),
            'occurrence_count': data['count'],
            'suggested_translation': suggested_translation,
            'source': source,
            'contexts': contexts
        })

    return suggestions

def main():
    """主函数"""
    print("=" * 60)
    print("翻译一致性检查工具")
    print("=" * 60)

    # 文件路径
    en_file = "en_US.lang"
    zh_file = "zh_cn.lang"

    # 检查文件是否存在
    if not os.path.exists(en_file):
        print(f"❌ 英文文件不存在: {en_file}")
        return

    if not os.path.exists(zh_file):
        print(f"❌ 中文文件不存在: {zh_file}")
        return

    # 分析一致性
    result = analyze_translation_consistency(en_file, zh_file)

    print("\n📊 分析结果:")
    print(f"   总术语数: {result['total_terms']}")
    print(f"   不一致术语数: {result['total_inconsistent']}")

    inconsistent_terms = result['inconsistent_terms']

    if inconsistent_terms:
        print(f"\n⚠️  发现 {len(inconsistent_terms)} 个不一致的术语:")

        # 生成修复建议
        suggestions = generate_fix_suggestions(inconsistent_terms)

        # 按不一致程度排序（翻译变体数量 * 出现次数）
        suggestions.sort(key=lambda x: x['translation_count'] * x['occurrence_count'], reverse=True)

        # 显示前20个最需要修复的术语
        print("\n🔧 前20个最需要修复的术语:")
        for i, suggestion in enumerate(suggestions[:20], 1):
            print(f"\n{i:2d}. {suggestion['term']}")
            print(f"    出现次数: {suggestion['occurrence_count']}")
            print(f"    翻译变体: {suggestion['translation_count']} 种")
            print(f"    当前翻译: {', '.join(suggestion['translations'][:3])}")
            print(f"    建议翻译: {suggestion['suggested_translation']} ({suggestion['source']})")

            if suggestion['contexts']:
                print(f"    上下文示例: {suggestion['contexts'][0]}")

        # 生成修复脚本
        print("\n" + "=" * 60)
        print("🛠️  生成修复脚本")
        print("=" * 60)

        fix_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
        fix_script += f'''
"""
翻译一致性修复脚本
修复 {len(suggestions)} 个不一致的术语翻译
"""

import re

def fix_translation_inconsistencies():
    """修复翻译不一致问题"""

    # 读取中文文件
    with open('{zh_file}', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 修复规则
    fix_rules = {{
'''

        # 添加修复规则（前50个）
        for suggestion in suggestions[:50]:
            term = suggestion['term']
            suggested = suggestion['suggested_translation']
            fix_script += f'        "{term}": "{suggested}",  # 替换为统一翻译\n'

        fix_script += '''    }

    # 应用修复
    fixed_lines = []
    for line in lines:
        fixed_line = line
        for term, replacement in fix_rules.items():
            # 简单的字符串替换（注意：这可能过于简单，需要根据实际情况调整）
            # 这里应该使用更智能的替换逻辑，比如只替换独立的术语
            fixed_line = fixed_line.replace(term, replacement)
        fixed_lines.append(fixed_line)

    # 保存修复后的文件
    with open('zh_cn_fixed.lang', 'w', encoding='utf-8', newline='\\n') as f:
        f.writelines(fixed_lines)

    print(f"✅ 修复完成，保存为: zh_cn_fixed.lang")
    print(f"   修复了 {len(fix_rules)} 个术语的不一致问题")

if __name__ == "__main__":
    fix_translation_inconsistencies()
'''

        with open("fix_translation_consistency.py", 'w', encoding='utf-8') as f:
            f.write(fix_script)

        print("✅ 已生成修复脚本: fix_translation_consistency.py")
        print(f"   包含 {min(50, len(suggestions))} 个修复规则")
        print("\n💡 使用方法:")
        print("   1. 审查修复规则，确保翻译准确")
        print("   2. 运行: python fix_translation_consistency.py")
        print("   3. 检查生成的 zh_cn_fixed.lang 文件")

        # 显示更多统计数据
        print("\n📈 详细统计:")

        # 按翻译变体数量分组
        variant_counts = {}
        for suggestion in suggestions:
            count = suggestion['translation_count']
            variant_counts[count] = variant_counts.get(count, 0) + 1

        print("   翻译变体分布:")
        for count in sorted(variant_counts.keys()):
            print(f"     {count} 种变体: {variant_counts[count]} 个术语")

    else:
        print("\n✅ 没有发现不一致的术语，翻译一致性良好！")

    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
