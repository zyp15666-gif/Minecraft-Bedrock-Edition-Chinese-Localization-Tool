#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语词典分类重构迁移脚本

将扁平结构的minecraft_terms.json转换为分类结构。

迁移策略：
1. 读取现有扁平术语
2. 根据术语前缀/特征自动分类
3. 输出新的分类结构JSON
4. 保留完整的后向兼容

使用方法:
    python scripts/migrate_terms_structure.py [--input INPUT_PATH] [--output OUTPUT_PATH]
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

CATEGORY_PATTERNS = {
    'block': [
        r'(block|stone|wood|plank|slab|stair|brick|glass|ore|dirt|grass|sand|gravel|cobble)',
        r'(acacia|birch|spruce|jungle|oak|dark|diamond|gold|iron|coal|redstone|lapis|emerald)',
        r'(slab|stairs|fence|wall|door|trapdoor|button|lever|pressure|plate)',
        r'(potted|flower|pumpkin|melon|cactus|sugar|cocoa|vine|dead|bamboo)',
        r'(concrete|powder|wool|carpet|bed|painting|frame|item_frame)',
        r'(lantern|torch|candle|chandelier|sconce)',
        r'(cabinet|chair|table|bench|shelf|desk|bed|sofa|couch)',
        r'(crate|chest|barrel|hopper|dispenser|dropper|hopper)',
        r'(furnace|blast_furnace|smoker|enchant|anvil|grindstone|loom)',
        r'(loom|beehive|beetrap|composter|stonecutter|smithing)',
        r'(smithing|brewing|cauldron|blast_furnace|smoker)',
        r'(cauldron|composter|hopper|dropper|dispenser|observer)',
    ],
    'item': [
        r'(sword|axe|pickaxe|shovel|hoe|helmet|chestplate|leggings|boots|shield|bow|crossbow|trident|arrow)',
        r'(sword|dagger|staff|wand|gem|crystal|shard|fragment|pearl|ender_eye)',
        r'(sword|pickaxe|shovel|axe|hoe|hammer|sickle|scythe)',
        r'(sword|axe|pickaxe|shovel|hoe|shovel|broadsword|longsword|rapier)',
        r'(helmet|chestplate|leggings|boots|elytra|horse_armor|turtle_shell)',
        r'(shield|bow|crossbow|trident|arrow|tipped_arrow|spectral_arrow|firework)',
        r'(fishing_rod|carrot_on_a_stick|warped_fungus_on_a_stick|flint_and_steel|compass|clock)',
        r'(shears|bucket|water_bucket|lava_bucket|milk_bucket|powder_bucket)',
        r'(bucket|cauldron|glass_bottle|honey_bottle|experience|potion|lingering_potion|splash_potion)',
        r'(apple|bread|cake|cookie|golden_apple|enchanted_golden_apple|carrot|golden_carrot)',
        r'(steak|porkchop|chicken|mutton|rabbit|fish|salmon|tropical_fish|pufferfish)',
        r'(cooked_beef|cooked_porkchop|cooked_chicken|cooked_mutton|cooked_rabbit|cooked_fish|cooked_salmon)',
        r'(apple|bread|carrot|potato|baked_potato|beetroot|sweet_berry|glow_berry|honey)',
        r'(coal|charcoal|iron_ingot|gold_ingot|diamond|emerald|lapis|redstone|gold_nugget|iron_nugget)',
        r'(netherite|ancient_debris|scrap|ingot|nugget|smithing_template|armor_trim)',
        r'(disc|music_disc|ghast_tear|phantom_membrane|heart_of_the_sea|conduit|trident|nautilus)',
        r'(shulker_box|shulker_shell|elytra|dragon_breath|ghast_tear|ender_pearl|blaze_rod)',
        r'(book|written_book|writable_book|enchanted_book|book_and_quill|knowledge_book)',
        r'(map|empty_map|map_#\d+|filled_map|compass|recovery_compass|lodestone)',
        r'(firework|firework_rocket|firework_star|fire_charge|balloon|firework_star)',
        r'(saddle|horse_armor|name_tag|lead|bundle|bucket|fish)',
        r'(amethyst|spyglass|glow_item_frame|hanging_sign|heavy_core|traffic_settings)',
    ],
    'entity': [
        r'^entity\.',
        r'(creeper|zombie|skeleton|spider|enderman|witch|slime|magma_cube|ghast|blaze|',
         r'wither|ender_dragon|elder_guardian|shulker|phantom|drowned|husk|stray|',
         r'pillager|ravager|vindicator|evoker|vex|illusioner|vex|evoker)',
        r'(villager|wanderer|nitwit|wandering_trader|golem|iron_golem|snow_golem)',
        r'(pig|sheep|cow|chicken|rabbit|horse|donkey|mule|llama|alpaca|'
         r'mooshroom|horse|piglin|brute|piglin|hoglin|zombified_piglin)',
        r'(cat|wolf|fox|owl|parrot|bear|panda|bee|fox|sniffer|)',
        r'(axolotl|glow_squid|squid|dolphin|turtle|guardian|elder_guardian)',
        r'(bat|phantom|vex|allay)',
        r'(arrow|fireball|small_fireball|dragon_fireball|wither_skull|trident|'
         r'firework_rocket|llama_spit|shulker_bullet|arrow|projectile)',
        r'(boat|minecart|chest_minecart|furnace_minecart|tnt_minecart|hopper_minecart|'
         r'command_block_minecart|rail|powered_rail|detector_rail|activator_rail)',
        r'(armor_stand|item_frame|glow_item_frame|painting|frame)',
        r'(XP|m Experience|experience_orb|player|item)',
        r'(cow|mooshroom|sheep|pig|chicken|rabbit|turtle|llama|'
         r'hoglin|piglin|zoglin|piglin_brute)',
    ],
    'fluid': [
        r'(water|lava|river|milk|honey|slime| magma)',
        r'(flowing_water|stationary_water|flowing_lava|stationary_lava)',
        r'(water_bucket|lava_bucket|bucket|cauldron)',
    ],
    'enchantment': [
        r'(protection|fire_protection|feather_falling|blast_protection|'
         r'projectile_protection|respiration|aqua_affinity|thorns|depth_strider|'
         r'frost_walker|sharpness|smite|bane_of_arthropods|knockback|fire_aspect|'
         r'looting|efficiency|unbreaking|power|punch|flame|infinity|mending|'
         r'vanishing|binding|curse|loyalty|impaling|riptide|channeling|multishot|'
         r'piercing|quick_charge|sweeping|edge|mending|unbreakable)',
        r'(efficiency|unbreaking|vanishing|curse|mending|innertia)',
        r'(sharpness|smite|banne_of_arthropods|knockback|fire_aspect|looting|luck|luck_of_the_sea|lure)',
        r'(efficiency|silk_touch|fortune|looting|unbreaking|mending)',
        r'(power|punch|flame|infinity|multishot|piercing|quick_charge|'
         r'riptide|loyalty|impaling|channeling|depth_strider|',
         r'frost_walker|curse_of_vanishing|curse_of_binding)',
        r'(protection|fire_protection|blast_protection|projectile_protection|'
         r'respiration|aqua_affinity|thorns)',
    ],
    'ui': [
        r'(button|text_field|label|checkbox|switch|slider|dropdown|'
         r'dialog|alert|confirm|tooltip|popup|menu|sidebar|tab|'
         r'container|row|column|stack|grid|list|container)',
        r'(button|submit|cancel|close|ok|confirm|deny|accept|refuse|'
         r'save|load|export|import|delete|remove|add|create|edit|update)',
        r'(title|header|footer|sidebar|content|body|main|navigation|'
         r'breadcrumb|pagination|progress|loading|spinner|skeleton|'
         r'empty|error|success|warning|info|notification|toast|'
         r'snackbar|badge|chip|tag|label|caption|placeholder|'
         r'hint|helper_text|error_text|prefix|suffix|icon|avatar|'
         r'divider|separator|spacer|gap|margin|padding|border|'
         r'shadow|opacity|visible|hidden|disabled|enabled|'
         r'selected|checked|unchecked|indeterminate|loading|'
         r'saving|saved|exporting|importing|deleting|creating|'
         r'editing|updating|refreshing|retry|back|next|previous|'
         r'first|last|jump|search|filter|sort|group|expand|collapse|'
         r'open|close|minimize|maximize|fullscreen|window|dialog|'
         r'modal|popup|dropdown|select|option|choice|radio|checkbox|'
         r'toggle|switch|slider|range|input|textarea|text|number|'
         r'email|url|password|submit|reset|button|link|anchor)',
    ],
    'system': [
        r'^:_input_key',
        r'^:_hotbar_slot',
        r'^:_key_',
        r':_input_key|:_hotbar_slot|:_key|:_button|:_trigger|:_dpad',
        r'(achievement|advancement|statistic|statistics|scoreboard|objective|team|'
         r'redstone|comparator|repeater|lever|button|pressure_plate|'
         r'tripwire|observer|hopper|dropper|dispenser|daylight_detector|'
         r'redstone_torch|redstone_block|piston|sticky_piston|observer|'
         r'comparator|repeater|wire|line|dot|cross)',
        r'(command|cmd|execute|function|tag|scoreboard|team|objective|'
         r'selector|datapack|loot_table|advancement|recipe|'
         r'predicate|storage|entity|block|item|nbt|tag|'
         r'function|tag|advancement|loot|recipe|predicate|'
         r'schedule|tick|load|init|setup|teardown|'
         r'debug|test|dev|prod|main|server|client|render|'
         r'update|create|delete|modify|query|select|'
         r'set|add|remove|clear|reset|give|take|replace|'
         r'effect|enchant|xp|experience|level|kill|summon|'
         r'setblock|fill|clone|execute|spread|'
         r'tp|teleport|location|position|rotation|dimension|'
         r'world|dimension|environment|biome|weather|time|gamerule|'
         r'difficulty|default|peaceful|easy|normal|hard|'
         r'game_mode|survival|creative|adventure|spectator|'
         r'play_time|world_size|spawn_rate|spawn_limit)',
        r'(world_border|weather|rain|thunder|time|day|night|noon|midnight|'
         r'sunrise|sunset|moon|phase|calendar|season|'
         r'day_night_cycle|game_rule|gamerule|keep_inventory|'
         r'mob_griefing|explosion|fire_spread|'
         r'command|control|key|bind|setting|option|preference|'
         r'render|graphics|quality|performance|fps|lag|mspt|tps|rps)',
    ],
}


