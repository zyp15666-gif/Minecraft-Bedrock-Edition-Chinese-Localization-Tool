#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能按钮分组布局组件

将11个功能按钮按照业务逻辑分组显示：
- 提取类：仅提取汉化key
- 翻译类：提取+翻译、多文件翻译等
- 批处理类：批量替换、删除、还原
- 管理类：备份管理

提供更清晰的UI组织和更好的用户体验。
"""

import flet as ft
from typing import List, Dict, Callable, Any, Optional
from enum import Enum


class FunctionButtonGroups(Enum):
    """功能按钮分组枚举"""
    EXTRACTION = ("提取类", ft.Colors.BLUE, "📤")
    TRANSLATION = ("翻译类", ft.Colors.GREEN, "🌐")
    BATCH_OPERATION = ("批处理", ft.Colors.ORANGE, "🔄")
    MANAGEMENT = ("管理类", ft.Colors.PURPLE, "⚙️")


class FunctionButtonConfig:
    """功能按钮配置"""

    BUTTON_GROUPS: Dict[str, FunctionButtonGroups] = {
        'extract_only': FunctionButtonGroups.EXTRACTION,
        'extract_and_translate': FunctionButtonGroups.TRANSLATION,
        'replace_display_names': FunctionButtonGroups.BATCH_OPERATION,
        'batch_delete_value': FunctionButtonGroups.BATCH_OPERATION,
        'batch_restore_value': FunctionButtonGroups.BATCH_OPERATION,
        'translate_lang_file': FunctionButtonGroups.TRANSLATION,
        'one_click_service': FunctionButtonGroups.TRANSLATION,
        'adapt_entity_display_names': FunctionButtonGroups.TRANSLATION,
        'translate_single_js_file': FunctionButtonGroups.TRANSLATION,
        'script_hardcode_translation': FunctionButtonGroups.TRANSLATION,
        'backup_management': FunctionButtonGroups.MANAGEMENT,
    }

    BUTTON_DEFINITIONS: List[Dict[str, Any]] = [
        {
            'key': 'extract_only',
            'name': '1. 仅提取',
            'icon': ft.icons.EXTRACT,
            'group': FunctionButtonGroups.EXTRACTION,
            'description': '提取汉化key',
        },
        {
            'key': 'extract_and_translate',
            'name': '2. 提取+翻译',
            'icon': ft.icons.TRANSLATE,
            'group': FunctionButtonGroups.TRANSLATION,
            'description': '提取并AI翻译',
        },
        {
            'key': 'replace_display_names',
            'name': '3. 替换显示名',
            'icon': ft.icons.SWAP_HORIZ,
            'group': FunctionButtonGroups.BATCH_OPERATION,
            'description': '全BP替换display_name',
        },
        {
            'key': 'batch_delete_value',
            'name': '4. 批量删除',
            'icon': ft.icons.DELETE_OUTLINE,
            'group': FunctionButtonGroups.BATCH_OPERATION,
            'description': '批量删除value',
        },
        {
            'key': 'batch_restore_value',
            'name': '5. 批量还原',
            'icon': ft.icons.RESTORE,
            'group': FunctionButtonGroups.BATCH_OPERATION,
            'description': '批量还原value',
        },
        {
            'key': 'translate_lang_file',
            'name': '6. 翻译lang',
            'icon': ft.icons.FILE_COPY,
            'group': FunctionButtonGroups.TRANSLATION,
            'description': '翻译.lang文件',
        },
        {
            'key': 'one_click_service',
            'name': '7. 一条龙',
            'icon': ft.icons.AUTO_AWESOME,
            'group': FunctionButtonGroups.TRANSLATION,
            'description': '全自动一条龙服务',
        },
        {
            'key': 'adapt_entity_display_names',
            'name': '8. 实体适配',
            'icon': ft.icons.PETS,
            'group': FunctionButtonGroups.TRANSLATION,
            'description': '实体信息显示名适配',
        },
        {
            'key': 'translate_single_js_file',
            'name': '9. JS翻译',
            'icon': ft.icons.JAVASCRIPT,
            'group': FunctionButtonGroups.TRANSLATION,
            'description': '翻译单个JS文件',
        },
        {
            'key': 'script_hardcode_translation',
            'name': '10. 脚本汉化',
            'icon': ft.icons.CODE,
            'group': FunctionButtonGroups.TRANSLATION,
            'description': '脚本硬编码汉化',
        },
        {
            'key': 'backup_management',
            'name': '11. 备份管理',
            'icon': ft.icons.BACKUP,
            'group': FunctionButtonGroups.MANAGEMENT,
            'description': '备份文件管理',
        },
    ]


class ButtonGroupCard(ft.Container):
    """按钮分组卡片"""

    def __init__(
        self,
        group: FunctionButtonGroups,
        buttons: List[ft.ElevatedButton],
        on_button_click: Callable[[str], None],
        expanded: bool = True,
    ):
        """初始化按钮分组卡片

        Args:
            group: 分组信息
            buttons: 该分组下的按钮列表
            on_button_click: 按钮点击回调
            expanded: 是否默认展开
        """
        self.group = group
        self.buttons = buttons
        self.on_button_click = on_button_click
        self._expanded = expanded

        group_name, group_color, group_icon = group.value

        content = ft.Column(
            controls=self._build_content(),
            spacing=8,
        )

        super().__init__(
            content=content,
            padding=10,
            border_radius=8,
            border=ft.Border.all(1, group_color),
            bgcolor=ft.Colors.with_opacity(0.05, group_color),
        )

    def _build_content(self) -> List[ft.Control]:
        """构建卡片内容"""
        group_name, group_color, group_icon = self.group.value

        header = ft.Container(
            content=ft.Row([
                ft.Text(f"{group_icon} {group_name}", size=14, weight=ft.FontWeight.BOLD, color=group_color),
                ft.Container(expand=True),
                ft.Text(f"{len(self.buttons)}个功能", size=11, color=ft.Colors.GREY),
            ]),
            padding=5,
        )

        content = [header, ft.Divider(height=1, color=group_color)]

        if self._expanded:
            content.extend(self.buttons)
        else:
            collapsed_text = ft.Text("点击展开...", size=12, color=ft.Colors.GREY, italic=True)
            content.append(collapsed_text)

        return content


class FunctionButtonGroupLayout(ft.Container):
    """功能按钮分组布局组件"""

    def __init__(
        self,
        button_configs: List[Dict[str, Any]] = None,
        on_button_click: Optional[Callable[[str], None]] = None,
        columns_per_group: int = 2,
        button_height: float = 45,
    ):
        """初始化功能按钮分组布局

        Args:
            button_configs: 按钮配置列表，默认使用BUTTON_DEFINITIONS
            on_button_click: 按钮点击回调，参数为按钮key
            columns_per_group: 每个分组中每行的按钮数
            button_height: 按钮高度
        """
        self.button_configs = button_configs or FunctionButtonConfig.BUTTON_DEFINITIONS
        self.on_button_click = on_button_click
        self.columns_per_group = columns_per_group
        self.button_height = button_height
        self._button_map: Dict[str, ft.ElevatedButton] = {}

        self._build_buttons()
        grouped_buttons = self._group_buttons_by_category()

        content = ft.Column(
            controls=self._build_grouped_ui(grouped_buttons),
            spacing=15,
        )

        super().__init__(
            content=content,
            padding=10,
        )

    def _build_buttons(self):
        """构建所有按钮"""
        for config in self.button_configs:
            key = config['key']
            button = ft.ElevatedButton(
                text=config['name'],
                icon=config['icon'],
                on_click=lambda e, k=key: self.on_button_click(k) if self.on_button_click else None,
                style=ft.ButtonStyle(
                    padding=10,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                tooltip=config.get('description', ''),
            )
            self._button_map[key] = button

    def _group_buttons_by_category(self) -> Dict[FunctionButtonGroups, List[ft.ElevatedButton]]:
        """按分类分组按钮"""
        groups: Dict[FunctionButtonGroups, List[ft.ElevatedButton]] = {
            FunctionButtonGroups.EXTRACTION: [],
            FunctionButtonGroups.TRANSLATION: [],
            FunctionButtonGroups.BATCH_OPERATION: [],
            FunctionButtonGroups.MANAGEMENT: [],
        }

        for config in self.button_configs:
            key = config['key']
            group = config['group']
            if key in self._button_map and group in groups:
                groups[group].append(self._button_map[key])

        return groups

    def _build_grouped_ui(self, grouped_buttons: Dict) -> List[ft.Control]:
        """构建分组UI"""
        ui_elements = []

        for group in FunctionButtonGroups:
            buttons = grouped_buttons.get(group, [])
            if not buttons:
                continue

            cards = self._build_button_cards(buttons, self.columns_per_group)

            group_name, group_color, group_icon = group.value
            group_header = ft.Container(
                content=ft.Text(
                    f"{group_icon} {group_name}",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=group_color,
                ),
                padding=5,
            )

            group_card = ButtonGroupCard(
                group=group,
                buttons=cards,
                on_button_click=self.on_button_click,
            )

            ui_elements.extend([group_header, group_card])

        return ui_elements

    def _build_button_cards(self, buttons: List[ft.ElevatedButton], columns: int) -> List[ft.ElevatedButton]:
        """构建按钮网格"""
        return buttons

    def get_button(self, key: str) -> Optional[ft.ElevatedButton]:
        """获取指定key的按钮"""
        return self._button_map.get(key)

    def get_all_buttons(self) -> List[ft.ElevatedButton]:
        """获取所有按钮"""
        return list(self._button_map.values())

    def set_button_disabled(self, key: str, disabled: bool = True):
        """设置按钮禁用状态"""
        if key in self._button_map:
            self._button_map[key].disabled = disabled
            if self.page:
                self.update()

    def set_all_buttons_disabled(self, disabled: bool = True):
        """设置所有按钮禁用状态"""
        for button in self._button_map.values():
            button.disabled = disabled
        if hasattr(self, 'page') and self.page:
            self.update()
