# 代码签名与杀毒软件误报应对指南

## 问题背景

PyInstaller 打包的 Windows 可执行程序常被杀毒软件误报为恶意软件，原因包括：
- 自解压行为（解压到 `%TEMP%` 目录）
- 动态加载模块
- 无代码签名
- 行为特征与恶意软件相似

## 解决方案

### 方案一：获取代码签名证书（推荐）

#### 1. 购买代码签名证书

**标准代码签名证书（~$200-400/年）：**
- DigiCert: https://www.digicert.com/signing/code-signing-certificates
- Sectigo: https://sectigo.com/ssl-certificates-tls/code-signing
- GlobalSign: https://www.globalsign.com/en/code-signing-certificate

**EV 代码签名证书（~$400-800/年，更可信）：**
- 需要硬件令牌（USB Key）
- SmartScreen 立即信任
- 适用于企业发布

#### 2. 签名流程

```powershell
# 安装 Windows SDK（包含 signtool.exe）
# 或使用 Visual Studio 自带的 signtool

# 标准签名
signtool sign /f "证书路径.pfx" /p "密码" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\Setup.exe"

# EV 证书签名（使用硬件令牌）
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\Setup.exe"
```

#### 3. CI/CD 集成

在 GitHub Actions 中添加签名步骤：

```yaml
- name: Sign executable
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: |
    signtool sign /f ${{ secrets.CERTIFICATE_PATH }} `
      /p ${{ secrets.CERTIFICATE_PASSWORD }} `
      /tr http://timestamp.digicert.com `
      /td sha256 /fd sha256 `
      "dist\MinecraftBedrockLocalizerSetup_v${{ steps.version.outputs.version }}.exe"
```

**注意：** 证书文件应存储在 GitHub Secrets 中，不要提交到仓库。

### 方案二：Microsoft SmartScreen 注册（免费）

#### 1. 注册 Microsoft 开发者账户

访问 https://partner.microsoft.com/dashboard 注册开发者账户。

#### 2. 提交应用进行认证

1. 上传应用文件
2. 提供应用信息和截图
3. 等待 Microsoft 审核（通常 1-3 天）

#### 3. 获取信誉

- 用户下载并安装后，SmartScreen 会逐步建立信任
- 初期仍可能显示警告，但会随下载量增加而减少

### 方案三：用户端解决方案（临时）

#### 向用户说明

1. **Windows Defender SmartScreen 警告：**
   - 点击"更多信息"
   - 点击"仍要运行"

2. **360/腾讯管家等警告：**
   - 选择"允许"或"添加信任"
   - 将程序添加到白名单

3. **企业环境：**
   - 联系 IT 管理员添加例外规则

#### 提供校验和

在 Release 页面提供 SHA256 校验和：

```bash
# 生成校验和
certutil -hashfile "dist\Setup.exe" SHA256 > SHA256.txt

# 或使用 PowerShell
Get-FileHash "dist\Setup.exe" -Algorithm SHA256 | Select-Object Hash > SHA256.txt
```

用户可以验证下载文件的完整性。

## 最佳实践

### 1. 构建环境

- 使用干净的构建机器
- 固定依赖版本（使用 `requirements-lock.txt`）
- 记录构建日志

### 2. 发布流程

1. 构建可执行文件
2. 对文件进行签名
3. 生成校验和
4. 上传到 GitHub Releases
5. 在 Release 说明中提供校验和

### 3. 用户沟通

在 README 和 Release 说明中明确说明：
- 为什么会出现杀毒软件警告
- 如何验证文件完整性
- 如何添加信任

## 参考链接

- [Microsoft SmartScreen 信誉](https://docs.microsoft.com/en-us/windows/security/threat-protection/microsoft-defender-smartscreen/)
- [代码签名最佳实践](https://www.digicert.com/blog/best-practices-for-code-signing-certificates)
- [PyInstaller 打包与杀毒软件](https://github.com/pyinstaller/pyinstaller/wiki/How-to-avoid-SmartScreen-warnings)

## 当前状态

本项目目前**未进行代码签名**，因此：
- Windows SmartScreen 可能显示警告
- 部分杀毒软件可能误报

**解决方案：**
- 用户需要手动确认信任
- 建议从 GitHub Releases 官方渠道下载
- 验证 SHA256 校验和（如有提供）
