# 开源说明

## 许可证
本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献指南
1. **Fork 仓库**
2. **创建分支**：`git checkout -b feature/your-feature`
3. **提交修改**：`git commit -m "Add your feature"`
4. **推送分支**：`git push origin feature/your-feature`
5. **创建 Pull Request**

## 代码规范
- 遵循 PEP 8 代码风格
- 使用类型提示
- 添加适当的注释
- 保持代码简洁明了

## 安全注意事项
- API 密钥存储在 `config/config.yml` 中，已被 `.gitignore` 忽略
- 不要在代码中硬编码 API 密钥
- 定期更新 API 密钥
- 遵循各 API 提供商的使用条款

## 开发环境设置
1. 克隆仓库：`git clone https://github.com/yourusername/MinecraftBedrockLocalizer.git`
2. 创建虚拟环境：`python -m venv .venv`
3. 激活虚拟环境：`source .venv/bin/activate` (Linux/Mac) 或 `.venv\Scripts\activate` (Windows)
4. 安装依赖：`pip install -r requirements.txt`
5. 运行测试：`pytest`

## 发布流程
1. 更新版本号
2. 运行测试：`pytest`
3. 构建应用：`pyinstaller "我的世界基岩版 汉化提取＆替换 工具.spec"`
4. 发布到 GitHub Releases
