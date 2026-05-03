#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语加载器 - 负责加载内置/外部词典、拼写修正、初始化自动机
"""

import re
import json
import os
import time
from typing import Dict, Optional, Any
from core.log_manager import get_logger

try:
    import ahocorasick
    AHOCORASICK_AVAILABLE = True
except ImportError:
    ahocorasick = None
    AHOCORASICK_AVAILABLE = False

logger = get_logger(__name__)


class TerminologyLoader:
    """术语加载器"""

    def __init__(self, dict_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """初始化术语加载器
        
        Args:
            dict_path: 术语词典文件路径，None表示使用内置词典
            config: 配置字典，用于读取高级配置
        """
        self.dict_path = dict_path
        self.terms: Dict[str, str] = {}
        self.meta: Dict[str, str] = {}
        self.automaton = None
        self.lower_terms: Dict[str, str] = {}
        self.clean_terms: Dict[str, str] = {}
        self.clean_lower_terms: Dict[str, str] = {}
        self.spelling_mistakes: Dict[str, str] = {}
        
        # 从配置中读取自动机配置
        config = config or {}
        advanced_config = config.get('advanced', {})
        terminology_config = advanced_config.get('terminology', {})
        self.use_automaton = terminology_config.get('use_automaton', AHOCORASICK_AVAILABLE)
        
        # 加载内置术语
        self.load_default_terms()
        
        # 如果提供了词典文件路径，合并外部词典
        if dict_path:
            self.merge_file(dict_path)
        
        # 构建清洗后的术语映射
        self._build_clean_terms()

        # 构建自动机
        self._build_automaton()

        self._file_mtime = 0
        self._last_check_time = 0
        self._hot_update_interval = 5.0

    def check_for_updates(self) -> bool:
        """检查术语文件是否有更新

        Returns:
            True 表示有更新，False 表示无更新
        """
        if not self.dict_path:
            return False

        current_time = time.time()
        if current_time - self._last_check_time < self._hot_update_interval:
            return False

        self._last_check_time = current_time

        try:
            if os.path.exists(self.dict_path):
                file_mtime = os.path.getmtime(self.dict_path)
                if file_mtime > self._file_mtime:
                    self._file_mtime = file_mtime
                    return True
        except Exception as e:
            logger.warning(f"检查术语文件更新失败: {e}")

        return False

    def hot_reload(self) -> bool:
        """热更新术语词典

        Returns:
            True 表示更新成功，False 表示失败
        """
        if not self.dict_path:
            return False

        try:
            logger.info(f"开始热更新术语词典: {self.dict_path}")

            old_count = len(self.terms)

            self.terms.clear()
            self.lower_terms.clear()
            self.clean_terms.clear()
            self.clean_lower_terms.clear()
            self.meta.clear()

            self.load_default_terms()
            self.merge_file(self.dict_path)
            self._build_clean_terms()
            self._build_automaton()

            new_count = len(self.terms)
            logger.info(f"术语词典热更新完成: {old_count} -> {new_count} 条")

            return True

        except Exception as e:
            logger.error(f"术语词典热更新失败: {e}")
            return False

    def auto_update_if_needed(self) -> bool:
        """自动检查并热更新（如果需要）

        Returns:
            True 表示执行了更新，False 表示无需更新
        """
        if self.check_for_updates():
            return self.hot_reload()
        return False
        
        # 加载拼写修正
        self._load_spelling_corrections()

    def load_default_terms(self) -> None:
        """加载内置术语词典"""
        minecraft_terms = {
            # 系统相关
            'Content Update': '内容更新',
            'Farmer\'s Guidebook': '农场指南',
            'Sec. Tech': '安全技术',
            'Security Technology': '安全技术',
            'Security Add-On': '安全附加包',
            'Security': '安全',
            'Add-On': '附加包',

            # 物品和方块
            'Display Blocks': '展示方块',
            'Cropboxes': '作物箱',
            'Wooden Steps': '木质台阶',
            'ceramic dishes': '陶瓷餐具',
            'ceramic': '陶瓷',
            'Vault Block': '金库方块',
            'Reinforced Door': '加固门',
            'Reinforced Metal': '加固金属',
            'Crafting Table': '工作台',
            'Warning Block': '警告方块',
            'Canvas Block': '画布方块',

            # 系统和设备
            'breeding pen': '繁殖围栏',
            'feeding station': '喂食站',
            'irrigation network': '灌溉网络',
            'storage system': '存储系统',
            'milking system': '挤奶系统',
            'watering system': '浇水系统',
            'chopping board': '切菜板',
            'smoking oven': '熏烤炉',
            'fruit press': '水果压榨机',
            'roasting trays': '烤盘',
            'painting station': '绘画工作站',
            'grinding mill': '磨粉机',
            'transport cart': '运输车',
            'crop harvester': '作物收割机',
            'blueprint workstation': '蓝图工作站',
            'automatic machines': '自动机器',

            # 炮塔和武器
            'Turret': '炮塔',
            'Arrow Turret': '箭塔',
            'Laser Turret': '激光炮塔',
            'Blaster Turret': '冲击波炮塔',
            'Toxic Turret': '毒液炮塔',
            'Fire Turret': '火焰炮塔',
            'Controllable Turret': '可控炮塔',
            'Laser': '激光',
            'Projectile': '投射物',
            'Arrow': '箭',
            'Blaster': '冲击波',
            'Toxic': '毒液',
            'Fire': '火焰',

            # 无人机和机器人
            'Drone': '无人机',
            'Drone Laser': '无人机激光',
            'Thief Bot': '盗贼机器人',
            'Thief Bot Boss': '盗贼机器人首领',
            'Thief Bot 1': '盗贼机器人 1',
            'Thief Bot 2': '盗贼机器人 2',
            'Thief Bot 3': '盗贼机器人 3',
            'Raid': '突袭',
            'Raid Indicator': '突袭指示器',

            # 陷阱和防御
            'Trap': '陷阱',
            'Explosive Trap': '爆炸陷阱',
            'Fire Trap': '火焰陷阱',
            'Electric Trap': '电击陷阱',
            'Toxic Trap': '毒气陷阱',
            'Trap System': '陷阱系统',

            # 电子设备
            'Camera': '摄像头',
            'Screen': '屏幕',
            'Panel': '面板',
            'Panel Key': '面板钥匙',
            'Laser Light': '激光灯',
            'Laser Lights': '激光灯',
            'Remote Control': '遥控器',
            'Controller': '控制器',

            # 箱子
            'Chest': '箱子',
            'Security Chest': '安全箱',
            'Thief Chest': '盗贼箱子',
            'Thief Chest Pointer': '盗贼箱子指针',

            # 其他术语
            'Food items': '食物物品',
            'paint': '绘画',
            'painting': '绘画',
            'roasting': '烘焙',
            'Blocks': '方块',
            'Sabers': '激光剑',
            'Laser Saber': '激光剑',
            'Turrets': '炮塔',
            'Drones': '无人机',
            'Traps': '陷阱'
        }
        
        self.terms.update(minecraft_terms)
        logger.info(f"已加载内置 Minecraft 术语词典，共 {len(minecraft_terms)} 条。")

    def migrate_terms(self, old_version: str, old_dict: Dict[str, str]) -> int:
        """合并旧版术语词典（保留已有，新增缺失）"""
        added = 0
        for key, value in old_dict.items():
            if key != '_meta' and key not in self.terms:
                self.terms[key] = value
                added += 1
        if added:
            logger.info(f"术语迁移完成: 版本 {old_version} → 当前，新增 {added} 条")
        return added

    def get_meta(self) -> Dict[str, str]:
        """获取术语库元数据"""
        return dict(self.meta)

    def merge_file(self, path: str) -> None:
        """合并外部词典文件（自动识别 _meta 元数据）"""
        try:
            if path.lower().endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    external_terms = json.load(f)

                if '_meta' in external_terms:
                    self.meta.update(external_terms.pop('_meta'))

                filtered_terms = {}
                for key, value in external_terms.items():
                    if isinstance(value, str) and not (value.startswith('[') and value.endswith(']')):
                        filtered_terms[key] = value
                
                logger.info(f"已加载JSON术语词典，原始 {len(external_terms)} 条，过滤后 {len(filtered_terms)} 条。")
                
                for key, value in filtered_terms.items():
                    if key not in self.terms:
                        self.terms[key] = value
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                key, value = parts[0], parts[1]
                                if not (value.startswith('[') and value.endswith(']')):
                                    if key not in self.terms:
                                        self.terms[key] = value
                
                logger.info(f"已加载外部术语词典，共 {len(self.terms)} 条。")
                
        except Exception as e:
            logger.warning(f"加载外部术语词典失败: {e}，继续使用内置词典。")

    def _build_clean_terms(self) -> None:
        """构建清洗后文本的映射"""
        self.clean_terms = {}
        for key, value in self.terms.items():
            hash_pos = key.find('#')
            if hash_pos != -1:
                clean_key = key[:hash_pos]
            else:
                clean_key = key
            
            clean_key = clean_key.replace('\t', ' ')
            clean_key = re.sub(r'\s+', ' ', clean_key).strip()
            self.clean_terms[clean_key] = value
        
        self.lower_terms = {k.lower(): v for k, v in self.terms.items()}
        self.clean_lower_terms = {k.lower(): v for k, v in self.clean_terms.items()}

    def _build_automaton(self) -> None:
        """构建Aho-Corasick自动机用于快速术语匹配"""
        if not AHOCORASICK_AVAILABLE or not self.use_automaton:
            return
        
        try:
            self.automaton = ahocorasick.Automaton()
            for term in self.terms.keys():
                self.automaton.add_word(term.lower(), term)
            self.automaton.make_automaton()
            logger.info(f"已构建Aho-Corasick自动机，包含 {len(self.terms)} 个术语")
        except Exception as e:
            logger.warning(f"构建自动机失败: {e}，降级到纯正则模式")
            self.use_automaton = False
            self.automaton = None

    def _load_spelling_corrections(self, file_path: Optional[str] = None) -> None:
        """加载拼写修正映射表"""
        if file_path is None:
            from core.utils import resolve_resource_path
            file_path = str(resolve_resource_path('resources/spelling_corrections.json'))
        
        default_mistakes = {
            'ereramic': 'ceramic',
            'paintin ': 'painting ',
            'paintins': 'painting',
            'roastin ': 'roasting ',
            'roastin,': 'roasting,',
            'roastin.': 'roasting.',
            'roastin|': 'roasting|',
            'irrigationg': 'irrigation',
            'automatics': 'automatic',
            'stationg': 'station',
            'dishess': 'dishes',
            'itemss': 'items',
            'milkin ': 'milking ',
            'waterin ': 'watering ',
            'smokin ': 'smoking ',
            'choppin ': 'chopping ',
            'breedin ': 'breeding '
        }
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.spelling_mistakes = data.get('mistakes', default_mistakes)
                logger.info(f"已从 {file_path} 加载 {len(self.spelling_mistakes)} 条拼写修正规则")
            else:
                self.spelling_mistakes = default_mistakes
                logger.warning(f"拼写修正文件不存在: {file_path}，使用默认规则")
        except Exception as e:
            self.spelling_mistakes = default_mistakes
            logger.error(f"加载拼写修正文件失败: {e}，使用默认规则")

    def add_spelling_correction(self, mistake: str, correction: str) -> None:
        """添加新的拼写修正规则
        
        Args:
            mistake: 错误拼写
            correction: 正确拼写
        """
        self.spelling_mistakes[mistake] = correction

    def save_spelling_corrections(self) -> bool:
        """保存拼写修正规则到文件"""
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'resources',
            'spelling_corrections.json'
        )
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['mistakes'] = self.spelling_mistakes
            data['last_updated'] = time.strftime('%Y-%m-%d')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存拼写修正规则到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存拼写修正规则失败: {e}")
            return False
