# UI 模块化架构设计

## 概述
Minecraft基岩版汉化工具使用 Flet 0.84+ 现代化 UI 框架，采用模块化架构设计。

## 模块结构
```
ui/
├── accessibility.py            # 可访问性支持
├── background_task_service.py  # 后台任务服务
├── backup_manager.py           # 备份管理器 UI
├── button_group_layout.py      # 按钮组布局
├── dialog_manager.py           # 对话框管理器
├── dialogs.py                  # 对话框组件
├── function_button_handler.py  # 功能按钮处理器
├── function_handlers.py        # 功能处理器
├── main_window.py              # 主窗口
├── theme_manager.py            # 主题管理器
├── ui_coordinator.py           # UI 协调器
├── utils.py                    # 工具函数
├── components/                 # UI 组件
│   ├── api_manager.py          #   API 管理组件
│   ├── config_io.py            #   配置导入导出组件
│   ├── folder_selector.py      #   文件夹选择器组件
│   ├── performance_monitor.py  #   性能监控组件
│   ├── progress_display.py     #   进度显示组件
│   └── status_bar.py           #   状态栏组件
├── tabs/                       # 标签页
│   ├── config_tab.py           #   配置标签页
│   ├── context.py              #   上下文管理器
│   ├── function_buttons.py     #   功能按钮标签页
│   ├── log_tab.py              #   日志标签页
│   ├── progress.py             #   进度标签页
│   └── status_bar.py           #   状态栏标签页
└── window/                     # 窗口管理
    └── window_manager.py       #   窗口管理器
```

### 主窗口 (`main_window.py`)
- `MinecraftTranslatorApp` — 主应用类
- `main()` — 入口函数（含 `on_close` 清理逻辑）
- `handle_exception()` — 全局异常处理
- `_mark_interaction()` — 用户交互标记辅助函数

### 可访问性模块 (`accessibility.py`)
- `AccessibilityHelper` — 可访问性辅助类
- `detect_high_contrast_mode()` — 检测系统高对比度模式
- `detect_screen_reader()` — 检测屏幕阅读器（NVDA、讲述人等）
- `get_system_text_scale()` — 获取系统文本缩放比例
- `announce_to_screen_reader()` — 向屏幕阅读器发送通知

### 后台任务服务 (`background_task_service.py`)
线程安全的任务调度器，统一管理后台任务。使用 `page.run_task()` 确保 UI 更新都在主线程执行。

主要类:
- `BackgroundTaskService` — 任务调度器（`run` / `run_with_ui_callbacks` / `schedule_on_main_thread` / `shutdown`）
- `SafeUIAccess` — 装饰器/上下文管理器，确保函数在主线程执行

### 主题管理器 (`theme_manager.py`)
- `UITheme` — 主题定义（暗色/亮色/高对比度）
- `ThemeManager` — 主题管理器（支持高对比度模式检测）

### 对话框模块 (`dialogs.py`)
- `show_success_dialog()` / `show_error_dialog()` / `show_info_dialog()`
- `show_log_dialog()` / `show_terminal_dialog()`
- `show_add_api_dialog()` — 添加 API 配置（含模型预设下拉菜单）
- `show_import_export_dialog()` — 导入导出管理（配置/术语库/翻译记忆库）

### 标签页组件 (`tabs/`)
- `UIContext` — UI 构建上下文，封装共享状态（page / ui_scale / theme_colors / callbacks）
- `create_status_bar()` — 暗夜模式切换
- `create_function_buttons()` — 12个核心功能按钮
- `create_progress_section()` — 进度条
- `create_config_tab()` — 基本配置 + 数据管理 + API 管理
- `create_log_tab()` — 内嵌日志窗口

### 工具函数 (`utils.py`)
- `get_theme_color()` / `generate_api_name()` / `create_ui_scale()`
- `format_file_size()` / `truncate_text()`
- `ProgressThrottler` — 进度更新节流器

### 窗口管理 (`window/window_manager.py`)
- `WindowManager` — 窗口状态管理（缩放、位置、大小调整）

## 启动流程
```
run_flet_desktop.py
  ├── check_dependencies()      —— WebView2 检测
  ├── init_logger()             —— 日志系统初始化
  ├── check_update_on_startup() —— 后台更新检查
  └── ft.run(main)
        └── MinecraftTranslatorApp(page)
              ├── build_app_container() —— 依赖注入容器
              ├── build_ui()           —— 构建 UI
              └── on_close()           —— 退出清理
```

## 退出清理
应用退出时依次执行：
1. `APIManager.close()` — 关闭 API 管理器
2. `BackgroundTaskService.shutdown()` — 关闭后台任务服务
3. `LogManager.cleanup()` — 清理日志管理器

## 技术栈
- Flet 0.84.x（版本约束 `<0.86.0`）
- 依赖注入模式（`UIContext` + 回调字典）
- 完整的类型提示和文档字符串
- 响应式缩放布局（支持 2K / 1080p / 900p / 笔记本 / 小屏）

## 代码质量
- Pre-commit 钩子：Flet 弃用 API 检查 / flake8 / mypy / bandit
- 所有 `page.run_task()` 调用均使用 `async def`
- 对话框使用 `page.open()` / `page.show_dialog()`（非旧 `page.dialog =` 模式）
- 样式使用大写 API（`ft.Border` / `ft.Padding` / `ft.Colors` / `ft.Icons`）

## 可访问性支持
- 自动检测系统高对比度模式并切换主题
- 自动检测屏幕阅读器（NVDA、Windows 讲述人、JAWS）
- 支持系统文本缩放
- 提供屏幕阅读器通知接口

**最后更新日期**：2026-05-03
