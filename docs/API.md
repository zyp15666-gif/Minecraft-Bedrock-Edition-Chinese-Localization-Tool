# 接口文档

## 核心模块接口

### 1. 翻译管道模块
**文件**：`core/pipeline.py`

翻译管道模块是项目的核心集成点，负责协调所有翻译组件。

#### 主要类
- `TranslationPipeline` — 翻译管道主类
- `setup_translation_pipeline()` — 设置管道（兼容旧接口）
- `translate_lang_file_direct()` — 直接翻译.lang文件的便捷函数

#### 主要方法
| 方法 | 说明 |
|------|------|
| `initialize()` | 初始化所有翻译组件 |
| `translate_lang_file(input, output, ...)` | 翻译单个.lang文件 |
| `batch_translate_files(file_pairs, ...)` | 批量翻译多个文件 |

### 2. 翻译器
**文件**：`core/translator.py`

#### 主要方法
| 方法 | 说明 |
|------|------|
| `translate_entries(entries, ...)` | 智能选择多线程/单线程模式 |
| `translate_dict_parallel(entries, ...)` | 多线程分批翻译 |
| `translate_dict_single(entries, ...)` | 单线程分批翻译 |
| `translate_single_item(...)` | 单个条目翻译（含术语匹配 + 智能降级） |

### 3. API 管理模块
**文件**：`api/api_manager.py`

#### 主要方法
| 方法 | 说明 |
|------|------|
| `build_api_list()` | 构建 API 列表（深拷贝，不修改原配置） |
| `detect_available_apis()` | 并行检测所有可用 API |
| `get_next_api()` | 加权轮询获取 API（带线程容量控制 + 60次超时） |
| `call_api_translate(api, text)` | 调用指定 API 翻译（委托给 TranslationStrategy） |
| `multi_api_translate(text)` | 多重 API 验证，选择最佳结果 |
| `close()` | 关闭 API 管理器，释放资源 |

#### 子组件
| 组件 | 文件 | 职责 |
|------|------|------|
| `APIClient` | `api/api_client.py` | 底层 HTTP 通信（Provider 模式 + 指数退避重试） |
| `LoadBalancer` | `api/load_balancer.py` | 基于响应时间的加权轮询 |
| `APIMonitor` | `api/api_monitor.py` | API 统计与告警 |
| `TranslationStrategy` | `api/translation_strategy.py` | 三阶段翻译流程 |
| `TranslationCache` | `api/translation_cache.py` | 内存 LRU + SQLite WAL 缓存（含完整性检查） |

### 4. Provider 层
**文件**：`api/providers/`

| Provider | 文件 | 支持 API 类型 |
|----------|------|---------------|
| `BaseProvider` | `base.py` | 抽象基类 |
| `OpenAICompatibleProvider` | `openai_compatible.py` | DeepSeek / Qwen / OpenAI |
| `OllamaProvider` | `ollama.py` | 本地 Ollama（支持 api_key） |
| `ZhipuProvider` | `zhipu.py` | 智谱 AI |
| `DoubaoProvider` | `doubao.py` | 豆包 AI |

#### Provider 统一错误处理
`BaseProvider` 提供了以下错误处理方法：

| 方法 | 说明 |
|------|------|
| `classify_error(error, response_data)` | 统一错误分类（auth/timeout/connection/rate_limit 等） |
| `get_error_user_message(error, response_data)` | 获取用户友好的错误消息 |

### 5. 术语服务
**文件**：`api/terminology_service.py` + `api/terminology/`

| 方法 | 说明 |
|------|------|
| `get_translation_original(text)` | 原始文本精确匹配 |
| `get_translation_clean(text)` | 清洗后文本匹配 |
| `preprocess(text)` | 术语 → 占位符 |
| `postprocess(text, map)` | 占位符 → 术语 |
| `export_terms(path)` / `import_terms(path)` | 导入导出 |
| `check_for_updates()` | 检查术语文件是否有更新（基于 mtime） |
| `hot_reload()` | 热更新术语词典 |
| `auto_update_if_needed()` | 自动检查并热更新 |

### 6. 配置管理模块
**文件**：`config/config_manager.py`

| 方法 | 说明 |
|------|------|
| `load_config()` | 加载配置文件（含版本迁移） |
| `save_config()` | 保存配置（API Key 自动加密存储） |
| `validate_config()` | 验证配置有效性 |
| `export_config(filepath)` | 导出配置到文件 |
| `import_config(filepath, merge)` | 从文件导入配置 |
| `restore_from_backup(backup_name)` | 从备份恢复配置 |
| `list_backups()` | 列出所有可用备份 |
| `get_function_buttons_config()` | 获取功能按钮配置 |
| `update_function_buttons_config()` | 更新功能按钮配置 |

#### 配置版本迁移
配置文件支持自动版本迁移，当前版本：`2.1`

| 版本 | 变更 |
|------|------|
| 1.x → 2.0 | 初始版本迁移框架 |
| 2.0 → 2.1 | API Key 迁移到安全存储（Windows DPAPI 加密） |

### 7. 安全存储模块
**文件**：`core/secure_storage.py`

使用 Windows DPAPI 加密存储敏感数据（如 API Key）。

| 方法 | 说明 |
|------|------|
| `store_api_key(provider, api_name, api_key)` | 安全存储 API Key |
| `retrieve_api_key(provider, api_name)` | 获取 API Key |
| `delete_api_key(provider, api_name)` | 删除 API Key |
| `migrate_from_config(config)` | 从配置文件迁移 API Key |
| `is_dpapi_available()` | 检查 DPAPI 是否可用 |

