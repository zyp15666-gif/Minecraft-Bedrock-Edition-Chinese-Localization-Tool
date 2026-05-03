#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 combined_en_US.lang 文件中提取附加包术语
用于扩展 Minecraft 术语词典
"""

import re
import json
import os
from typing import Dict, List, Tuple

def load_existing_terms(terms_file: str) -> Dict[str, str]:
    """加载现有术语词典
    
    Args:
        terms_file: 术语词典文件路径
        
    Returns:
        术语字典 {英文: 中文}
    """
    try:
        with open(terms_file, 'r', encoding='utf-8') as f:
            terms = json.load(f)
        print(f"✅ 已加载现有术语词典: {len(terms)} 条")
        return terms
    except Exception as e:
        print(f"❌ 加载现有术语词典失败: {e}")
        return {}

def extract_terms_from_lang_file(file_path: str) -> Dict[str, List[str]]:
    """从.lang文件中提取潜在术语
    
    Args:
        file_path: .lang文件路径
        
    Returns:
        字典包含提取的术语和上下文
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # 提取所有键值对
    terms = []
    term_context = {}
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('##'):
            continue
        
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if not value:
                continue
            
            # 清理文本：移除颜色代码、占位符、特殊格式
            clean_value = re.sub(r'§[0-9a-fklmnor]', '', value)
            clean_value = re.sub(r'~LINEBREAK~', ' ', clean_value)
            clean_value = re.sub(r'%[0-9]*\$?[sdf]', '', clean_value)
            clean_value = re.sub(r'\\n', ' ', clean_value)
            clean_value = re.sub(r'[\[\]{}()<>]', '', clean_value)
            
            # 提取可能的大写单词（术语通常首字母大写或全大写）
            # 1. 提取全大写单词（如 UI, GPS 等）
            uppercase_words = re.findall(r'\b[A-Z]{2,}\b', clean_value)
            
            # 2. 提取首字母大写的单词（术语）
            titlecase_words = re.findall(r'\b[A-Z][a-z]+\b', clean_value)
            
            # 3. 提取复合术语（如 Health Amulet, Better Maps）
            compound_terms = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', clean_value)
            
            # 4. 提取包含多个单词的术语（如 Better Maps Add-On）
            multiword_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', clean_value)
            
            # 5. 提取游戏内实体/物品标识符（如 item.jfc_amulet:health_amulet）
            # 从key中提取标识符部分
            if ':' in key:
                # 提取冒号后的部分
                identifier = key.split(':')[-1]
                # 分割下划线和点号
                parts = re.split(r'[._]', identifier)
                for part in parts:
                    if part and part[0].isupper():
                        titlecase_words.append(part)
            
            all_terms = uppercase_words + titlecase_words + compound_terms + multiword_terms
            
            for term in all_terms:
                if len(term) > 2:  # 忽略过短的词
                    terms.append(term)
                    if term not in term_context:
                        term_context[term] = []
                    term_context[term].append(f"{key}={value[:50]}...")
    
    # 计算术语频率
    term_freq = {}
    for term in terms:
        term_freq[term] = term_freq.get(term, 0) + 1
    
    # 按频率排序
    sorted_terms = sorted(term_freq.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'sorted_terms': sorted_terms,
        'term_context': term_context,
        'total_unique_terms': len(term_freq)
    }

def identify_missing_terms(extracted_terms: List[Tuple[str, int]], existing_terms: Dict[str, str]) -> List[str]:
    """识别缺失的术语
    
    Args:
        extracted_terms: 提取的术语列表 (术语, 频率)
        existing_terms: 现有术语词典
        
    Returns:
        缺失的术语列表
    """
    missing = []
    existing_lower = {k.lower(): v for k, v in existing_terms.items()}
    
    for term, freq in extracted_terms:
        term_lower = term.lower()
        
        # 检查是否已存在（不区分大小写）
        if term_lower in existing_lower:
            continue
        
        # 检查是否为现有术语的部分匹配（如 "Amulet" 可能包含在 "Health Amulet" 中）
        is_part_of_existing = False
        for existing in existing_terms.keys():
            if term_lower in existing.lower() or existing.lower() in term_lower:
                is_part_of_existing = True
                break
        
        if not is_part_of_existing:
            missing.append(term)
    
    return missing

