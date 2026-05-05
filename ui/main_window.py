"""
Minecraft 基岩版汉化工具 - Flet 现代化 UI 版本

基于旧版 PyQt UI 完全重构
特性：
- 现代化设计
- 响应式布局
- 完整的功能实现
- 翻译进度条
- 剩余翻译条数和时间显示
- 暗夜模式
"""

from core.log_manager import init_logger, get_logger, get_log_manager
from core.container import build_app_container
from ui import dialogs
from ui import tabs
from ui.utils import ProgressThrottler
from ui.background_task_service import BackgroundTaskService
from ui.function_handlers import FunctionHandlers
from ui.window import WindowManager
from ui.components import FolderSelector, ProgressDisplay, StatusBar
from ui.dialog_manager import DialogManager
from ui.function_button_handler import FunctionButtonHandler
from ui.ui_coordinator import UICoordinator
import flet as ft
import sys
import os
import asyncio
import yaml
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 导入日志管理模块

# 初始化日志系统
init_logger()

# 获取logger
logger = get_logger(__name__)

# 全局异常处理


def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    import traceback
    error_msg = ''.join(traceback.format_exception(
        exc_type, exc_value, exc_traceback))
    logger.error(f"应用崩溃: {error_msg}")

    lm = get_log_manager()
    if lm:
        lm.mark_crash()


sys.excepthook = handle_exception


def _mark_interaction(event_type: str, description: str):
    """辅助函数：标记用户交互"""
    lm = get_log_manager()
    if lm:
        lm.mark_user_interaction(event_type, description)