def classify_term(term: str, categories: Dict[str, List[str]]) -> Tuple[str, float]:
    """
    根据术语特征分类

    Returns:
        (category, confidence) - 分类结果和置信度
    """
    term_lower = term.lower()

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, term_lower, re.IGNORECASE):
                return category, 0.8

    return 'other', 0.1


def migrate_terms(input_path: str, output_path: str = None) -> Dict:
    """
    迁移术语词典到分类结构

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径，None表示覆盖原文件
    """
    print(f"读取术语词典: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    meta = data.get('_meta', {})
    terms = {k: v for k, v in data.items() if k != '_meta'}

    print(f"共 {len(terms)} 条术语")

    categories = {
        'block': {},
        'item': {},
        'entity': {},
        'fluid': {},
        'enchantment': {},
        'ui': {},
        'system': {},
        'other': {}
    }

    category_counts = {cat: 0 for cat in categories}
    unclassified = []

    for term, translation in terms.items():
        category, confidence = classify_term(term, categories)

        if category == 'other' and confidence < 0.5:
            unclassified.append((term, translation))
            categories['other'][term] = translation
        else:
            categories[category][term] = translation

        category_counts[category] += 1

    print("\n分类统计:")
    for cat, count in category_counts.items():
        print(f"  {cat}: {count} 条")

    print(f"\n未分类术语: {len(unclassified)} 条")

    migrated = {
        '_meta': {
            'version': '2.0',
            'updated_at': datetime.now().strftime('%Y-%m-%d'),
            'total_terms': len(terms),
            'description': 'Minecraft 基岩版汉化术语词典（分类结构）',
            'categories': list(categories.keys()),
            'migration_date': datetime.now().isoformat(),
            'original_version': meta.get('version', '1.0'),
        },
        **categories
    }

    output = output_path or input_path
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(migrated, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output}")

    return migrated


def main():
    import argparse

    parser = argparse.ArgumentParser(description='迁移术语词典到分类结构')
    parser.add_argument('--input', '-i', default='resources/api/minecraft_terms.json',
                        help='输入文件路径')
    parser.add_argument('--output', '-o', default=None,
                        help='输出文件路径（默认覆盖原文件）')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅显示统计，不写入文件')

    args = parser.parse_args()

    if args.dry_run:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
        terms = {k: v for k, v in data.items() if k != '_meta'}
        print(f"dry-run: 将分类 {len(terms)} 条术语")
        for term, _ in list(terms.items())[:10]:
            cat, conf = classify_term(term, {})
            print(f"  {term[:40]:40s} -> {cat} ({conf:.2f})")
    else:
        migrate_terms(args.input, args.output)


if __name__ == '__main__':
    main()