def generate_translation_suggestions(missing_terms: List[str], term_context: Dict[str, List[str]]) -> List[Dict]:
    """为缺失术语生成翻译建议
    
    Args:
        missing_terms: 缺失术语列表
        term_context: 术语上下文字典
        
    Returns:
        包含翻译建议的字典列表
    """
    suggestions = []
    
    # 基于上下文的翻译建议规则
    translation_rules = {
        # Amulets Add-on 相关
        'Amulet': '护符',
        'Health': '生命',
        'Inferno': '地狱',
        'Frost': '寒霜',
        'Storm': '风暴',
        'Nature': '自然',
        'Venom': '剧毒',
        'Wind': '狂风',
        'Shadow': '暗影',
        'Soul': '灵魂',
        'Guardian': '守护',
        
        # Better Maps 相关
        'Waypoint': '路径点',
        'Gravestone': '墓碑',
        'Map': '地图',
        'Minimap': '小地图',
        'Zoom': '缩放',
        'Destination': '目的地',
        'Teleport': '传送',
        'Permission': '权限',
        'Settings': '设置',
        'Global': '全局',
        'Player': '玩家',
        'Public': '公开',
        'Private': '私有',
        'Icon': '图标',
        'Colour': '颜色',
        'Aqua': '水色',
        'Black': '黑色',
        'Blue': '蓝色',
        'Dark': '暗',
        'Gray': '灰色',
        'Green': '绿色',
        'Purple': '紫色',
        'Red': '红色',
        'Gold': '金色',
        'White': '白色',
        'Yellow': '黄色',
        'Light': '亮',
        
        # Better on Bedrock 相关
        'Goblin': '地精',
        'Trader': '商人',
        'Bounty': '赏金',
        'Board': '板',
        'Backpack': '背包',
        'Waystone': '路标石',
        'Achievement': '成就',
        'Mana': '魔力',
        'Staff': '法杖',
        'Enchant': '附魔',
        'Tool': '工具',
        'Ore': '矿石',
        'Pickaxe': '镐',
        'Copper': '铜',
        'Iron': '铁',
        'Hardcore': '极限模式',
        'Necklace': '项链',
        'Ghost': '幽灵',
        
        # 通用游戏术语
        'Add-on': '附加包',
        'Add-On': '附加包',
        'Guide': '指南',
        'Book': '书',
        'Menu': '菜单',
        'Button': '按钮',
        'Title': '标题',
        'Body': '正文',
        'Description': '描述',
        'Location': '位置',
        'Distance': '距离',
        'Dimension': '维度',
        'Resolution': '分辨率',
        'Mode': '模式',
        'Option': '选项',
        'Always': '总是',
        'Never': '从不',
        'Still': '静止时',
        'Creative': '创造模式',
        'Cave': '洞穴',
        'Surface': '地表',
        'Nether': '下界',
        'Crafting': '合成',
        'Crafted': '已合成',
        'Death': '死亡',
        'Die': '死亡',
        'Spawn': '生成',
        'Item': '物品',
        'Entity': '实体',
        'Command': '命令',
        'Config': '配置',
        'Update': '更新',
    }
    
    for term in missing_terms:
        contexts = term_context.get(term, [])
        
        # 生成翻译建议
        translation = term
        
        # 规则1: 检查是否匹配完整术语
        if term in translation_rules:
            translation = translation_rules[term]
        
        # 规则2: 检查是否为复合术语（如 Health Amulet）
        else:
            words = re.findall(r'[A-Z][a-z]+', term)
            if words:
                translated_words = []
                for word in words:
                    if word in translation_rules:
                        translated_words.append(translation_rules[word])
                    else:
                        # 保留原词，但标记需要人工翻译
                        translated_words.append(f"[{word}]")
                translation = ''.join(translated_words)
        
        # 规则3: 如果是单个单词且未找到翻译，尝试常见后缀处理
        if translation == term and len(words) == 1:
            # 常见后缀处理
            if term.endswith('s') and term[:-1] in translation_rules:
                translation = translation_rules[term[:-1]] + "们"
            elif term.endswith('ing') and term[:-3] in translation_rules:
                translation = translation_rules[term[:-3]] + "中"
        
        suggestions.append({
            'term': term,
            'suggested_translation': translation,
            'contexts': contexts[:2],  # 只显示前2个上下文
            'context_count': len(contexts),
            'needs_review': translation == term or '[' in translation
        })
    
    return suggestions

