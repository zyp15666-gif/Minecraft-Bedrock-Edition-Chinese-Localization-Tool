"""
Minecraft 基岩版汉化工具 - Flet 应用主体

窗口与业务 UI 实现。全局日志与崩溃钩子由 ui.bootstrap 在导入本模块前安装。
"""

import asyncio
import os
import sys
from datetime import datetime

import flet as ft

from core.container import build_app_container
from core.log_manager import get_log_manager, get_logger
from ui import tabs
from ui.application_api_batch import ApplicationApiBatchMixin
from ui.application_api_config import ApplicationApiConfigMixin
from ui.application_dialogs_theme import ApplicationDialogsThemeMixin
from ui.application_feature_operations import ApplicationFeatureOperationsMixin
from ui.application_script_translation import ApplicationScriptTranslationMixin
from ui.application_tab_shell import ApplicationTabShellMixin
from ui.application_tools_dialogs import ApplicationToolsDialogsMixin
from ui.background_task_service import BackgroundTaskService
from ui.dialog_manager import DialogManager
from ui.first_run_wizard import FirstRunWizard
from ui.function_handlers import FunctionHandlers
from ui.ui_coordinator import UICoordinator
from ui.user_interaction import mark_interaction
from ui.utils import ProgressThrottler
from ui.window import WindowManager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)


class MinecraftTranslatorApp(
    ApplicationTabShellMixin,
    ApplicationFeatureOperationsMixin,
    ApplicationApiConfigMixin,
    ApplicationApiBatchMixin,
    ApplicationDialogsThemeMixin,
    ApplicationToolsDialogsMixin,
    ApplicationScriptTranslationMixin,
):
    """Minecraft 基岩版汉化翻译工具 - Flet 版本"""

    def __init__(self, page: ft.Page):
        """初始化应用"""
        self.page = page
        self.page.title = "🎮 Minecraft 基岩版汉化工具"

        self.full_log_text = []
        self.terminal_text = []

        self._progress_throttler = ProgressThrottler(min_interval=0.1, significant_delta=0.05)

        self.window_manager = WindowManager(page, self.log)
        self.window_manager.initialize_window()
        self.window_manager.init_theme_colors()

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

        self.page.window.on_resize = self.window_manager.create_window_resize_handler()

        self.page.theme_mode = ft.ThemeMode.LIGHT

        self._file_pickers_available = not getattr(self.page, 'web', False)
        logger.debug(f"文件选择器使用 tkinter，_file_pickers_available = {self._file_pickers_available}")

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

        self.functions = self.app_service

        max_workers_config = self.config.get('basic', {}).get('max_threads', 4)
        self.task_service = BackgroundTaskService(
            page=self.page,
            max_workers=min(max_workers_config, 8)
        )
        self.log(f"✅ 后台任务服务已初始化，最大线程数: {self.task_service.executor._max_workers}")
        lm = get_log_manager()
        if lm:
            self.log(f"📁 日志文件目录: {lm.log_dir}")

        self.ui_coordinator = UICoordinator(
            page=self.page,
            task_service=self.task_service,
            log_callback=self.log,
            show_error=self.show_error_dialog,
            show_success=self.show_success_dialog,
        )
        self.log("✅ UI协调器已初始化 (ui/ui_coordinator.py)")

        self.func_handlers = FunctionHandlers(self)
        self.log("✅ 功能事件处理器已加载 (ui/function_handlers.py)")

        self.dialog_manager = DialogManager(
            page=self.page,
            config_manager=self.config_manager,
            api_manager=self.api_manager,
            log_callback=self.log
        )
        self.log("✅ 对话框管理器已初始化 (ui/dialog_manager.py)")

        self.bp_path_label = ft.Text("未选择", color=ft.Colors.GREY)
        self.rp_path_label = ft.Text("未选择", color=ft.Colors.GREY)
        self.api_status_label = ft.Text("未检测", color=ft.Colors.GREY)

        self.bp_path = None
        self.rp_path = None

        self.selected_api = None
        self.selected_api_type = None

        self.progress_value = 0
        self.progress_text = ft.Text("就绪", size=self.ui_scale['body_size'])
        self.remaining_count = 0
        self.remaining_time = 0

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

        mark_interaction("app_startup", "应用程序启动完成 (版本: Minecraft基岩版汉化工具)")
        self.log("🚀 应用程序启动完成 - 详细调试模式已启用")
        self.log("🎮 Minecraft基岩版汉化工具 - 全功能详细日志记录已开启")
        self.log(f"📁 工作目录: {os.getcwd()}")
        self.log("🔧 日志级别: DEBUG")
        self.log("👤 所有用户操作将被详细记录")

        try:
            self.page.bring_to_front()
        except Exception as ex:
            logger.debug(f"窗口前置功能不可用: {ex}")

        self.show_startup_animation()

        self._first_run_wizard = FirstRunWizard(
            self.page, self.config, on_continue=self._on_first_run_continue
        )
        if self._first_run_wizard.is_first_run():
            self._first_run_wizard.show()

    def _on_first_run_continue(self):
        self.log("✅ 首次运行向导完成")

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

        self.task_service.run(startup_task)

    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.full_log_text.append(log_entry)
        logger.info(message)

    def run_background_task(self, task_func, *args, **kwargs):
        """安全地运行后台任务（线程安全包装）"""
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

    async def on_select_bp_folder(self, e):
        """选择 BP 文件夹（使用tkinter）"""
        mark_interaction("folder_select", "选择BP文件夹")

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
        mark_interaction("folder_select", "选择RP文件夹")

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
            both_selected = (self.bp_path is not None and
                             self.rp_path is not None)

            if hasattr(self, 'function_buttons'):
                for btn in self.function_buttons:
                    btn.disabled = not both_selected

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

        if hasattr(self, 'api_detect_button') and self.api_detect_button:
            self.api_detect_button.disabled = True
            self.api_detect_button.text = "检测中..."

        self.api_status_label.value = "正在检测..."
        self.api_status_label.color = ft.Colors.BLUE_400

        self.page.update()

        async def update_progress_api():
            self.update_progress(0.6, "正在检测API...", 0, 0)
        self.page.run_task(update_progress_api)

        try:
            available_apis = self.api_manager.detect_available_apis()
            if available_apis:
                self.api_status_label.value = f"检测到 {len(available_apis)} 个可用 API"
                self.api_status_label.color = ft.Colors.GREEN_400
                self.log(f"检测到 {len(available_apis)} 个可用 API")
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
            if hasattr(self, 'api_detect_button') and self.api_detect_button:
                self.api_detect_button.disabled = False
                self.api_detect_button.text = "检测可用 API"

            async def reset_progress():
                self.update_progress(0, "", 0, 0)
            self.page.run_task(reset_progress)

        self.page.update()

    def update_progress(self, value, text, remaining_count, remaining_time):
        """更新进度条和文本 - 委托给UICoordinator"""
        self.ui_coordinator.update_progress(value, text, remaining_count, remaining_time)

    def _run_feature_task(self, method_name: str, log_prefix: str, feature_tag: str, **extra_kwargs):
        """统一后台任务调度 — 自动管理按钮状态、进度、日志"""
        mark_interaction("button_click", feature_tag)
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
