# Minecraft 基岩版汉化工具

## 项目概述
Minecraft 基岩版汉化工具是一个现代化的汉化翻译工具，专为 Minecraft 基岩版插件和资源包提供汉化支持。

## 核心功能
1. **[1] 仅提取汉化 key** - 从 BP 文件夹中提取需要汉化的文本
2. **[2] 提取+AI翻译** - 使用多种 AI API 进行智能翻译，支持三阶段翻译策略
3. **[3] 全 BP 替换 display_name** - 批量替换 display_name 等字段
4. **[4] 批量删除 value** - 处理 JSON 文件中的 value 字段
5. **[5] 批量还原 value** - 恢复 JSON 文件中的 value 字段
6. **[6] 翻译独立的.lang 文件** - 支持翻译单独的语言文件
7. **[7] 一条龙服务** - 集成提取、翻译、替换的完整流程
8. **[8] 高亮实体信息显示名称适配** - 适配实体信息显示
9. **[9] 翻译单个 JS 文件** - 提取和翻译 JavaScript 文件中的文本
10. **[10] 脚本文件夹硬编码汉化测试版** - 脚本文件夹硬编码汉化（测试版）
11. **[11] 备份文件管理** - 管理和恢复备份文件
12. **[12] mcstructure 汉化** - 翻译 .mcstructure 结构文件

## 高级特性

### 安全性
- **API Key 加密存储**：使用 Windows DPAPI 加密，密钥不以明文保存
- **配置版本迁移**：自动迁移旧版本配置
- **数据完整性保护**：SQLite 缓存完整性检查，损坏自动恢复

### 稳定性
- **WebView2 检测**：启动时自动检测运行时依赖
- **自动更新检查**：后台检查 GitHub Releases 新版本
- **资源泄漏防护**：完善的资源管理和清理机制

### 可访问性
- **高对比度支持**：自动检测系统高对比度模式
- **屏幕阅读器支持**：检测 NVDA、Windows 讲述人等
- **系统文本缩放**：跟随系统缩放设置

### 翻译质量
- **三阶段翻译策略**：智能处理颜色代码、占位符和游戏术语
- **术语一致性管理**：内置 1551 条 Minecraft 术语
- **翻译质量检查**：自动检测 AI 提示信息、长度比例等问题
- **多 API 负载均衡**：支持 10+ 种 API，自动检测并平衡负载

### 架构设计
- **模块化架构**：清晰的分层设计（UI → 服务层 → 用例 → 翻译器 → API）
- **依赖注入容器**：统一初始化入口，避免重复初始化
- **Provider 模式**：统一 API 提供商抽象层，易于扩展

## 技术栈
- Python 3.9+
- Flet 0.84.x (现代化 UI 框架)
- Windows DPAPI (敏感数据加密)
- SQLite WAL (翻译缓存)
- 多线程处理

## 支持的 API
| 提供商 | 类型 | 说明 |
|--------|------|------|
| DeepSeek | 云端 | 推荐，性价比高 |
| 智谱 AI | 云端 | 国产大模型 |
| 通义千问 | 云端 | 阿里云 |
| 豆包 | 云端 | 字节跳动 |
| OpenAI | 云端 | GPT 系列 |
| Azure OpenAI | 云端 | 企业级 |
| 百度文心 | 云端 | 百度 |
| 讯飞星火 | 云端 | 科大讯飞 |
| Google Gemini | 云端 | Google |
| Ollama | 本地 | 开源本地模型 |

## 项目结构
```
├── api/              # API 抽象层
│   ├── providers/    #   API 提供者（Provider 模式）
│   ├── terminology/  #   术语子模块
│   └── ...           #   管理器、缓存、负载均衡等
├── config/           # 配置层
├── core/             # 核心业务层
│   ├── use_cases/    #   12 个独立用例
│   ├── secure_storage.py  # 安全存储
│   ├── update_checker.py  # 更新检查
│   ├── webview2_checker.py # 运行时检测
│   └── ...
├── docs/             # 文档
├── resources/        # 资源文件
├── scripts/          # 工具脚本
├── tests/            # 测试
├── ui/               # 用户界面
│   ├── components/   #   UI 组件
│   ├── tabs/         #   标签页
│   ├── window/       #   窗口管理
│   ├── accessibility.py  # 可访问性支持
│   └── ...
└── requirements.txt  # Python 依赖
```

## 快速开始

### 方式一：使用安装包
1. 下载最新版本安装包
2. 运行安装程序
3. 启动应用

### 方式二：从源码运行
```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python scripts/run_flet_desktop.py
```

## 系统要求
- **操作系统**：Windows 10 1909+ 或 Windows 11
- **运行时**：Microsoft Edge WebView2（应用会自动检测）
- **Python**：3.9+（仅从源码运行时需要）
- **网络**：用于 AI 翻译 API 调用

## 文档
- [用户指南](docs/USER_GUIDE.md)
- [API 文档](docs/API.md)
- [代码签名指南](docs/CODE_SIGNING_GUIDE.md)
- [UI 架构](docs/ui_architecture.md)

## 更新日志

### 2026-05-03
- **安全**：API Key 使用 Windows DPAPI 加密存储
- **安全**：配置文件版本迁移机制
- **稳定**：WebView2 运行时检测
- **稳定**：SQLite 缓存完整性检查
- **稳定**：应用更新检查
- **稳定**：修复多处异常处理和资源泄漏
- **UX**：可访问性支持（屏幕阅读器、高对比度）
- **部署**：安装目录使用 LocalAppData
- **部署**：卸载时清理用户数据选项

### 2026-04-28
- Flet 0.84+ 迁移
- 后台任务服务线程安全修复
- 多处 Bug 修复

### 2026-04-15
- 统一配置格式为 YAML
- 删除冗余的 api_config.json

### 2026-04-13
- 大规模架构重构
- 新增智能翻译策略
- 新增质量检查器

## 许可证
MIT License - 详见 [LICENSE](LICENSE)