def main():
    """主函数"""
    print("=" * 60)
    print("附加包术语提取工具")
    print("=" * 60)
    
    # 文件路径
    lang_file = "data/combined_en_US.lang"
    terms_file = "resources/api/minecraft_terms.json"
    
    print(f"📄 分析文件: {lang_file}")
    print(f"📚 现有术语词典: {terms_file}")
    
    # 检查文件是否存在
    if not os.path.exists(lang_file):
        print(f"❌ 文件不存在: {lang_file}")
        return
    
    # 1. 提取术语
    print("\n🔍 提取术语中...")
    result = extract_terms_from_lang_file(lang_file)
    sorted_terms = result['sorted_terms']
    term_context = result['term_context']
    total_unique = result['total_unique_terms']
    
    print(f"📊 提取结果:")
    print(f"   唯一术语数量: {total_unique}")
    print(f"   总出现次数: {sum(freq for _, freq in sorted_terms)}")
    
    # 显示前30个最频繁的术语
    print(f"\n🏆 前30个最频繁的术语:")
    for i, (term, freq) in enumerate(sorted_terms[:30], 1):
        print(f"   {i:2d}. {term:30s} (出现 {freq:2d} 次)")
    
    # 2. 加载现有术语
    existing_terms = load_existing_terms(terms_file)
    
    # 3. 识别缺失术语
    missing_terms = identify_missing_terms(sorted_terms, existing_terms)
    print(f"\n🔍 缺失术语数量: {len(missing_terms)}")
    
    if missing_terms:
        print("\n❌ 缺失的术语:")
        for i, term in enumerate(missing_terms[:50], 1):
            print(f"   {i:2d}. {term}")
        
        if len(missing_terms) > 50:
            print(f"   ... 还有 {len(missing_terms) - 50} 个术语未显示")
        
        # 4. 生成翻译建议
        print("\n💡 翻译建议:")
        suggestions = generate_translation_suggestions(missing_terms, term_context)
        
        # 按是否需要人工审核排序
        suggestions.sort(key=lambda x: (x['needs_review'], -x['context_count']))
        
        print("\n" + "=" * 60)
        print("📋 扩展词典建议 (JSON格式)")
        print("=" * 60)
        
        print("\n将以下术语添加到 resources/api/minecraft_terms.json 文件中:")
        print("\n{")
        
        for suggestion in suggestions[:100]:  # 最多显示100个
            term = suggestion['term']
            translation = suggestion['suggested_translation']
            needs_review = suggestion['needs_review']
            
            # 标记需要人工审核的术语
            if needs_review:
                print(f'  "{term}": "{translation}",  # ⚠️ 需要人工审核')
            else:
                print(f'  "{term}": "{translation}",')
        
        print("}")
        
        # 统计信息
        needs_review_count = sum(1 for s in suggestions if s['needs_review'])
        auto_translated_count = len(suggestions) - needs_review_count
        
        print(f"\n📊 统计:")
        print(f"   总缺失术语: {len(missing_terms)}")
        print(f"   自动翻译建议: {auto_translated_count}")
        print(f"   需要人工审核: {needs_review_count}")
        
        # 5. 生成扩展文件
        print("\n" + "=" * 60)
        print("💾 生成扩展文件")
        print("=" * 60)
        
        # 创建扩展词典（合并现有和新增）
        extended_terms = existing_terms.copy()
        for suggestion in suggestions:
            term = suggestion['term']
            translation = suggestion['suggested_translation']
            if term not in extended_terms:
                extended_terms[term] = translation
        
        # 保存扩展词典
        extended_file = "resources/api/minecraft_terms_extended.json"
        with open(extended_file, 'w', encoding='utf-8') as f:
            json.dump(extended_terms, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已生成扩展术语词典: {extended_file}")
        print(f"   总术语数: {len(extended_terms)} (+{len(extended_terms) - len(existing_terms)})")
        
        # 生成合并脚本
        merge_script = """
# 合并术语词典脚本
import json

# 加载现有词典
with open('resources/api/minecraft_terms.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

# 加载扩展词典
with open('resources/api/minecraft_terms_extended.json', 'r', encoding='utf-8') as f:
    extended = json.load(f)

# 合并（扩展覆盖现有）
existing.update(extended)

# 保存
with open('resources/api/minecraft_terms.json', 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

print(f"✅ 术语词典已更新，总术语数: {len(existing)}")
"""
        
        with open("merge_terms.py", 'w', encoding='utf-8') as f:
            f.write(merge_script)
        
        print("✅ 已生成合并脚本: merge_terms.py")
        print("\n💡 使用方法:")
        print("   1. 审查翻译建议，修改 resources/api/minecraft_terms_extended.json 中的翻译")
        print("   2. 运行: python merge_terms.py")
        print("   3. 重启翻译服务以应用新术语")
    
    else:
        print("\n✅ 没有缺失术语，现有词典已足够完整")
    
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()