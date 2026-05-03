# ⚠️ 安全警告

## API 密钥保护

**本项目配置文件 `config/config.yml` 包含真实的API密钥！**

### 安全措施
1. ✅ `config/config.example.yml` 作为配置模板（不含真实密钥）
2. ✅ 真实密钥仅保存在本地 `config/config.yml`
3. ✅ `config/config.yml` 应在 `.gitignore` 中排除
4. ✅ 日志输出已脱敏（`sanitize_log_message` 隐藏 API Key）
5. ✅ 支持环境变量读取 API 密钥
6. ⚠️ **请勿将 config/config.yml 提交到公开仓库！**

### 如果已提交
立即轮换 API 密钥，各平台密钥重置入口：
- 智谱 AI: https://open.bigmodel.cn/usercenter/apikeys
- DeepSeek: https://platform.deepseek.com/api_keys
- 豆包: https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey
- 通义千问: https://dashscope.console.aliyun.com/apiKey

### 开发安全
- 不要在代码中硬编码 API 密钥
- 优先使用环境变量 `{PROVIDER}_API_KEY`
- 代码中的占位符检测支持中英文（`你的` / `your` / `your_key`）
- 日志输出自动脱敏

**最后更新**：2026-04-28