### 8. WebView2 检测模块
**文件**：`core/webview2_checker.py`

检测和引导安装 WebView2 运行时。

| 方法 | 说明 |
|------|------|
| `check_webview2_installed()` | 检查 WebView2 是否已安装 |
| `ensure_webview2(show_dialog)` | 确保 WebView2 可用，未安装时提示用户 |
| `open_webview2_download_page()` | 打开下载页面 |

### 9. 更新检查模块
**文件**：`core/update_checker.py`

检查 GitHub Releases 是否有新版本。

| 方法 | 说明 |
|------|------|
| `check_for_update(force)` | 检查更新 |
| `check_async(callback, force)` | 异步检查更新 |
| `open_download_page(update_info)` | 打开下载页面 |
| `get_current_version()` | 获取当前应用版本 |

### 10. 质量检查器
**文件**：`core/quality_checker.py`

检查项：AI提示信息 / 长度比例 / 颜色代码 / 占位符 / 英文比例 / 术语一致性

### 11. 文件处理器
**文件**：`core/file_handler.py`

| 方法 | 说明 |
|------|------|
| `parse_lang_file(path)` | 解析.lang文件（`\\n` → `\n` 还原） |
| `merge_and_write_lang(path, entries)` | 合并写入语言文件 |
| `backup_folder(path)` | 备份文件夹 |
| `extract_entries(bp_folder)` | 提取 BP 中 JSON 翻译条目 |
| `validate_operation_path(path)` | 验证操作路径安全性 |

### 12. 翻译缓存
**文件**：`api/translation_cache.py`

| 方法 | 说明 |
|------|------|
| `get(key)` | 获取缓存 |
| `set(key, value)` | 设置缓存 |
| `close()` | 关闭缓存，保存数据 |
| `_check_database_integrity()` | 检查数据库完整性 |
| `_handle_corrupted_database()` | 处理损坏的数据库 |

### 13. UI 模块
**文件**：`ui/`

| 模块 | 文件 | 职责 |
|------|------|------|
| `MinecraftTranslatorApp` | `main_window.py` | 主窗口 |
| `BackgroundTaskService` | `background_task_service.py` | 线程安全任务调度 |
| `AccessibilityHelper` | `accessibility.py` | 可访问性支持（屏幕阅读器/高对比度） |
| `ThemeManager` | `theme_manager.py` | 主题管理（含高对比度支持） |
| 对话框 | `dialogs.py` | 成功/错误/导入导出/API添加 |
| 标签页 | `tabs/__init__.py` | 状态栏/按钮/进度/配置/日志 |
| UI工具 | `utils.py` | 主题颜色/缩放/进度节流器 |

### 14. 可访问性模块
**文件**：`ui/accessibility.py`

| 方法 | 说明 |
|------|------|
| `detect_high_contrast_mode()` | 检测系统高对比度模式 |
| `detect_screen_reader()` | 检测屏幕阅读器 |
| `get_system_text_scale()` | 获取系统文本缩放比例 |
| `get_accessibility_config()` | 获取可访问性配置 |
| `announce_to_screen_reader(page, message)` | 向屏幕阅读器发送通知 |

### 15. 后台任务服务
**文件**：`ui/background_task_service.py`

| 方法 | 说明 |
|------|------|
| `run(fn, ...)` | 安全执行后台任务 |
| `run_with_ui_callbacks(fn, ...)` | 带完整 UI 回调的任务执行 |
| `schedule_on_main_thread(cb)` | 主线程调度 |
| `shutdown(wait)` | 关闭服务 |

### 16. 弃用 API 检查器
**文件**：`scripts/check_flet_deprecated.py`

Pre-commit 钩子，自动检测：`ft.border.*` / `ft.padding.*` / `ft.margin.*` / `ft.border_radius.*` / `ft.app()` / 旧对话框 API / `page.close_dialog()`。

---

## 模块调用关系
```
主窗口 (main_window.py)
  ├── BackgroundTaskService     —— 线程安全任务调度
  ├── dialogs.py                —— 对话框
  ├── tabs/__init__.py          —— 标签页组件
  ├── accessibility.py          —— 可访问性支持
  └── ApplicationService (core/application_service.py)
        └── use_cases/          —— 12个用例模块
              └── Translator    —— 翻译器
                    └── APIManager —— API 管理器
                          ├── TranslationStrategy
                          ├── TranslationCache
                          ├── LoadBalancer
                          ├── APIMonitor
                          └── APIClient → Provider
```

---

## 启动流程

```
run_flet_desktop.py
  ├── check_dependencies()      —— WebView2 检测
  ├── init_logger()             —— 日志系统初始化
  ├── check_update_on_startup() —— 后台更新检查
  └── ft.run(main)
        └── MinecraftTranslatorApp(page)
              ├── build_app_container() —— 依赖注入容器
              │     ├── ConfigManager
              │     ├── APIManager
              │     ├── Translator
              │     ├── FileHandler
              │     └── ApplicationService
              ├── build_ui()           —— 构建 UI
              └── on_close()           —— 退出清理
                    ├── APIManager.close()
                    ├── BackgroundTaskService.shutdown()
                    └── LogManager.cleanup()
```

**最后更新日期**：2026-05-03