class MinecraftTranslatorApp:
    """Minecraft 基岩版汉化翻译工具 - Flet 版本"""

    def __init__(self, page: ft.Page):
        """初始化应用"""
        self.page = page
        self.page.title = "🎮 Minecraft 基岩版汉化工具"

        # 日志存储（必须在 log() 调用前初始化）
        self.full_log_text = []
        self.terminal_text = []

        self._progress_throttler = ProgressThrottler(min_interval=0.1, significant_delta=0.05)

        # ========== 使用 WindowManager 初始化窗口 ==========
        self.window_manager = WindowManager(page, self.log)
        self.window_manager.initialize_window()
        self.window_manager.init_theme_colors()

        # 从 WindowManager 获取配置
        self.is_low_resolution = self.window_manager.is_low_resolution
        self.initial_window_size = self.window_manager.initial_window_size
        self.target_height = self.window_manager.target_height
        self.scale = self.window_manager.scale
        self.scale_x = self.window_manager.scale_x
        self.scale_y = self.window_manager.scale_y
        self.button_scale = self.window_manager.button_scale
        self.ui_scale = self.window_manager.ui_scale
        self.theme_colors = self.window_manager.theme_colors
        self.get_color = self.window_manager.get_theme_color

        # 添加窗口大小变化事件监听
        self.page.window.on_resize = self.window_manager.create_window_resize_handler()

        # ========== 移除旧版窗口配置（已由 WindowManager 处理）==========
        # 以下旧版配置代码已被移除：
        # - 屏幕检测和窗口大小计算（由 WindowManager.initialize_window() 处理）
        # - 窗口缩放比例计算（由 WindowManager._calculate_scale() 处理）
        # - 主题颜色初始化（由 WindowManager.init_theme_colors() 处理）
        # - 窗口大小变化处理（由 WindowManager.create_window_resize_handler() 处理）

        # 设置主题
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # 文件选择器使用 tkinter（避免 Flet FilePicker 在桌面模式下的兼容性问题）
        self._file_pickers_available = not getattr(self.page, 'web', False)
        logger.debug(f"文件选择器使用 tkinter，_file_pickers_available = {self._file_pickers_available}")

        # 初始化配置管理器
        container = build_app_container(
            log_callback=self.log,
            show_error=self.show_error_dialog,
            show_success=self.show_success_dialog,
        )
        self.config_manager = container.config_manager
        self.config = container.config
        self.api_manager = container.api_manager
        self.translator = container.translator
        self.file_handler = container.file_handler
        self.app_service = container.app_service
        
        # 向后兼容：保留functions引用，指向app_service
        self.functions = self.app_service
        
        # 🆕 初始化后台任务服务（线程安全的任务调度）
        max_workers_config = self.config.get('basic', {}).get('max_threads', 4)
        self.task_service = BackgroundTaskService(
            page=self.page, 
            max_workers=min(max_workers_config, 8)
        )
        self.log(f"✅ 后台任务服务已初始化，最大线程数: {self.task_service.executor._max_workers}")
        lm = get_log_manager()
        if lm:
            self.log(f"📁 日志文件目录: {lm.log_dir}")

        # 🆕 初始化UI协调器（统一管理UI协调和后台任务调度）
        self.ui_coordinator = UICoordinator(
            page=self.page,
            task_service=self.task_service,
            log_callback=self.log,
            show_error=self.show_error_dialog,
            show_success=self.show_success_dialog,
        )
        self.log("✅ UI协调器已初始化 (ui/ui_coordinator.py)")

        # 🆕 初始化功能事件处理器
        self.func_handlers = FunctionHandlers(self)
        self.log("✅ 功能事件处理器已加载 (ui/function_handlers.py)")

        # 🆕 初始化对话框管理器（统一管理所有对话框）
        self.dialog_manager = DialogManager(
            page=self.page,
            config_manager=self.config_manager,
            api_manager=self.api_manager,
            log_callback=self.log
        )
        self.log("✅ 对话框管理器已初始化 (ui/dialog_manager.py)")

        # 初始化 UI 组件占位符
        self.bp_path_label = ft.Text("未选择", color=ft.Colors.GREY)
        self.rp_path_label = ft.Text("未选择", color=ft.Colors.GREY)
        self.api_status_label = ft.Text("未检测", color=ft.Colors.GREY)

        # 文件夹路径
        self.bp_path = None
        self.rp_path = None

        # 选中的 API
        self.selected_api = None
        self.selected_api_type = None

        # 进度条相关
        self.progress_value = 0
        self.progress_text = ft.Text("就绪", size=self.ui_scale['body_size'])
        self.remaining_count = 0
        self.remaining_time = 0

        # 创建UI上下文，用于标签页模块
        self.ui_context = tabs.UIContext(
            page=self.page,
            ui_scale=self.ui_scale,
            scale=self.scale,
            theme_colors=self.theme_colors,
            callbacks={
                'toggle_dark_mode': self.toggle_dark_mode,
                'get_function_buttons_config': self.config_manager.get_function_buttons_config,
                'update_function_buttons_config': self.config_manager.update_function_buttons_config,
                'get_author_text': lambda: "作者：CAIMEO，BILIBILI UID：288374519",
            }
        )

        self.build_ui()

        _mark_interaction("app_startup", f"应用程序启动完成 (版本: Minecraft基岩版汉化工具)")
        self.log("🚀 应用程序启动完成 - 详细调试模式已启用")
        self.log(f"🎮 Minecraft基岩版汉化工具 - 全功能详细日志记录已开启")
        self.log(f"📁 工作目录: {os.getcwd()}")
        self.log(f"🔧 日志级别: DEBUG")
        self.log(f"👤 所有用户操作将被详细记录")

        # 确保窗口前置并获得焦点
        try:
            self.page.bring_to_front()
        except Exception as ex:
            logger.debug(f"窗口前置功能不可用: {ex}")

        # 显示启动动画并在后台线程中检测API
        self.show_startup_animation()

    def show_startup_animation(self):
        """显示启动动画并在后台检测API（使用任务服务）"""
        def startup_task():
            import time

            animation_duration = self.config.get('ui', {}).get(
                'startup_animation_duration', 0.8)

            if animation_duration <= 0:
                self.task_service.schedule_on_main_thread(
                    self.update_progress, 0.3, "正在检测API...", 0, 0)
                self.detect_apis()
                self.task_service.schedule_on_main_thread(
                    self.update_progress, 1.0, "就绪", 0, 0)
                return

            init_duration = animation_duration * 0.25
            modules_duration = animation_duration * 0.25
            api_duration = animation_duration * 0.5

            self.task_service.schedule_on_main_thread(
                self.update_progress, 0.2, "正在初始化应用...", 0, 0)
            time.sleep(init_duration)

            self.task_service.schedule_on_main_thread(
                self.update_progress, 0.4, "正在加载核心模块...", 0, 0)
            time.sleep(modules_duration)

            self.task_service.schedule_on_main_thread(
                self.update_progress, 0.6, "正在检测API...", 0, 0)

            self.detect_apis()
            time.sleep(api_duration)

            self.task_service.schedule_on_main_thread(
                self.update_progress, 1.0, "就绪", 0, 0)

        # 使用任务服务执行后台任务
        self.task_service.run(startup_task)

    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.full_log_text.append(log_entry)
        logger.info(message)
    
    def run_background_task(self, task_func, *args, **kwargs):
        """安全地运行后台任务（线程安全包装）
        
        Args:
            task_func: 后台任务函数
            *args: 函数参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象
        """
        self.disable_all_buttons()
        
        return self.task_service.run_with_ui_callbacks(
            task_func,
            *args,
            on_progress=kwargs.get('on_progress'),
            on_log=kwargs.get('on_log'),
            on_result=kwargs.get('on_result'),
            on_error=kwargs.get('on_error'),
            on_complete=self.enable_all_buttons,
        )

    def build_ui(self):
        s = self.ui_scale

        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("Minecraft 基岩版汉化工具", size=s['title_size'], weight=ft.FontWeight.BOLD, color=self.get_color('accent_text')),
                    ft.Text("现代化、易用、高效的翻译工具", size=s['subtitle_size'], color=self.get_color('text_secondary'))
                ], spacing=int(5 * self.scale), alignment=ft.MainAxisAlignment.CENTER),
                padding=int(20 * self.scale),
                bgcolor=self.get_color('primary_bg'),
                border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=s['border_radius'], bottom_right=s['border_radius'])
            )
        )

        tabs_control = ft.Tabs(
            selected_index=0,
            length=3,
            expand=True,
            content=ft.Column([
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="主功能"),
                        ft.Tab(label="配置"),
                        ft.Tab(label="日志"),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        self.create_main_tab(),
                        self.create_config_tab(),
                        self.create_log_tab(),
                    ]
                ),
            ])
        )
        self.page.add(tabs_control)

    def create_main_tab(self):
        """创建主功能标签页"""
        column = ft.Column([
            # 文件夹选择和 API 检测
            self.create_folder_and_api_section(),
            ft.Divider(height=10),

            # 功能按钮
            self.create_function_buttons(),
            ft.Divider(height=10),

            # 进度条和状态
            self.create_progress_section(),
            ft.Divider(height=10),

            self.create_status_bar(),
        ], scroll=ft.ScrollMode.AUTO, spacing=10)
        return column

    def create_folder_section(self):
        """创建文件夹选择区域（使用动态缩放 + 自适应文字）"""
        s = self.ui_scale
        return ft.Container(
            content=ft.Column([
                ft.Text("📁 文件夹选择", size=s['section_title_size'],
                        weight=ft.FontWeight.BOLD, color=self.get_color('text_primary')),
                ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Text("BP 文件夹:",
                                    weight=ft.FontWeight.BOLD,
                                    no_wrap=True,
                                    size=s['body_size'],
                                    color=self.get_color('text_primary')),
                            self.bp_path_label,
                            ft.ElevatedButton(
                                "选择",
                                icon=ft.Icons.FOLDER,
                                on_click=self.on_select_bp_folder,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            ft.Text("RP 文件夹:",
                                    weight=ft.FontWeight.BOLD,
                                    no_wrap=True,
                                    size=s['body_size'],
                                    color=self.get_color('text_primary')),
                            self.rp_path_label,
                            ft.ElevatedButton(
                                "选择",
                                icon=ft.Icons.FOLDER,
                                on_click=self.on_select_rp_folder,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], expand=True),
                ]),
            ]),
            padding=s['padding'],
            bgcolor=self.get_color('primary_bg'),
            border_radius=s['border_radius'],
        )

    def create_folder_and_api_section(self):
        """创建文件夹选择和 API 检测区域（使用动态缩放）"""
        s = self.ui_scale
        return ft.Container(
            content=ft.Row([
                # 左侧：文件夹选择（占4份）
                ft.Column([
                    self.create_folder_section(),
                ], expand=4, spacing=int(10 * self.scale)),

                # 右侧：API 检测（占3份）
                ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🔌 API 检测", size=s['section_title_size'], weight=ft.FontWeight.BOLD, color=self.get_color(
                                'text_primary')),
                            ft.ElevatedButton(
                                "检测可用 API",
                                icon=ft.Icons.SEARCH,
                                on_click=self.detect_apis,
                                ref=lambda e: setattr(
                                    self, 'api_detect_button', e),
                            ),
                            ft.Divider(height=int(10 * self.scale)),
                            self.api_status_label,
                        ]),
                        padding=s['padding'],
                        bgcolor=self.get_color('primary_bg'),
                        border_radius=s['border_radius'],
                    ),
                ], expand=3, spacing=int(10 * self.scale)),
            ], spacing=int(20 * self.scale)),
        )

    def create_function_buttons(self):
        """创建功能按钮区域（使用动态缩放 + 2K下1.2倍放大 + 文件夹检查） - 调用tabs模块"""
        callbacks = {
            'on_extract_only': self.func_handlers.on_extract_only,
            'on_extract_and_translate': self.func_handlers.on_extract_and_translate,
            'replace_display_names': self.func_handlers.replace_display_names,
            'one_click_service': self.func_handlers.on_one_click_service,
            'remove_value_for_specified_folder': self.func_handlers.on_batch_delete_value,
            'restore_value_for_specified_folder': self.func_handlers.on_batch_restore_value,
            'translate_lang_file': self.func_handlers.on_translate_lang_file,
            'process_guidebook_js': self.process_guidebook_js,
            'extract_entity_display_names': self.func_handlers.on_adapt_entity_display_names,
            'script_hardcode_translation': self.script_hardcode_translation,
            'on_backup_management': self.func_handlers.on_backup_management,
            'translate_mcstructure': self.func_handlers.on_translate_mcstructure,
        }
        
        # 调用tabs模块创建功能按钮
        container, button_dict, function_buttons = tabs.create_function_buttons(
            context=self.ui_context,
            callbacks=callbacks
        )
        
        # 存储按钮引用到实例属性
        self.btn_extract_only = button_dict.get('extract_only')
        self.btn_extract_translate = button_dict.get('extract_and_translate')
        self.btn_replace_display = button_dict.get('replace_display_names')
        self.btn_one_click = button_dict.get('one_click_service')
        self.btn_remove_value = button_dict.get('batch_delete_value')
        self.btn_restore_value = button_dict.get('batch_restore_value')
        self.btn_translate_lang = button_dict.get('translate_lang_file')
        self.btn_guidebook = button_dict.get('translate_single_js_file')
        self.btn_entity = button_dict.get('adapt_entity_display_names')
        self.btn_script_hardcode = button_dict.get('script_hardcode_translation')
        self.btn_backup_management = button_dict.get('backup_management')
        self.btn_mcstructure = button_dict.get('translate_mcstructure')
        
        self.function_buttons = function_buttons
        
        self.ui_coordinator.register_function_buttons(function_buttons)
        
        return container

    def disable_all_buttons(self, disabled=True):
        """禁用或启用所有功能按钮 - 委托给UICoordinator"""
        self.ui_coordinator.disable_all_buttons(disabled)

    def enable_all_buttons(self):
        """启用所有功能按钮 - 委托给UICoordinator"""
        self.ui_coordinator.enable_all_buttons()

    def create_progress_section(self):
        """创建进度条和状态显示区域（使用动态缩放） - 调用tabs模块"""
        container, progress_bar = tabs.create_progress_section(
            context=self.ui_context,
            progress_text=self.progress_text
        )
        
        self.progress_bar = progress_bar
        
        self.ui_coordinator.register_progress_controls(progress_bar, self.progress_text)
        
        return container

    def create_status_bar(self):
        """创建状态栏（使用动态缩放） - 调用tabs模块"""
        return tabs.create_status_bar(self.ui_context)

    def create_config_tab(self):
        """创建配置标签页 - 调用tabs模块"""
        callbacks = {
            'save_config': self.save_config,
            'restore_default_config': self.restore_default_config,
            'show_error_dialog': dialogs.show_error_dialog,
            'show_success_dialog': dialogs.show_success_dialog,
            'log': self.log,
            'show_add_api_dialog': self.show_add_api_dialog,
            'get_api_list': self.get_api_list,
            'show_import_export_dialog': self.show_import_export_dialog,
            'enable_all_apis': self.enable_all_apis,
            'disable_all_apis': self.disable_all_apis,
            'get_function_buttons_config': self.config_manager.get_function_buttons_config,
            'update_function_buttons_config': self.config_manager.update_function_buttons_config,
        }

        result = tabs.create_config_tab(
            context=self.ui_context,
            config=self.config,
            callbacks=callbacks
        )
        return result

    def build_config_tab_content(self):
        """构建配置标签页内容（可刷新）"""
        # 调用create_config_tab方法（已模块化）
        return self.create_config_tab()

    def refresh_config_tab(self):
        """刷新配置标签页"""
        try:
            # 找到 Tabs 控件并重建整个配置标签页
            tabs_control = None

            # 查找 Tabs 控件
            for control in self.page.controls:
                if isinstance(control, ft.Tabs):
                    tabs_control = control
                    break

            if tabs_control:
                # 重新构建配置标签页内容
                new_config_content = self.build_config_tab_content()

                # 更新 TabBarView 中的第二个控件（配置标签页）
                if hasattr(tabs_control, 'content') and tabs_control.content:
                    tabbar_view = tabs_control.content.controls[1]
                    tabbar_view.controls[1] = new_config_content

                self.page.update()
                self.log("配置标签页已刷新")
            else:
                self.log("警告：未找到 Tabs 控件")
        except Exception as ex:
            self.log(f"刷新配置标签页失败: {str(ex)}")

    def create_log_tab(self):
        """创建日志标签页（使用动态缩放 + 内嵌日志窗口） - 调用tabs模块"""
        callbacks = {
            'show_log_in_page': self.show_log_in_page,
            'clear_log_display': self.clear_log_display,
        }

        container, log_display = tabs.create_log_tab(
            context=self.ui_context,
            callbacks=callbacks
        )

        self.log_display = log_display
        return container

    def show_log_in_page(self, e):
        """在页面内显示详细日志"""
        try:
            # 清空现有内容
            self.log_display.controls.clear()

            # 获取日志内容
            if not self.full_log_text:
                self.log_display.controls.append(
                    ft.Text("📝 暂无日志记录",
                            size=self.ui_scale['body_size'],
                            color=ft.Colors.GREY_500,
                            italic=True)
                )
            else:
                # 显示最近200条日志
                recent_logs = self.full_log_text[-200:]

                for log_entry in recent_logs:
                    # 根据日志类型设置不同颜色和图标
                    if "⚠️" in log_entry or "错误" in log_entry or "失败" in log_entry:
                        color = ft.Colors.RED_700
                        prefix = "❌"
                    elif "✅" in log_entry or "成功" in log_entry or "完成" in log_entry:
                        color = ft.Colors.GREEN_700
                        prefix = "✅"
                    elif "检测到" in log_entry or "已" in log_entry:
                        color = ft.Colors.BLUE_700
                        prefix = "ℹ️"
                    else:
                        color = ft.Colors.BLACK
                        prefix = "•"

                    self.log_display.controls.append(
                        ft.Text(f"{prefix} {log_entry}",
                                size=self.ui_scale['small_size'],
                                color=color,
                                font_family="Consolas")
                    )

            # 滚动到底部（异步方法需要通过 run_task 调用）
            if self.page:
                self.page.run_task(self._scroll_log_to_bottom)
                self.page.update()

            self.log(f"已在页面内显示 {len(self.full_log_text)} 条日志记录")
        except Exception as ex:
            self.log(f"显示日志失败: {str(ex)}")

    async def _scroll_log_to_bottom(self):
        """异步滚动日志到底部"""
        try:
            await self.log_display.scroll_to(offset=-1, duration=200)
        except Exception:
            pass

    def clear_log_display(self, e):
        """清空日志显示"""
        try:
            self.log_display.controls.clear()
            self.log_display.controls.append(
                ft.Text("📝 日志已清空",
                        size=self.ui_scale['body_size'],
                        color=ft.Colors.GREY_500,
                        italic=True)
            )
            self.page.update()
            self.log("日志显示已清空")
        except Exception as ex:
            self.log(f"清空日志失败: {str(ex)}")

    def get_api_list(self):
        """获取 API 列表显示"""
        apis = []
        for api_type in ['zhipu', 'deepseek', 'qwen', 'doubao', 'local_ollama', 'openai', 'azure_openai', 'baidu_ernie', 'iflytek_spark', 'google_gemini']:
            if api_type in self.config:
                apis.extend([(api, api_type) for api in self.config[api_type]])

        if not apis:
            return ft.Text("暂无配置的 API", color=ft.Colors.GREY, italic=True)

        # 创建 API 条目（用于2列显示）
        api_items = []
        for api, api_type in apis:
            api_type_name = {
                'zhipu': '智谱',
                'deepseek': 'DeepSeek',
                'qwen': '通义千问',
                'doubao': '豆包',
                'local_ollama': '本地 Ollama',
                'openai': 'OpenAI',
                'azure_openai': 'Azure OpenAI',
                'baidu_ernie': '百度文心一言',
                'iflytek_spark': '讯飞星火',
                'google_gemini': 'Google Gemini'
            }.get(api_type, api_type)

            # 创建一个容器来显示每个 API 条目
            api_item = ft.Container(
                content=ft.Column([
                    ft.Text(f"{api.get('name', '未命名')} ({api_type_name})",
                            weight=ft.FontWeight.BOLD,
                            size=self.ui_scale['body_size'],
                            no_wrap=True),
                    ft.Text(f"模型：{api.get('model', '未知')}",
                            size=self.ui_scale['small_size'],
                            color=ft.Colors.GREY_600),
                    ft.Row([
                        ft.TextButton(
                            "编辑",
                            icon=ft.Icons.EDIT,
                            on_click=lambda e, api=api, api_type=api_type: self.edit_api(
                                api, api_type),
                        ),
                        ft.TextButton(
                            "删除",
                            icon=ft.Icons.DELETE,
                            on_click=lambda e, api=api, api_type=api_type: self.delete_api(
                                api, api_type),
                        ),
                    ], spacing=int(5 * self.scale))
                ]),
                padding=int(10 * self.scale),
                bgcolor=self.get_color('card_bg'),
                border=ft.Border.all(1, self.get_color('border_color')),
                border_radius=self.ui_scale['border_radius'],
                margin=ft.Margin(0, int(5 * self.scale),
                                 0, int(5 * self.scale))
            )
            api_items.append(api_item)

        # 使用 GridView 实现2列布局
        return ft.GridView(
            controls=api_items,
            max_extent=int(380 * self.scale),  # 每列最大宽度
            child_aspect_ratio=1.5,  # 宽高比
            spacing=int(10 * self.scale),
            run_spacing=int(10 * self.scale),
            expand=True,
        )

    async def on_select_bp_folder(self, e):
        """选择 BP 文件夹（使用tkinter）"""
        _mark_interaction("folder_select", "选择BP文件夹")

        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件夹选择，请使用桌面模式")
            return

        path = await asyncio.to_thread(self.file_handler.select_folder, "选择 BP 文件夹")
        if path:
            self.bp_path = path
            folder_name = os.path.basename(path)
            self.bp_path_label.value = folder_name
            self.bp_path_label.color = ft.Colors.GREEN
            self.page.update()
            self.log(f"已选择 BP 文件夹：{path}")
            self.update_function_buttons_state()

    async def on_select_rp_folder(self, e):
        """选择 RP 文件夹（使用tkinter）"""
        _mark_interaction("folder_select", "选择RP文件夹")

        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件夹选择，请使用桌面模式")
            return

        path = await asyncio.to_thread(self.file_handler.select_folder, "选择 RP 文件夹")
        if path:
            self.rp_path = path
            folder_name = os.path.basename(path)
            self.rp_path_label.value = folder_name
            self.rp_path_label.color = ft.Colors.GREEN
            self.page.update()
            self.log(f"已选择 RP 文件夹：{path}")
            self.update_function_buttons_state()

    def _check_api_available(self) -> bool:
        """检查是否有可用的API，返回True表示可用"""
        if not hasattr(self, 'api_manager') or not self.api_manager:
            return False
        try:
            available_apis = self.api_manager.get_available_apis()
            return len(available_apis) > 0
        except Exception as ex:
            self.log(f"检查API可用性失败: {str(ex)}")
            return False

    def _require_api(self, function_name: str) -> bool:
        """检查API是否可用，不可用则弹出错误对话框并返回False"""
        if self._check_api_available():
            return True
        self.show_error_dialog("错误", f"{function_name}需要使用AI翻译功能，但未检测到可用API。\n\n请先在配置中添加API后重试。")
        return False

    def update_function_buttons_state(self):
        """根据文件夹选择状态更新功能按钮的启用/禁用状态"""
        try:
            # 检查是否同时选择了BP和RP文件夹
            both_selected = (self.bp_path is not None and
                             self.rp_path is not None)

            # 更新所有功能按钮状态
            if hasattr(self, 'function_buttons'):
                for btn in self.function_buttons:
                    btn.disabled = not both_selected

                # 刷新页面显示
                self.page.update()

                if both_selected:
                    self.log("✅ 已选择 BP 和 RP 文件夹，功能按钮已启用")
                else:
                    missing = []
                    if not self.bp_path:
                        missing.append("BP")
                    if not self.rp_path:
                        missing.append("RP")
                    self.log(f"⚠️ 请先选择 {', '.join(missing)} 文件夹以启用功能按钮")
        except Exception as ex:
            self.log(f"更新按钮状态失败: {str(ex)}")

    def detect_apis(self, e=None):
        """检测可用 API"""
        self.log("正在检测 API...")

        # 直接使用属性引用（如果存在）
        if hasattr(self, 'api_detect_button') and self.api_detect_button:
            self.api_detect_button.disabled = True
            self.api_detect_button.text = "检测中..."

        # 更新状态标签
        self.api_status_label.value = "正在检测..."
        self.api_status_label.color = ft.Colors.BLUE_400

        # 立即更新界面
        self.page.update()

        # 更新进度条为API检测状态
        async def update_progress_api():
            self.update_progress(0.6, "正在检测API...", 0, 0)
        self.page.run_task(update_progress_api)

        try:
            available_apis = self.api_manager.detect_available_apis()
            if available_apis:
                self.api_status_label.value = f"检测到 {len(available_apis)} 个可用 API"
                self.api_status_label.color = ft.Colors.GREEN_400
                self.log(f"检测到 {len(available_apis)} 个可用 API")
                # 更新最大线程数
                auto_threads = len(available_apis) * 3
                if 'basic' in self.config:
                    self.config['basic']['max_workers'] = auto_threads
            else:
                self.api_status_label.value = "未检测到可用 API"
                self.api_status_label.color = ft.Colors.RED_400
                self.log("未检测到可用 API，请检查配置")
        except Exception as ex:
            self.api_status_label.value = f"检测失败: {str(ex)}"
            self.api_status_label.color = ft.Colors.RED_400
            self.log(f"API 检测失败: {str(ex)}")
        finally:
            # 恢复按钮状态
            if hasattr(self, 'api_detect_button') and self.api_detect_button:
                self.api_detect_button.disabled = False
                self.api_detect_button.text = "检测可用 API"

            # 重置进度条
            async def reset_progress():
                self.update_progress(0, "", 0, 0)
            self.page.run_task(reset_progress)

        # 最终更新界面
        self.page.update()

    def update_progress(self, value, text, remaining_count, remaining_time):
        """更新进度条和文本 - 委托给UICoordinator"""
        self.ui_coordinator.update_progress(value, text, remaining_count, remaining_time)

    # ── 统一后台任务调度 ──

    def _run_feature_task(self, method_name: str, log_prefix: str, feature_tag: str, **extra_kwargs):
        """统一后台任务调度 — 自动管理按钮状态、进度、日志"""
        _mark_interaction("button_click", feature_tag)
        self.log(f"🚀 {log_prefix}")

        def task_fn(progress_callback, log_callback):
            return getattr(self.functions, method_name)(
                bp_path=self.bp_path, rp_path=self.rp_path,
                progress_callback=progress_callback, log_callback=log_callback,
                **extra_kwargs,
            )

        self.task_service.run_with_button_state(
            task_fn,
            disabled_controls=self.function_buttons,
            on_progress=lambda v, r, t: self.update_progress(
                v, f"{log_prefix} {int(v*100)}%" if v < 1 else "完成", r, t),
            on_log=lambda msg: self.log(msg),
            on_result=self._handle_feature_result,
            on_error=self._handle_feature_error,
        )

    def _handle_feature_result(self, result):
        async def _show():
            if result.get('success'):
                self.update_progress(1.0, result.get('message', ''), 0, 0)
                self.show_success_dialog("成功", result.get('message', ''))
                self.log(f"✅ {result.get('message', '')}")
            else:
                self.show_error_dialog("错误", result.get('message', ''))
                self.log(f"❌ {result.get('message', '')}")
        self.page.run_task(_show)

    def _handle_feature_error(self, error):
        async def _show():
            self.log(f"❌ 操作失败: {error}")
            self.show_error_dialog("操作失败", str(error))
        self.page.run_task(_show)

    def on_extract_only(self, e):
        """[1] 仅提取汉化 key - 调用独立功能模块"""
        # 标记用户交互
        _mark_interaction("button_click", "功能1: 仅提取汉化 key")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能1"):
            return

        self.log("🚀 [功能1] 开始提取汉化 key...")

        try:
            import threading

            def extract_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        async def update_progress_task():
                            self.update_progress(value,
                                                 f"提取中... {int(value*100)}%" if value < 1 else "提取完成", remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.extract_only(
                            bp_path=self.bp_path,
                            rp_path=self.rp_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"提取过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        async def update_progress_success_task():
                            self.update_progress(1.0, result['message'], 0, 0)
                        self.page.run_task(update_progress_success_task)

                        async def show_success_dialog_task():
                            self.show_success_dialog("成功", result['message'])
                        self.page.run_task(show_success_dialog_task)

                        async def log_success_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_success_task)
                    else:
                        async def show_error_dialog_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_dialog_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "提取失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=extract_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "提取失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    def on_extract_and_translate(self, e):
        """[2] 提取+AI翻译 - 调用独立功能模块"""
        # 标记用户交互
        _mark_interaction("button_click", "功能2: 提取+AI翻译")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能2"):
            return

        self.log("🚀 [功能2] 开始提取并翻译...")

        try:
            import threading

            def translation_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        # 所有进度值都是浮点数 (0.0-1.0)
                        progress_value = value
                        if value < 1:
                            text = f"翻译中... {int(value*100)}%"
                        else:
                            text = "翻译完成"

                        async def update_progress_task():
                            self.update_progress(
                                progress_value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.extract_and_translate(
                            bp_path=self.bp_path,
                            rp_path=self.rp_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"翻译过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        async def update_progress_success_task():
                            self.update_progress(1.0, result['message'], 0, 0)
                        self.page.run_task(update_progress_success_task)

                        async def show_success_dialog_task():
                            self.show_success_dialog("成功", result['message'])
                        self.page.run_task(show_success_dialog_task)

                        async def log_success_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_success_task)
                    else:
                        async def show_error_dialog_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_dialog_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "操作失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动翻译线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=translation_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "操作失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    def replace_display_names(self, e):
        """[3] 全 BP 替换 display_name"""
        # 标记用户交互
        _mark_interaction("button_click", "功能3: 全BP替换display_name")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能3"):
            return

        self.log("🚀 [功能3] 开始替换 display_name...")

        try:
            import threading

            def replace_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        text = f"替换中... {int(value*100)}%" if value < 1 else "替换完成"

                        async def update_progress_task():
                            self.update_progress(
                                value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.replace_display_names(
                            bp_path=self.bp_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"替换过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        msg = f"{result['message']}\n原文件夹已备份至:\n{result['backup_path']}"

                        async def update_progress_success_task():
                            self.update_progress(1.0, result['message'], 0, 0)
                        self.page.run_task(update_progress_success_task)

                        async def show_success_dialog_task():
                            self.show_success_dialog("成功", msg)
                        self.page.run_task(show_success_dialog_task)

                        async def log_success_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_success_task)
                    else:
                        async def show_error_dialog_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_dialog_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "替换失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=replace_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "替换失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    def on_one_click_service(self, e):
        """[7] 一条龙服务"""
        # 标记用户交互
        _mark_interaction("button_click", "功能7: 一条龙服务")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能7"):
            return

        self.log("🚀 [功能7] 开始一条龙服务...")

        try:
            import threading

            def one_click_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        text = f"一条龙服务中... {int(value*100)}%" if value < 1 else "一条龙完成"

                        async def update_progress_task():
                            self.update_progress(
                                value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.one_click_service(
                            bp_path=self.bp_path,
                            rp_path=self.rp_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"一条龙服务过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        async def update_progress_task():
                            self.update_progress(
                                1.0, f"一条龙完成！{result['translate_count']}条", 0, 0)
                        self.page.run_task(update_progress_task)

                        async def show_success_task():
                            self.show_success_dialog("成功", result['message'])
                        self.page.run_task(show_success_task)

                        async def log_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_task)
                    else:
                        async def show_error_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "操作失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=one_click_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "操作失败", 0, 0)

    async def remove_value_for_specified_folder(self, e):
        """[4] 批量删除 value - 调用独立功能模块"""
        # 标记用户交互
        _mark_interaction("button_click", "功能4: 批量删除value")

        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return

        # 检查是否有可用的API
        if not self._require_api("功能4"):
            return

        def _select_folder():
            return self.file_handler.select_folder("选择文件夹")

        path = await asyncio.to_thread(_select_folder)
        if not path:
            return

        folder_path = path
        self.log(f"🚀 [功能4] 开始批量删除 value: {folder_path}")

        try:
            import threading

            def delete_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        text = f"删除中... {int(value*100)}%" if value < 1 else "删除完成"

                        async def update_progress_task():
                            self.update_progress(
                                value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.batch_delete_value(
                            folder_path=folder_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"删除过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        msg = f"{result['message']}\n原文件夹已备份至:\n{result['backup_path']}"

                        async def update_progress_success_task():
                            self.update_progress(
                                1.0, f"删除完成：{result['success_count']}/{result['total']}", 0, 0)
                        self.page.run_task(update_progress_success_task)

                        async def show_success_dialog_task():
                            self.show_success_dialog("成功", msg)
                        self.page.run_task(show_success_dialog_task)

                        async def log_success_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_success_task)
                    else:
                        async def show_error_dialog_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_dialog_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "删除失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=delete_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "删除失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    async def restore_value_for_specified_folder(self, e):
        """[5] 批量还原 value - 调用独立功能模块"""
        # 标记用户交互
        _mark_interaction("button_click", "功能5: 批量还原value")

        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return

        # 检查是否有可用的API
        if not self._require_api("功能5"):
            return

        def _select_folder():
            return self.file_handler.select_folder("选择文件夹")

        path = await asyncio.to_thread(_select_folder)
        if not path:
            return

        folder_path = path
        self.log(f"🚀 [功能5] 开始批量还原 value: {folder_path}")

        try:
            import threading

            def restore_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        text = f"还原中... {int(value*100)}%" if value < 1 else "还原完成"

                        async def update_progress_task():
                            self.update_progress(
                                value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.batch_restore_value(
                            folder_path=folder_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"还原过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        msg = f"{result['message']}\n原文件夹已备份至:\n{result['backup_path']}"

                        async def update_progress_success_task():
                            self.update_progress(
                                1.0, f"还原完成：{result['success_count']}/{result['total']}", 0, 0)
                        self.page.run_task(update_progress_success_task)

                        async def show_success_dialog_task():
                            self.show_success_dialog("成功", msg)
                        self.page.run_task(show_success_dialog_task)

                        async def log_success_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_success_task)
                    else:
                        async def show_error_dialog_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_dialog_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "还原失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=restore_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "还原失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    async def translate_lang_file(self, e):
        """[6] 翻译独立的.lang 文件 - 使用tkinter"""
        # 标记用户交互
        _mark_interaction("button_click", "功能6: 翻译独立的.lang文件")

        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return

        # 检查是否有可用的API
        if not self._require_api("功能6"):
            return

        def _select_file():
            return self.file_handler.select_file("选择 lang 文件", [("lang文件", "*.lang")])

        lang_file = await asyncio.to_thread(_select_file)

        if not lang_file:
            return

        self.log(f"🚀 [功能6] 开始翻译 lang 文件: {lang_file}")

        try:
            import threading

            def translate_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        # 所有进度值都是浮点数 (0.0-1.0)
                        progress_value = value
                        if value < 1:
                            text = f"翻译中... {int(value*100)}%"
                        else:
                            text = "翻译完成"

                        async def update_progress_task():
                            self.update_progress(
                                progress_value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.translate_lang_file(
                            lang_file_path=lang_file,
                            bp_path=self.bp_path,
                            rp_path=self.rp_path,
                            progress_callback=progress_callback,
                            log_callback=log_callback
                        )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"翻译过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        output_info = "\n".join(
                            result['output_paths']) if result['output_paths'] else "（未指定输出目录）"
                        msg = f"{result['message']}\n输出路径:\n{output_info}"

                        async def update_progress_success_task():
                            self.update_progress(1.0, result['message'], 0, 0)
                        self.page.run_task(update_progress_success_task)

                        async def show_success_dialog_task():
                            self.show_success_dialog("成功", msg)
                        self.page.run_task(show_success_dialog_task)

                        async def log_success_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_success_task)
                    else:
                        async def show_error_dialog_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_dialog_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "翻译失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=translate_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "翻译失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    async def process_guidebook_js(self, e):
        """[9] 翻译单个 JS 文件（AST+AI 智能翻译）"""
        # 标记用户交互
        _mark_interaction("button_click", "功能9: 翻译单个JS文件")

        if not self._file_pickers_available:
            self.show_error_dialog("浏览器模式不支持文件选择，请使用桌面模式")
            return

        # 检查是否有可用的API
        if not self._require_api("功能9"):
            return

        def _select_file():
            return self.file_handler.select_file("选择 JS 文件", [("JS文件", "*.js")])

        js_file = await asyncio.to_thread(_select_file)

        if not js_file:
            return

        self.log(f"🚀 [功能9] 开始翻译 JS 文件: {js_file}")

        def mode1(e):
            self.page.pop_dialog()
            # 使用新的预览对话框
            self.show_js_translation_preview_dialog([js_file], mode=1, bp_path=self.bp_path)

        def mode2(e):
            self.page.pop_dialog()
            # 使用新的预览对话框
            self.show_js_translation_preview_dialog([js_file], mode=2, bp_path=self.bp_path)

        def cancel(e):
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text("🔧 翻译模式选择"),
            content=ft.Column([
                ft.Text("请选择翻译模式:", size=14),
                ft.Divider(height=10),
                ft.Text("模式1: 只翻译包含§颜色代码的字符串（最安全）", size=12),
                ft.Text("模式2: AI 智能判断并翻译所有玩家可见文本", size=12),
                ft.Divider(height=10),
                ft.Text("📝 注意: 现在会先显示预览对话框，确认后再执行翻译", size=11, color=ft.Colors.GREEN),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("模式1", on_click=mode1),
                ft.TextButton("模式2", on_click=mode2),
                ft.TextButton("取消", on_click=cancel),
            ],
        )
        self.page.show_dialog(dialog)


    def _execute_single_js_translation(self, js_file, mode):
        import threading

        def translation_task():
            try:
                def progress_callback(value, remaining_count=0, remaining_time=0):
                    text = f"翻译中... {int(value*100)}%" if value < 1 else "翻译完成"
                    async def update():
                        self.update_progress(value, text, remaining_count, remaining_time)
                    self.page.run_task(update)

                def log_callback(msg):
                    async def update():
                        self.log(msg)
                    self.page.run_task(update)

                self.disable_all_buttons()
                result = self.functions.translate_single_js_file(
                    js_file_path=js_file,
                    mode=mode,
                    progress_callback=progress_callback,
                    log_callback=log_callback
                )
                if result.get('success'):
                    # 如果翻译数量为0，显示提示而非错误
                    if result.get('translated_files') and len(result.get('translated_files', [])) == 0:
                        msg = "该文件中没有找到需要翻译的字符串（可能已汉化或无文本）"
                    else:
                        msg = result.get('message', '翻译完成')
                    async def show_success():
                        self.show_success_dialog("翻译完成", msg)
                    self.page.run_task(show_success)
                else:
                    async def show_error():
                        self.show_error_dialog("翻译失败", result.get('message', '未知错误'))
                    self.page.run_task(show_error)
            except Exception as ex:
                error_msg = str(ex)
                async def show_error():
                    self.show_error_dialog("错误", error_msg)
                self.page.run_task(show_error)
            finally:
                self.enable_all_buttons()

        thread = threading.Thread(target=translation_task, daemon=True)
        thread.start()




    def extract_entity_display_names(self, e):
        """[8] 高亮实体信息显示名称适配 - 调用独立功能模块"""
        # 标记用户交互
        _mark_interaction("button_click", "功能8: 高亮实体信息显示名称适配")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能8"):
            return

        self.log("🚀 [功能8] 开始提取实体显示名称...")

        try:
            import threading

            def entity_task():
                try:
                    # 定义进度回调
                    def progress_callback(value, remaining_count=0, remaining_time=0):
                        text = f"适配中... {int(value*100)}%" if value < 1 else "适配完成"

                        async def update_progress_task():
                            self.update_progress(
                                value, text, remaining_count, remaining_time)
                        self.page.run_task(update_progress_task)

                    # 定义日志回调
                    def log_callback(msg):
                        async def log_task():
                            self.log(msg)
                        self.page.run_task(log_task)

                    # 调用独立功能模块
                    try:
                        result = self.functions.extract_entity_display_names(
                    bp_path=self.bp_path,
                    rp_path=self.rp_path,
                    progress_callback=progress_callback,
                    log_callback=log_callback
                )
                    except Exception as ex:
                        # 捕获函数调用异常，转换为错误结果
                        result = {'success': False,
                                  'message': f"适配过程出错: {str(ex)}"}

                    # 处理结果
                    if result['success']:
                        # 显示预览信息
                        preview_text = "\n".join(
                            [f"   {p['key']}" for p in result.get('preview', [])])
                        msg = f"{result['message']}\n\n预览（前5条）：\n{preview_text}"

                        async def update_progress_task():
                            self.update_progress(
                                1.0, f"适配完成！{result['count']}条", 0, 0)
                        self.page.run_task(update_progress_task)

                        async def show_success_task():
                            self.show_success_dialog("成功", msg)
                        self.page.run_task(show_success_task)

                        async def log_task():
                            self.log(f"✅ {result['message']}")
                        self.page.run_task(log_task)
                    else:
                        async def show_error_task():
                            self.show_error_dialog("错误", result['message'])
                        self.page.run_task(show_error_task)

                        async def update_progress_fail_task():
                            self.update_progress(0, "操作失败", 0, 0)
                        self.page.run_task(update_progress_fail_task)
                finally:
                    # 无论成功失败，都重新启用按钮
                    self.enable_all_buttons()

            # 启动线程前禁用所有按钮
            self.disable_all_buttons()
            thread = threading.Thread(target=entity_task, daemon=True)
            thread.start()

        except Exception as ex:
            self.show_error_dialog("错误", str(ex))
            self.update_progress(0, "操作失败", 0, 0)
            self.enable_all_buttons()  # 确保按钮重新启用

    def generate_api_name(self, api_type, model):
        """自动生成 API 名称（类型_数字 或 类型_模型_数字）"""
        try:
            # 获取该类型下已有的 API 数量
            type_key_map = {
                "智谱": "zhipu",
                "DeepSeek": "deepseek",
                "通义千问": "qwen",
                "豆包": "doubao",
                "本地 Ollama": "local_ollama",
                "OpenAI": "openai",
                "Azure OpenAI": "azure_openai",
                "百度文心一言": "baidu_ernie",
                "讯飞星火": "iflytek_spark",
                "Google Gemini": "google_gemini",
            }

            type_key = type_key_map.get(api_type, "zhipu")

            if type_key in self.config:
                existing_count = len(self.config[type_key])
            else:
                existing_count = 0

            new_number = existing_count + 1

            # 如果模型为空，只生成：类型_数字
            if not model or model.strip() == "":
                return f"{api_type}_{new_number}"

            # 如果有模型，生成：类型_模型_数字
            return f"{api_type}_{model}_{new_number}"
        except Exception as ex:
            return f"{api_type}_1"

    def on_api_type_changed(self, e):
        """当 API 类型改变时的事件处理"""
        pass  # 这个方法会在 show_add_api_dialog 内部定义

    def show_add_api_dialog(self, e):
        """显示添加 API 对话框 - 调用dialogs模块"""
        # 准备回调函数字典
        callbacks = {
            'save_config': self.save_config,
            'show_error_dialog': dialogs.show_error_dialog,
            'show_success_dialog': dialogs.show_success_dialog,
            'log': self.log,
            'show_add_api_dialog': self.show_add_api_dialog,
            'get_api_list': self.get_api_list,
            'show_import_export_dialog': self.show_import_export_dialog,
            # 新增
            'enable_all_apis': self.enable_all_apis,
            'disable_all_apis': self.disable_all_apis,
            'refresh_config_tab': self.refresh_config_tab,
            'detect_apis': self.detect_apis,
        }
        
        # 使用实例方法作为生成API名称的函数
        # 注意：这里传递的是self.generate_api_name方法引用
        generate_api_name_func = self.generate_api_name
        
        # 调用dialogs模块显示添加API对话框
        dialogs.show_add_api_dialog(
            page=self.page,
            callbacks=callbacks,
            config=self.config,
            generate_api_name_func=generate_api_name_func
        )

    def edit_api(self, api, api_type):
        """编辑 API"""
        try:
            # 创建编辑表单
            name_field = ft.TextField(
                label="API 名称", value=api.get('name', ''), width=300)
            api_key_field = ft.TextField(label="API 密钥", value=api.get(
                'api_key', ''), password=True, can_reveal_password=True, width=300)
            model_field = ft.TextField(
                label="模型名称", value=api.get('model', ''), width=300)
            api_url_field = ft.TextField(
                label="API URL", value=api.get('api_url', ''), width=300)
            priority_field = ft.TextField(label="优先级", value=str(
                api.get('priority', 1)), width=300, keyboard_type=ft.KeyboardType.NUMBER)
            enabled_switch = ft.Switch(
                label="启用", value=api.get('enabled', True))

            def save_changes(e):
                """保存修改"""
                try:
                    api['name'] = name_field.value
                    api['api_key'] = api_key_field.value
                    api['model'] = model_field.value
                    api['api_url'] = api_url_field.value
                    api['priority'] = int(
                        priority_field.value) if priority_field.value.isdigit() else 1
                    api['enabled'] = enabled_switch.value

                    # 保存配置
                    self.save_config()

                    self.log(f"已编辑 API: {api['name']}")
                    self.page.pop_dialog()
                    self.refresh_config_tab()
                    self.show_success_dialog("成功", f"API '{api['name']}' 已更新")
                    
                    # 在后台检测API，不阻塞UI
                    import threading
                    def background_detect():
                        # 延迟一下，让UI先更新
                        import time
                        time.sleep(0.5)
                        self.detect_apis()
                    
                    # 启动后台线程
                    detect_thread = threading.Thread(target=background_detect, daemon=True)
                    detect_thread.start()
                    
                    self.page.update()
                except Exception as ex:
                    self.log(f"保存编辑失败: {str(ex)}")
                    self.show_error_dialog("错误", str(ex))

            def cancel(e):
                """取消编辑"""
                self.page.pop_dialog()

            # 创建对话框
            dialog = ft.AlertDialog(
                title=ft.Text("✏️ 编辑 API"),
                content=ft.Column([
                    name_field,
                    api_key_field,
                    model_field,
                    api_url_field,
                    priority_field,
                    enabled_switch,
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("取消", on_click=cancel),
                    ft.TextButton("保存", on_click=save_changes),
                ],
            )

            # 显示对话框
            self.page.show_dialog(dialog)
        except Exception as ex:
            self.log(f"打开编辑 API 对话框失败: {str(ex)}")
            self.show_error_dialog("错误", str(ex))

    def delete_api(self, api, api_type):
        """删除 API"""
        try:
            # 确认删除
            def confirm_delete(e):
                try:
                    if api_type in self.config:
                        api_list = self.config[api_type]
                        if api in api_list:
                            api_name = api.get('name', '未知')
                            api_list.remove(api)
                            # 保存配置到文件
                            self.save_config()
                            self.log(f"已删除 API: {api_name}")

                    # 关闭对话框
                    self.page.pop_dialog()
                    self.refresh_config_tab()
                    self.show_success_dialog(
                        "成功", f"API '{api.get('name', '未知')}' 已删除")

                    # 在后台检测API，不阻塞UI
                    import threading
                    def background_detect():
                        # 延迟一下，让UI先更新
                        import time
                        time.sleep(0.5)
                        self.detect_apis()
                    
                    # 启动后台线程
                    detect_thread = threading.Thread(target=background_detect, daemon=True)
                    detect_thread.start()

                    self.page.update()
                except Exception as ex:
                    self.log(f"删除 API 失败: {str(ex)}")
                    self.show_error_dialog("错误", str(ex))

            def cancel(e):
                """取消删除"""
                self.page.pop_dialog()

            # 创建对话框
            dialog = ft.AlertDialog(
                title=ft.Text("🗑️ 确认删除"),
                content=ft.Text("确定要删除此 API 吗？此操作不可恢复。"),
                actions=[
                    ft.TextButton("取消", on_click=cancel),
                    ft.TextButton("删除", on_click=confirm_delete),
                ],
            )

            # 显示对话框
            self.page.show_dialog(dialog)
        except Exception as ex:
            self.log(f"打开删除确认对话框失败: {str(ex)}")
            self.show_error_dialog("错误", str(ex))

    def save_config(self, e=None):
        """保存配置"""
        try:
            success = self.config_manager.save_config(self.config)
            if success:
                self.log("配置已保存")
            else:
                raise Exception("保存失败")
        except Exception as ex:
            self.show_error_dialog("保存失败", str(ex))

    def restore_default_config(self, e=None):
        """恢复默认配置（保留API密钥）"""
        try:
            restored = self.config_manager.restore_default_config(keep_api_keys=True)
            self.config = restored
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("✅ 已恢复默认配置（API密钥已保留）"), duration=3000)
            self.page.snack_bar.open = True
            self.page.update()
            self.log("已恢复默认配置（API密钥已保留）")
            return restored
        except Exception as ex:
            self.show_error_dialog("恢复失败", str(ex))
            return None

    def show_log_dialog(self, e=None):
        """显示日志对话框（包装器，调用dialogs模块）"""
        dialogs.show_log_dialog(self.page, self.full_log_text, "📋 操作日志")

    def show_terminal_dialog(self, e=None):
        """显示终端对话框（包装器，调用dialogs模块）"""
        dialogs.show_terminal_dialog(self.page, self.terminal_text, "💻 终端输出")

    def show_success_dialog(self, title, message):
        """显示成功对话框（包装器，调用dialogs模块）"""
        dialogs.show_success_dialog(self.page, title, message)

    def show_error_dialog(self, title, message):
        """显示错误对话框（用户友好版，包装器，调用dialogs模块）"""
        dialogs.show_error_dialog(self.page, title, message)

    def show_info_dialog(self, title, message):
        """显示信息对话框（包装器，调用dialogs模块）"""
        dialogs.show_info_dialog(self.page, title, message)

    def toggle_dark_mode(self, e=None):
        """切换暗夜模式（UIState快照 → 重建 → 恢复）"""
        saved_state = self._save_ui_state()

        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.log("已切换到暗夜模式")
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.log("已切换到日间模式")

        if hasattr(self, 'ui_context') and self.ui_context:
            self.ui_context.clear_color_cache()

        self.rebuild_ui_for_theme()
        self._restore_ui_state(saved_state)
        self.page.update()

    def _save_ui_state(self):
        """保存主题切换前的 UI 状态"""
        state = {}
        if hasattr(self, 'api_status_label') and self.api_status_label:
            state['api_status_value'] = self.api_status_label.value
            state['api_status_color'] = self.api_status_label.color
        if hasattr(self, 'bp_path_label') and self.bp_path_label:
            state['bp_label_value'] = self.bp_path_label.value
            state['bp_label_color'] = self.bp_path_label.color
        if hasattr(self, 'rp_path_label') and self.rp_path_label:
            state['rp_label_value'] = self.rp_path_label.value
            state['rp_label_color'] = self.rp_path_label.color
        if hasattr(self, 'bp_path'):
            state['bp_path'] = self.bp_path
        if hasattr(self, 'rp_path'):
            state['rp_path'] = self.rp_path
        return state

    def _restore_ui_state(self, state):
        """恢复主题切换后的 UI 状态"""
        if state.get('api_status_value') and hasattr(self, 'api_status_label'):
            self.api_status_label.value = state['api_status_value']
            self.api_status_label.color = state['api_status_color']
        if state.get('bp_label_value') and hasattr(self, 'bp_path_label'):
            self.bp_path_label.value = state['bp_label_value']
            self.bp_path_label.color = state['bp_label_color']
        if state.get('rp_label_value') and hasattr(self, 'rp_path_label'):
            self.rp_path_label.value = state['rp_label_value']
            self.rp_path_label.color = state['rp_label_color']
        if state.get('bp_path'):
            self.bp_path = state['bp_path']
        if state.get('rp_path'):
            self.rp_path = state['rp_path']
        if hasattr(self, 'update_function_buttons_state'):
            self.update_function_buttons_state()

    def rebuild_ui_for_theme(self):
        """重新构建UI以应用主题颜色"""
        try:
            self.page.controls.clear()
            self.build_ui()
            self.log("UI已根据新主题重新构建")
        except Exception as ex:
            self.log(f"重新构建UI失败: {str(ex)}")

    def show_backup_management_dialog(self, e=None):
        """显示备份文件管理对话框"""
        # 标记用户交互
        _mark_interaction("button_click", "功能11: 备份文件管理")
        
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能11"):
            return
        
        self.log("📂 正在扫描备份文件...")
        
        # 扫描备份文件
        import os
        import shutil
        from datetime import datetime
        
        backup_files = []
        
        # 扫描BP文件夹及其子文件夹中的.bak文件
        for root, dirs, files in os.walk(self.bp_path):
            for file in files:
                if file.endswith('.bak'):
                    backup_path = os.path.join(root, file)
                    original_path = backup_path[:-4]  # 移除.bak扩展名
                    
                    # 获取文件信息
                    try:
                        backup_size = os.path.getsize(backup_path)
                        backup_mtime = datetime.fromtimestamp(os.path.getsize(backup_path))
                        backup_mtime_str = backup_mtime.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 检查原始文件是否存在
                        original_exists = os.path.exists(original_path)
                        
                        backup_files.append({
                            'backup_path': backup_path,
                            'original_path': original_path,
                            'original_exists': original_exists,
                            'size': backup_size,
                            'modified': backup_mtime_str,
                            'filename': os.path.basename(backup_path),
                            'folder': os.path.relpath(root, self.bp_path)
                        })
                    except Exception as ex:
                        logger.debug(f"跳过无效备份文件 {backup_path}: {ex}")
                        continue
        
        if not backup_files:
            self.show_info_dialog("提示", f"在BP文件夹中未找到备份文件 (.bak)")
            return
        
        self.log(f"📊 找到 {len(backup_files)} 个备份文件")
        
        # 创建备份文件列表
        backup_list_items = []
        
        for i, backup in enumerate(backup_files):
            # 创建每行显示的内容
            status_color = ft.Colors.GREEN if backup['original_exists'] else ft.Colors.RED
            status_text = "原始文件存在" if backup['original_exists'] else "原始文件已删除"
            
            file_row = ft.Row([
                ft.Column([
                    ft.Text(f"{i+1}. {backup['filename']}", size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(f"位置: {backup['folder']}", size=11, color=ft.Colors.GREY),
                    ft.Text(f"状态: {status_text}", size=11, color=status_color),
                    ft.Text(f"大小: {backup['size']:,} bytes, 修改: {backup['modified']}", size=11, color=ft.Colors.GREY),
                ], expand=True),
                ft.Column([
                    ft.ElevatedButton("预览", 
                        on_click=lambda e, b=backup: self._preview_backup_file(b),
                        style=ft.ButtonStyle(color=ft.Colors.BLUE, bgcolor=ft.Colors.BLUE_50),
                        width=80
                    ),
                    ft.ElevatedButton("恢复", 
                        on_click=lambda e, b=backup: self._restore_backup_file(b),
                        style=ft.ButtonStyle(color=ft.Colors.GREEN, bgcolor=ft.Colors.GREEN_50),
                        width=80
                    ),
                    ft.ElevatedButton("删除", 
                        on_click=lambda e, b=backup: self._delete_backup_file(b),
                        style=ft.ButtonStyle(color=ft.Colors.RED, bgcolor=ft.Colors.RED_50),
                        width=80
                    ),
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            
            backup_list_items.append(file_row)
            backup_list_items.append(ft.Divider(height=5))
        
        # 移除最后一个分隔线
        if backup_list_items:
            backup_list_items.pop()
        
        # 创建对话框内容
        dialog_content = ft.Column([
            ft.Text(f"📂 备份文件管理 ({len(backup_files)} 个文件)", size=16, weight=ft.FontWeight.BOLD),
            ft.Text(f"BP文件夹: {self.bp_path}", size=12, color=ft.Colors.GREY),
            ft.Divider(height=10),
            ft.Container(
                content=ft.Column(backup_list_items, spacing=8, scroll=ft.ScrollMode.AUTO),
                height=400,
                padding=10,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=5,
            ),
            ft.Divider(height=10),
            ft.Text("操作说明:", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("• 预览: 查看备份文件内容", size=11, color=ft.Colors.GREY),
            ft.Text("• 恢复: 将备份文件还原为原始文件（覆盖）", size=11, color=ft.Colors.GREY),
            ft.Text("• 删除: 永久删除备份文件", size=11, color=ft.Colors.GREY),
            ft.Text("⚠️ 注意: 恢复操作会覆盖当前文件，请谨慎操作", size=11, color=ft.Colors.ORANGE),
        ], scroll=ft.ScrollMode.AUTO)
        
        def close_dialog(e):
            self.page.pop_dialog()
        
        # 创建对话框
        dialog = ft.AlertDialog(
            title=ft.Text("💾 备份文件管理"),
            content=dialog_content,
            actions=[
                ft.TextButton("刷新", on_click=lambda e: self._refresh_backup_dialog()),
                ft.TextButton("关闭", on_click=close_dialog),
            ],
        )
        
        # 保存对话框引用以便刷新
        self._backup_dialog = dialog
        
        # 显示对话框
        self.page.show_dialog(dialog)
    
    def _preview_backup_file(self, backup_info):
        """预览备份文件内容"""
        try:
            with open(backup_info['backup_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 限制预览内容长度
            preview_length = min(len(content), 2000)
            preview_content = content[:preview_length]
            if len(content) > preview_length:
                preview_content += f"\n\n... (文件过大，已截断，完整大小: {len(content):,} 字符)"
            
            # 显示预览对话框
            def close_preview(e):
                self.page.pop_dialog()
            
            preview_dialog = ft.AlertDialog(
                title=ft.Text(f"👁️ 预览备份文件: {backup_info['filename']}"),
                content=ft.Container(
                    content=ft.Text(preview_content, size=11, font_family="Consolas"),
                    height=400,
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                ),
                actions=[
                    ft.TextButton("关闭", on_click=close_preview),
                ],
            )
            
            self.page.show_dialog(preview_dialog)
            
        except Exception as ex:
            self.show_error_dialog("预览失败", str(ex))
    
    def _restore_backup_file(self, backup_info):
        """恢复备份文件"""
        # 确认对话框
        def confirm_restore(e):
            self.page.pop_dialog()
            self._execute_restore_backup(backup_info)
        
        def cancel_restore(e):
            self.page.pop_dialog()
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认恢复"),
            content=ft.Column([
                ft.Text(f"确定要恢复备份文件吗？", size=14),
                ft.Text(f"备份文件: {backup_info['filename']}", size=12, color=ft.Colors.GREY),
                ft.Text(f"原始文件: {os.path.basename(backup_info['original_path'])}", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("警告: 此操作将覆盖当前原始文件，且不可撤销！", size=12, color=ft.Colors.RED, weight=ft.FontWeight.BOLD),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=cancel_restore),
                ft.TextButton("确认恢复", on_click=confirm_restore, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        
        self.page.show_dialog(confirm_dialog)
    
    def _execute_restore_backup(self, backup_info):
        """执行备份恢复操作"""
        try:
            import shutil
            
            # 备份当前原始文件（如果存在）
            if os.path.exists(backup_info['original_path']):
                temp_backup = backup_info['original_path'] + '.temp.bak'
                shutil.copy2(backup_info['original_path'], temp_backup)
            
            # 恢复备份文件
            shutil.copy2(backup_info['backup_path'], backup_info['original_path'])
            
            self.log(f"✅ 已恢复备份文件: {backup_info['filename']} -> {os.path.basename(backup_info['original_path'])}")
            
            # 显示成功对话框
            def close_success(e):
                self.page.pop_dialog()
                # 刷新备份对话框
                if hasattr(self, '_backup_dialog'):
                    self.page.pop_dialog()
                    self.show_backup_management_dialog()
            
            success_dialog = ft.AlertDialog(
                title=ft.Text("✅ 恢复成功"),
                content=ft.Text(f"已成功恢复备份文件\n原始文件已更新"),
                actions=[
                    ft.TextButton("确定", on_click=close_success),
                ],
            )
            
            self.page.show_dialog(success_dialog)
            
        except Exception as ex:
            self.show_error_dialog("恢复失败", str(ex))
    
    def _delete_backup_file(self, backup_info):
        """删除备份文件"""
        # 确认对话框
        def confirm_delete(e):
            self.page.pop_dialog()
            self._execute_delete_backup(backup_info)
        
        def cancel_delete(e):
            self.page.pop_dialog()
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认删除"),
            content=ft.Column([
                ft.Text(f"确定要永久删除此备份文件吗？", size=14),
                ft.Text(f"文件: {backup_info['filename']}", size=12, color=ft.Colors.GREY),
                ft.Text(f"路径: {backup_info['folder']}", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("警告: 此操作不可撤销！", size=12, color=ft.Colors.RED),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=cancel_delete),
                ft.TextButton("确认删除", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        
        self.page.show_dialog(confirm_dialog)
    
    def _execute_delete_backup(self, backup_info):
        """执行备份文件删除"""
        try:
            os.remove(backup_info['backup_path'])
            
            self.log(f"🗑️ 已删除备份文件: {backup_info['filename']}")
            
            # 显示成功对话框
            def close_success(e):
                self.page.pop_dialog()
                # 刷新备份对话框
                if hasattr(self, '_backup_dialog'):
                    self.page.pop_dialog()
                    self.show_backup_management_dialog()
            
            success_dialog = ft.AlertDialog(
                title=ft.Text("✅ 删除成功"),
                content=ft.Text(f"已成功删除备份文件"),
                actions=[
                    ft.TextButton("确定", on_click=close_success),
                ],
            )
            
            self.page.show_dialog(success_dialog)
            
        except Exception as ex:
            self.show_error_dialog("删除失败", str(ex))

    def translate_mcstructure(self, e):
        """[12] mcstructure 汉化"""
        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            self.log("❌ [功能12] 请先选择 BP 文件夹")
            return

        if not self._require_api("功能12"):
            return

        structures_path = os.path.join(self.bp_path, "structures")
        if not os.path.exists(structures_path):
            self.show_error_dialog("错误", f"structures 文件夹不存在:\n{structures_path}")
            self.log(f"❌ [功能12] structures 文件夹不存在: {structures_path}")
            return

        self._run_feature_task(
            method_name="translate_mcstructure",
            log_prefix="[功能12]",
            feature_tag="功能12: mcstructure 汉化",
        )

    def _refresh_backup_dialog(self):
        """刷新备份对话框"""
        if hasattr(self, '_backup_dialog'):
            self.page.pop_dialog()
            self.show_backup_management_dialog()

    def show_import_export_dialog(self, e=None):
        """显示导入/导出管理对话框"""
        # 标记用户交互
        _mark_interaction("button_click", "导入/导出管理")
        
        # 调用对话框模块中的函数
        from ui import dialogs
        
        # 调试日志
        self.log(f"📥📤 点击了导入/导出管理按钮")
        self.log(f"配置管理器: {self.config_manager}")
        self.log(f"API管理器: {self.api_manager}")
        if self.api_manager:
            self.log(f"术语服务: {self.api_manager.term_service}")
            self.log(f"翻译缓存: {self.api_manager.cache}")
        
        try:
            dialogs.show_import_export_dialog(
                page=self.page,
                config_manager=self.config_manager,
                terminology_service=self.api_manager.term_service,
                translation_cache=self.api_manager.cache,
                log_callback=self.log
            )
            self.log("✅ 导入/导出对话框已显示")
        except Exception as ex:
            self.log(f"❌ 显示导入/导出对话框时出错: {ex}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            # 显示错误对话框
            from ui import dialogs as ui_dialogs
            ui_dialogs.show_error_dialog(self.page, "对话框错误", f"无法显示导入/导出对话框: {ex}")

    def show_performance_monitor_dialog(self, e=None):
        """显示性能监控和统计对话框"""
        # 标记用户交互
        _mark_interaction("button_click", "性能监控")
        
        import time
        from datetime import datetime
        
        # 收集性能统计信息
        stats = {}
        
        # 1. AST缓存统计（如果可用）
        try:
            from core.script_translation import JSASTExtractor
            ast_cache_stats = JSASTExtractor.get_cache_stats()
            stats['ast_cache'] = ast_cache_stats
        except Exception:
            stats['ast_cache'] = {'cache_size': 0, 'total_cached_strings': 0}
        
        # 2. 翻译缓存统计（如果可用）
        try:
            # 使用 api_manager 中的缓存实例，而不是创建新的
            translation_cache = self.api_manager.cache
            cache_stats = translation_cache.get_cache_stats()
            stats['translation_cache'] = cache_stats
        except Exception:
            stats['translation_cache'] = {'total_cached': 0, 'hits': 0, 'misses': 0}
        

        # 3. API调用统计（使用当前实例）
        try:
            api_stats = self.api_manager.get_api_stats() if hasattr(self.api_manager, 'get_api_stats') else {}
            stats['api'] = api_stats
        except Exception:
            stats['api'] = {'total_calls': 0, 'successful_calls': 0, 'failed_calls': 0}

        # 3.5. 实时指标采集器（环形缓冲区历史数据）
        try:
            from core.metrics_collector import get_metrics_collector
            collector = get_metrics_collector()
            collector.record_memory()
            stats['realtime'] = collector.get_snapshot()
        except Exception:
            stats['realtime'] = {}

        # 4. 系统信息
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            stats['system'] = {
                'memory_usage_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(interval=0.1),
                'thread_count': process.num_threads(),
                'create_time': datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                'runtime_seconds': time.time() - process.create_time()
            }
        except Exception:
            # 如果psutil不可用，提供基本系统信息
            
            import os
            import time
            
            stats['system'] = {
                'memory_usage_mb': 0,
                'cpu_percent': 0,
                'thread_count': 0,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'runtime_seconds': 0
            }
        
        # 5. 应用统计（从日志文件估算）
        log_stats = self._analyze_log_files()
        stats['application'] = log_stats
        
        # 创建对话框内容
        dialog_content = []
        
        # 添加标题
        dialog_content.append(ft.Text("📊 性能监控和统计", size=18, weight=ft.FontWeight.BOLD))
        dialog_content.append(ft.Divider(height=10))
        
        # 系统信息部分
        dialog_content.append(ft.Text("💻 系统信息:", size=14, weight=ft.FontWeight.BOLD))
        sys_info = stats['system']
        dialog_content.append(ft.Text(f"• 内存使用: {sys_info['memory_usage_mb']:.1f} MB", size=12))
        dialog_content.append(ft.Text(f"• CPU使用率: {sys_info['cpu_percent']:.1f}%", size=12))
        dialog_content.append(ft.Text(f"• 线程数: {sys_info['thread_count']}", size=12))
        dialog_content.append(ft.Text(f"• 运行时间: {sys_info['runtime_seconds']:.0f} 秒", size=12))
        dialog_content.append(ft.Text(f"• 启动时间: {sys_info['create_time']}", size=12))
        
        dialog_content.append(ft.Divider(height=10))
        
        # AST缓存统计
        dialog_content.append(ft.Text("🧠 AST缓存统计:", size=14, weight=ft.FontWeight.BOLD))
        ast_info = stats['ast_cache']
        dialog_content.append(ft.Text(f"• 缓存文件数: {ast_info['cache_size']}", size=12))
        dialog_content.append(ft.Text(f"• 最大缓存大小: {ast_info.get('maxsize', 128)}", size=12))
        
        # 计算真实缓存命中率（基于hits/misses）
        total_access = ast_info.get('hits', 0) + ast_info.get('misses', 0)
        if total_access > 0:
            hit_rate = ast_info.get('hits', 0) / total_access * 100
            dialog_content.append(ft.Text(f"• 命中率: {hit_rate:.1f}%", size=12))
            dialog_content.append(ft.Text(f"• 命中数: {ast_info.get('hits', 0)} | 未命中数: {ast_info.get('misses', 0)}", size=12))
        else:
            dialog_content.append(ft.Text(f"• 命中率: 无访问记录", size=12))
        
        dialog_content.append(ft.Divider(height=10))
        
        # 翻译缓存统计
        dialog_content.append(ft.Text("🔤 翻译缓存统计:", size=14, weight=ft.FontWeight.BOLD))
        trans_info = stats['translation_cache']
        total_access = trans_info.get('hits', 0) + trans_info.get('misses', 0)
        hit_rate = trans_info.get('hits', 0) / total_access * 100 if total_access > 0 else 0
        
        dialog_content.append(ft.Text(f"• 缓存条目数: {trans_info.get('total_cached', 0)}", size=12))
        dialog_content.append(ft.Text(f"• 缓存命中: {trans_info.get('hits', 0)}", size=12))
        dialog_content.append(ft.Text(f"• 缓存未命中: {trans_info.get('misses', 0)}", size=12))
        dialog_content.append(ft.Text(f"• 命中率: {hit_rate:.1f}%", size=12))
        
        dialog_content.append(ft.Divider(height=10))
        
        # API统计
        dialog_content.append(ft.Text("🌐 API调用统计:", size=14, weight=ft.FontWeight.BOLD))
        api_info = stats['api']
        success_rate = api_info.get('successful_calls', 0) / api_info.get('total_calls', 1) * 100 if api_info.get('total_calls', 0) > 0 else 0
        
        dialog_content.append(ft.Text(f"• 总调用次数: {api_info.get('total_calls', 0)}", size=12))
        dialog_content.append(ft.Text(f"• 成功调用: {api_info.get('successful_calls', 0)}", size=12))
        dialog_content.append(ft.Text(f"• 失败调用: {api_info.get('failed_calls', 0)}", size=12))
        dialog_content.append(ft.Text(f"• 成功率: {success_rate:.1f}%", size=12))
        
        dialog_content.append(ft.Divider(height=10))
        
        # 应用统计
        dialog_content.append(ft.Text("📈 应用统计:", size=14, weight=ft.FontWeight.BOLD))
        app_info = stats['application']
        
        if app_info:
            dialog_content.append(ft.Text(f"• 总翻译文件数: {app_info.get('total_files', 0)}", size=12))
            dialog_content.append(ft.Text(f"• 总翻译字符串数: {app_info.get('total_strings', 0)}", size=12))
            dialog_content.append(ft.Text(f"• 平均翻译速度: {app_info.get('avg_speed', 0):.1f} 字符串/秒", size=12))
            if app_info.get('last_operation'):
                dialog_content.append(ft.Text(f"• 最后操作: {app_info['last_operation']}", size=12))
        
        dialog_content.append(ft.Divider(height=10))

        # 实时采集指标
        realtime = stats.get('realtime', {})
        if realtime:
            dialog_content.append(ft.Text("⏱️ 实时采集指标:", size=14, weight=ft.FontWeight.BOLD))
            uptime = realtime.get('uptime_seconds', 0)
            m, s = divmod(int(uptime), 60)
            h, m = divmod(m, 60)
            dialog_content.append(ft.Text(f"• 运行时长: {h}h {m}m {s}s", size=12))
            dialog_content.append(ft.Text(f"• 累计翻译: {realtime.get('total_translated', 0)} 条", size=12))
            dialog_content.append(ft.Text(f"• 累计API调用: {realtime.get('total_api_calls', 0)} 次 (错误 {realtime.get('total_api_errors', 0)} 次)", size=12))
            dialog_content.append(ft.Text(f"• 平均翻译速率: {realtime.get('avg_translation_rate', 0):.1f} 条/秒", size=12))
            dialog_content.append(ft.Text(f"• 平均API响应: {realtime.get('avg_response_time', 0)*1000:.0f} ms", size=12))
            mem_history = realtime.get('memory_history_mb', [])
            if mem_history:
                dialog_content.append(ft.Text(f"• 当前内存: {mem_history[-1]:.1f} MB (最近{len(mem_history)}个采样点)", size=12))

        dialog_content.append(ft.Divider(height=10))
        
        # 性能优化建议
        dialog_content.append(ft.Text("💡 性能优化建议:", size=14, weight=ft.FontWeight.BOLD))
        
        suggestions = []
        
        # 基于统计数据的建议
        if ast_info['cache_size'] < 10:
            suggestions.append("• 考虑处理更多JS文件以提高AST缓存效率")
        
        if hit_rate < 50 and trans_info.get('total_cached', 0) > 0:
            suggestions.append("• 翻译缓存命中率较低，可能需要调整缓存策略")
        
        if sys_info['memory_usage_mb'] > 500:
            suggestions.append("• 内存使用较高，建议定期重启应用程序")
        
        if success_rate < 80 and api_info.get('total_calls', 0) > 10:
            suggestions.append("• API调用成功率较低，请检查网络连接或API配置")
        
        if not suggestions:
            suggestions.append("• 当前性能表现良好，继续保持！")
        
        for suggestion in suggestions:
            dialog_content.append(ft.Text(suggestion, size=12, color=ft.Colors.BLUE))
        
        dialog_content.append(ft.Divider(height=10))
        dialog_content.append(ft.Text("🔄 点击'刷新'按钮更新统计信息", size=11, color=ft.Colors.GREY))
        
        def close_dialog(e):
            self.page.pop_dialog()
        
        def refresh_dialog(e):
            self.page.pop_dialog()
            self.show_performance_monitor_dialog()
        
        # 创建对话框
        dialog = ft.AlertDialog(
            title=ft.Text("📊 性能监控和统计"),
            content=ft.Container(
                content=ft.Column(dialog_content, scroll=ft.ScrollMode.AUTO),
                height=500,
                padding=10,
            ),
            actions=[
                ft.TextButton("刷新", on_click=refresh_dialog),
                ft.TextButton("关闭", on_click=close_dialog),
            ],
        )
        
        self.page.show_dialog(dialog)
    
    def _analyze_log_files(self):
        """分析日志文件获取应用统计信息"""
        import os
        import re
        from datetime import datetime, timedelta
        
        stats = {
            'total_files': 0,
            'total_strings': 0,
            'avg_speed': 0,
            'last_operation': None
        }
        
        try:
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
            if not os.path.exists(log_dir):
                return stats
            
            # 查找最新的日志文件
            log_files = []
            for file in os.listdir(log_dir):
                if file.startswith('minecraft_translator_') and file.endswith('.log'):
                    log_files.append(os.path.join(log_dir, file))
            
            if not log_files:
                return stats
            
            # 按修改时间排序，获取最新的日志文件
            latest_log = max(log_files, key=os.path.getmtime)
            
            with open(latest_log, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 提取翻译相关统计
            file_pattern = r'成功 (\d+) 个，失败 (\d+) 个'
            string_pattern = r'翻译 (\d+) 处|翻译 (\d+) 个字符串'
            speed_pattern = r'速度.*?(\d+\.?\d*) 字符串/秒'
            
            file_matches = re.findall(file_pattern, log_content)
            string_matches = re.findall(string_pattern, log_content)
            speed_matches = re.findall(speed_pattern, log_content)
            
            if file_matches:
                stats['total_files'] = sum(int(match[0]) for match in file_matches)
            
            if string_matches:
                total_strings = 0
                for match in string_matches:
                    # match可能是元组，需要处理两种模式
                    if isinstance(match, tuple):
                        for num in match:
                            if num:
                                total_strings += int(num)
                    else:
                        total_strings += int(match)
                stats['total_strings'] = total_strings
            
            if speed_matches:
                speeds = [float(speed) for speed in speed_matches]
                stats['avg_speed'] = sum(speeds) / len(speeds) if speeds else 0
            
            # 提取最后操作时间
            time_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?开始.*?功能'
            time_matches = re.findall(time_pattern, log_content)
            if time_matches:
                stats['last_operation'] = time_matches[-1]
            
        except Exception:
            pass
        
        return stats

    def script_hardcode_translation(self, e):
        """[10] 脚本文件夹硬编码汉化测试版 - 增强版（支持三种汉化模式）"""
        # 标记用户交互
        _mark_interaction("button_click", "功能10: 脚本文件夹硬编码汉化")

        if not self.bp_path:
            self.show_error_dialog("错误", "请先选择 BP 文件夹")
            return

        # 检查是否有可用的API
        if not self._require_api("功能10"):
            return

        self.log("🚀 [功能10] 开始脚本文件夹硬编码汉化测试...")

        # 先快速扫描JS文件
        import os
        script_folder = os.path.join(self.bp_path, "scripts")
        if not os.path.exists(script_folder):
            self.show_error_dialog("错误", f"未找到脚本文件夹: {script_folder}")
            return
        
        # 扫描JS文件
        js_files = []
        for root, _, files in os.walk(script_folder):
            for file in files:
                if file.lower().endswith('.js'):
                    js_files.append(os.path.join(root, file))
        
        if not js_files:
            self.show_error_dialog("提示", f"在脚本文件夹中未找到任何JS文件")
            return
        
        self.log(f"📁 找到 {len(js_files)} 个JS脚本文件")
        
        # 创建选项对话框
        def option1_selected(e):
            """选项1: 只汉化包含§颜色/格式代码的脚本"""
            self.page.pop_dialog()
            self.log(f"🔧 选择模式1: 只汉化包含§颜色/格式代码的脚本")
            self.show_js_translation_preview_dialog(js_files, mode=1, bp_path=self.bp_path)
        
        def option2_selected(e):
            """选项2: 汉化通过了三重API验证机制的脚本"""
            self.page.pop_dialog()
            self.log(f"🔧 选择模式2: 汉化通过了三重API验证机制的脚本")
            self.show_js_translation_preview_dialog(js_files, mode=2, bp_path=self.bp_path)
        
        def option3_selected(e):
            """选项3: 取消"""
            self.page.pop_dialog()
            self.log(f"🔧 选择模式3: 取消操作")
        
        # 创建对话框
        dialog = ft.AlertDialog(
            title=ft.Text("🔧 脚本文件夹硬编码汉化选项"),
            content=ft.Column([
                ft.Text(f"在脚本文件夹中找到 {len(js_files)} 个JS文件", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("请选择汉化模式:", size=14),
                ft.Divider(height=10),
                ft.Text("选项1: 只汉化包含§颜色/格式代码的脚本", size=12),
                ft.Text("  • 仅处理包含Minecraft颜色代码(§)的文件", size=12, color=ft.Colors.GREY),
                ft.Text("  • 最安全的模式，基本不会误判", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("选项2: 汉化通过了三重API验证机制的脚本", size=12),
                ft.Text("  • 使用AI三重验证判断是否需要汉化", size=12, color=ft.Colors.GREY),
                ft.Text("  • 更全面，但需要API支持", size=12, color=ft.Colors.GREY),
                ft.Divider(height=10),
                ft.Text("📝 注意: 选择后将先显示预览对话框，确认后再执行翻译", size=11, color=ft.Colors.GREEN),
                ft.Divider(height=10),
                ft.Text("选项3: 取消操作", size=12, color=ft.Colors.GREY),
            ], tight=True, spacing=5),
            actions=[
                ft.TextButton("选项1", on_click=option1_selected),
                ft.TextButton("选项2", on_click=option2_selected),
                ft.TextButton("取消", on_click=option3_selected),
            ],
        )
        
        # 显示对话框
        self.page.show_dialog(dialog)
        
    def show_js_translation_preview_dialog(self, js_files, mode, bp_path=None):
        """
        显示JS翻译预览对话框
        
        参数:
            js_files: JS文件列表
            mode: 翻译模式 (1: 颜色代码模式, 2: AI智能模式)
            bp_path: BP文件夹路径
        """
        # 首先分析文件获取预览数据
        self.log(f"🔍 开始分析 {len(js_files)} 个JS文件用于预览...")
        
        # 禁用所有按钮
        self.disable_all_buttons()
        
        def analyze_task():
            try:
                def progress_callback(value, remaining=0, time_left=0):
                    async def update():
                        text = f"分析中... {int(value*100)}%" if value < 1 else "分析完成"
                        self.update_progress(value, text, remaining, time_left)
                    self.page.run_task(update)

                def log_callback(msg):
                    async def update():
                        self.log(msg)
                    self.page.run_task(update)

                # 创建ScriptTranslation实例
                from core.script_translation import create_script_translation
                script_translator = create_script_translation(self.translator)

                # 分析文件获取预览数据
                analysis_result = script_translator.analyze_js_files_for_preview(
                    js_files=js_files,
                    mode=mode,
                    progress_callback=progress_callback,
                    log_callback=log_callback
                )
                # ... 后续代码保持不变
                
                async def show_preview_dialog():
                    # 启用所有按钮
                    self.enable_all_buttons()
                    
                    if not analysis_result.get('success'):
                        self.show_error_dialog("分析失败", analysis_result.get('message', '未知错误'))
                        return
                    
                    # 获取分析数据
                    file_analyses = analysis_result.get('file_analyses', [])
                    summary = analysis_result.get('summary', {})
                    
                    if not file_analyses:
                        self.show_error_dialog("提示", "没有找到可翻译的字符串")
                        return
                    
                    # 创建预览内容
                    preview_content = []
                    
                    # 添加摘要信息
                    preview_content.append(ft.Text(
                        f"📊 分析摘要: {summary.get('total_files', 0)} 个文件, "
                        f"{summary.get('total_strings', 0)} 个字符串, "
                        f"{summary.get('needs_translation_count', 0)} 个需要翻译",
                        size=14,
                        weight=ft.FontWeight.BOLD
                    ))
                    
                    # 添加预估时间
                    estimated_time = summary.get('estimated_translation_time', 0)
                    preview_content.append(ft.Text(
                        f"⏱️ 预估翻译时间: {estimated_time:.1f} 秒",
                        size=12,
                        color=ft.Colors.GREY
                    ))
                    
                    preview_content.append(ft.Divider(height=10))
                    
                    # 创建文件列表
                    file_list = []
                    
                    for file_analysis in file_analyses:
                        file_path = file_analysis['file_path']
                        file_name = os.path.basename(file_path)
                        needs_count = file_analysis.get('needs_translation_count', 0)
                        total_count = file_analysis.get('total_strings', 0)
                        error = file_analysis.get('error')
                        
                        if error:
                            file_info_row = ft.Row([
                                ft.Text(file_name, size=12, expand=True),
                                ft.Text(f"错误: {error[:30]}", size=12, color=ft.Colors.RED)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        else:
                            file_info_row = ft.Row([
                                ft.Text(file_name, size=12, expand=True),
                                ft.Text(f"{needs_count}/{total_count}", size=12, color=ft.Colors.GREEN if needs_count > 0 else ft.Colors.GREY)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        
                        file_list.append(file_info_row)
                    
                    # 添加到预览内容
                    preview_content.append(ft.Text("📁 文件列表:", size=13, weight=ft.FontWeight.BOLD))
                    preview_content.extend(file_list)
                    preview_content.append(ft.Divider(height=10))
                    
                    # 添加提示信息
                    preview_content.append(ft.Text(
                        "⚠️ 注意: 翻译将创建备份文件 (.bak)，如有问题可手动恢复",
                        size=11,
                        color=ft.Colors.ORANGE
                    ))
                    
                    # 创建确认翻译的函数
                    def confirm_translation(e):
                        self.page.pop_dialog()
                        self._execute_script_translation(js_files, mode, bp_path)
                    
                    def cancel_preview(e):
                        self.page.pop_dialog()
                        self.log("预览取消")
                    
                    # 创建对话框
                    dialog = ft.AlertDialog(
                        title=ft.Text(f"🔍 JS翻译预览 (模式{mode})"),
                        content=ft.Column(preview_content, tight=True, spacing=8, scroll=ft.ScrollMode.AUTO),
                        actions=[
                            ft.TextButton("取消", on_click=cancel_preview),
                            ft.TextButton("确认翻译", on_click=confirm_translation, style=ft.ButtonStyle(color=ft.Colors.GREEN))
                        ],
                    )
                    
                    # 显示对话框
                    self.page.show_dialog(dialog)
                
                # 显示预览对话框
                self.page.run_task(show_preview_dialog)
                
            except Exception as ex:
                async def show_error(error=ex):
                    self.enable_all_buttons()
                    self.show_error_dialog("分析错误", str(error))
                self.page.run_task(show_error)
        
        # 启动分析任务线程
        import threading
        thread = threading.Thread(target=analyze_task, daemon=True)
        thread.start()

    


    def _execute_script_translation(self, js_files, mode, bp_path=None):
        """执行脚本翻译：支持单文件和多文件两种场景"""
        import threading
        def translation_task():
            try:
                def progress_callback(value, remaining_count=0, remaining_time=0):
                    text = f"翻译中... {int(value*100)}%" if value < 1 else "翻译完成"
                    async def update():
                        self.update_progress(value, text, remaining_count, remaining_time)
                    self.page.run_task(update)

                def log_callback(msg):
                    async def update():
                        self.log(msg)
                    self.page.run_task(update)

                self.disable_all_buttons()
                
                # 根据文件数量选择翻译方式
                if len(js_files) == 1:
                    # 单文件翻译
                    js_file = js_files[0]
                    log_callback(f"🚀 开始翻译单个 JS 文件: {os.path.basename(js_file)}")
                    result = self.functions.translate_single_js_file(
                        js_file_path=js_file,
                        mode=mode,
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )
                else:
                    # 多文件批量翻译
                    log_callback(f"🚀 开始批量翻译 {len(js_files)} 个 JS 文件")
                    from core.script_translation import ScriptTranslation
                    script_trans = ScriptTranslation(self.translator)
                    result = script_trans.translate_js_files_with_ast(
                        js_files=js_files,
                        mode=mode,
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )
                
                if result.get('success'):
                    translated_count = len(result.get('translated_files', []))
                    if translated_count == 0:
                        msg = "所有文件中均未找到需要翻译的字符串"
                    else:
                        msg = f"成功翻译 {translated_count} 个文件，共处理 {len(js_files)} 个文件"
                    async def show_success():
                        self.show_success_dialog("翻译完成", msg)
                    self.page.run_task(show_success)
                else:
                    async def show_error():
                        self.show_error_dialog("翻译失败", result.get('message', '未知错误'))
                    self.page.run_task(show_error)
            except Exception as ex:
                error_msg = str(ex)
                async def show_error():
                    self.show_error_dialog("错误", error_msg)
                self.page.run_task(show_error)
            finally:
                self.enable_all_buttons()
        thread = threading.Thread(target=translation_task, daemon=True)
        thread.start()
    
    def enable_all_apis(self, e=None):
        """批量启用所有API"""
        # 标记用户交互
        _mark_interaction("button_click", "批量启用所有API")
        
        try:
            # 遍历所有API提供商
            providers = ["deepseek", "qwen", "zhipu", "doubao", "local_ollama", 
                        "openai", "azure_openai", "baidu_ernie", "iflytek_spark", "google_gemini"]
            changed = False
            for provider in providers:
                apis = self.config.get(provider, [])
                if isinstance(apis, list):
                    for api in apis:
                        if not api.get("enabled", True):
                            api["enabled"] = True
                            changed = True
            
            if changed:
                self.save_config()
                self.refresh_config_tab()
                self.log("✅ 已批量启用所有API")
                self.show_success_dialog("成功", "所有API已启用")
            else:
                self.log("ℹ️ 所有API已经处于启用状态")
                self.show_info_dialog("提示", "所有API已经是启用状态")
                
        except Exception as ex:
            self.log(f"❌ 批量启用API失败: {ex}")
            self.show_error_dialog("错误", f"批量启用失败: {ex}")


    def disable_all_apis(self, e=None):
        """批量禁用所有API"""
        # 标记用户交互
        _mark_interaction("button_click", "批量禁用所有API")
        
        try:
            # 遍历所有API提供商
            providers = ["deepseek", "qwen", "zhipu", "doubao", "local_ollama", 
                        "openai", "azure_openai", "baidu_ernie", "iflytek_spark", "google_gemini"]
            changed = False
            for provider in providers:
                apis = self.config.get(provider, [])
                if isinstance(apis, list):
                    for api in apis:
                        if api.get("enabled", True):
                            api["enabled"] = False
                            changed = True
            
            if changed:
                self.save_config()
                self.refresh_config_tab()
                self.log("✅ 已批量禁用所有API")
                self.show_success_dialog("成功", "所有API已禁用")
            else:
                self.log("ℹ️ 所有API已经处于禁用状态")
                self.show_info_dialog("提示", "所有API已经是禁用状态")
                
        except Exception as ex:
            self.log(f"❌ 批量禁用API失败: {ex}")
            self.show_error_dialog("错误", f"批量禁用失败: {ex}")

def main(page: ft.Page):
    """主函数"""
    app = MinecraftTranslatorApp(page)

    def on_close(e):
        """应用退出时的清理处理"""
        logger.info("应用正在关闭...")

        try:
            if hasattr(app, 'api_manager') and app.api_manager:
                app.api_manager.close()
                logger.debug("APIManager 已关闭")
        except Exception as ex:
            logger.error(f"关闭 APIManager 失败: {ex}")

        try:
            from ui.background_task_service import get_global_task_service
            task_service = get_global_task_service()
            if task_service:
                task_service.shutdown(wait=False)
                logger.debug("后台任务服务已关闭")
        except Exception as ex:
            logger.error(f"关闭后台任务服务失败: {ex}")

        try:
            lm = get_log_manager()
            if lm:
                lm.cleanup()
                logger.debug("日志管理器已清理")
        except Exception as ex:
            print(f"清理日志失败: {ex}")

        logger.info("应用已安全退出")

    page.on_close = on_close