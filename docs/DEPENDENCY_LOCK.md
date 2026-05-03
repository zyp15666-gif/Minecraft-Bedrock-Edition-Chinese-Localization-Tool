# 依赖锁定文件说明

## 文件说明

### requirements.in
- **用途**: 定义项目依赖的顶层需求
- **内容**: 只包含直接依赖，不包含版本号（或只指定最低版本）
- **维护**: 手动维护，添加新依赖时更新此文件

### requirements.txt
- **用途**: 开发环境使用的依赖文件
- **内容**: 包含所有依赖及其版本范围
- **维护**: 手动维护，定期更新

### requirements.lock
- **用途**: 生产环境使用的锁定文件
- **内容**: 包含所有依赖的精确版本号
- **维护**: 自动生成，不要手动修改

## 使用方法

### 开发环境

```bash
# 安装开发依赖
pip install -r requirements.txt
```

### 生产环境

```bash
# 安装精确版本的依赖
pip install -r requirements.lock
```

### 更新依赖

```bash
# 方法1: 使用pip-tools（推荐）
pip install pip-tools
pip-compile requirements.in --output-file requirements.lock

# 方法2: 使用pip freeze
pip freeze > requirements.lock
```

### 添加新依赖

1. 在`requirements.in`中添加新依赖
2. 运行`pip-compile requirements.in --output-file requirements.lock`
3. 提交`requirements.in`和`requirements.lock`到版本控制

## CI/CD集成

在CI/CD流水线中使用锁定文件：

```yaml
# GitHub Actions示例
- name: Install dependencies
  run: pip install -r requirements.lock

# 或者在CI中生成锁定文件
- name: Generate lock file
  run: pip freeze > requirements.lock
```

## 版本控制

**应该提交的文件**:
- ✅ requirements.in
- ✅ requirements.txt
- ✅ requirements.lock

**不应该提交的文件**:
- ❌ venv/ (虚拟环境目录)
- ❌ __pycache__/ (Python缓存)

## 最佳实践

1. **开发时**: 使用`requirements.txt`，允许版本范围
2. **部署时**: 使用`requirements.lock`，确保版本一致
3. **更新时**: 定期更新锁定文件，确保安全补丁
4. **测试时**: 在CI中使用锁定文件，确保环境一致

## 依赖分类

### 核心依赖
- flet: UI框架
- pyyaml: YAML配置文件解析
- requests: HTTP请求
- tqdm: 进度条
- esprima: JavaScript解析

### 可选依赖（性能优化）
- json5: JSON5格式支持
- screeninfo: 屏幕信息
- pyahocorasick: 术语匹配加速
- jieba: 中文分词
- psutil: 系统信息
- pynbt: NBT文件解析
- numpy: 数值计算
- aiohttp: 异步HTTP
- cachetools: LRU缓存
- mcstructure: Minecraft结构文件

## 故障排除

### 问题: 版本冲突
```bash
# 清除缓存并重新安装
pip cache purge
pip install -r requirements.lock --force-reinstall
```

### 问题: 依赖安装失败
```bash
# 检查Python版本
python --version

# 升级pip
python -m pip install --upgrade pip

# 重新安装
pip install -r requirements.lock
```

## 相关文档

- [pip-tools文档](https://github.com/jazzband/pip-tools)
- [Python依赖管理最佳实践](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
