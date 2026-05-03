# 依赖管理说明

## 依赖锁定文件

### 文件说明

#### requirements.in
- **用途**: 定义项目依赖的顶层需求
- **内容**: 只包含直接依赖，不包含版本号（或只指定最低版本）
- **维护**: 手动维护，添加新依赖时更新此文件

#### requirements.txt
- **用途**: 开发环境使用的依赖文件
- **内容**: 包含所有依赖及其版本范围
- **维护**: 手动维护，定期更新

#### requirements.lock
- **用途**: 生产环境使用的锁定文件
- **内容**: 包含所有依赖的精确版本号
- **维护**: 自动生成，不要手动修改

### 使用方法

#### 开发环境
```bash
pip install -r requirements.txt
```

#### 生产环境
```bash
pip install -r requirements.lock
```

#### 更新依赖
```bash
# 方法1: 使用pip-tools（推荐）
pip install pip-tools
pip-compile requirements.in --output-file requirements.lock

# 方法2: 使用pip freeze
pip freeze > requirements.lock
```

## JavaScript解析库依赖

### esprima

**包名**: `esprima>=4.0.1`

**用途**: JavaScript AST解析（脚本汉化必需）

**选择原因**:
1. 高性能、标准兼容的ECMAScript解析器
2. 支持ECMAScript 2017 (ECMA-262 8th Edition)
3. 遵循ESTree项目标准化的语法树格式
4. 实验性支持JSX语法
5. 大量单元测试覆盖，稳定可靠

**使用位置**: `core/script_translation.py`

**导入方式**:
```python
import esprima

# 词法分析（tokenization）
tokens = esprima.tokenize(program)

# 句法分析（parsing）
ast = esprima.parseScript(program)
```

**版本说明**:
- 当前最低版本: 4.0.1
- 支持ECMAScript 2017标准
- 可选更新版本（如可用）

**备选方案**:
- `esprima-fork>=4.0.4`: 社区fork版本，可能包含更多更新
- `tree-sitter`: 更活跃的解析器，但需要额外配置

## NBT库依赖选择

### 当前选择：mcstructure

**包名**: `mcstructure>=0.0.1b6`

**用途**: Minecraft基岩版.mcstructure文件读写

**选择原因**:
1. 专门为Minecraft基岩版设计
2. 直接支持.mcstructure文件格式
3. 提供Structure和Block类，便于操作

**使用位置**: `core/use_cases/translate_mcstructure.py`

**导入方式**:
```python
from mcstructure import NBTFile
```

### 备选方案：pynbt

**包名**: `pynbt>=2.0.0`

**用途**: Minecraft NBT结构文件解析（通用NBT库）

**保留原因**:
1. Python NBT常用库，稳定可靠
2. 支持little-endian（基岩版需要）
3. 作为mcstructure的备选方案
4. 未来可能用于其他NBT文件处理

**API示例**:
```python
from pynbt import NBTFile

# 读取NBT文件
with open('file.nbt', 'rb') as f:
    nbt = NBTFile(f)

# 保存NBT文件
with open('output.nbt', 'wb') as f:
    nbt.save(f)
```

### 依赖冲突解决

**问题**:
- requirements.txt声明了pynbt>=2.0.0
- 代码实际使用的是mcstructure库
- mcstructure未在依赖中声明
- pynbt未被使用

**解决方案**:
1. ✅ 在requirements.txt中添加mcstructure>=0.0.1b6
2. ✅ 保留pynbt作为备选方案
3. ✅ 更新依赖说明文档
4. ✅ 更新esprima版本为>=4.0.1以接受更新版本

### 安装说明

```bash
# 安装所有依赖
pip install -r requirements.txt

# 仅安装JavaScript解析相关依赖
pip install esprima>=4.0.1

# 仅安装mcstructure相关依赖
pip install mcstructure>=0.0.1b6 pynbt>=2.0.0 numpy>=2.0.0
```

### 注意事项

1. **esprima版本**: 支持ECMAScript 2017，对于现代JavaScript语法可能需要更新
2. **mcstructure版本**: 当前为beta版本（0.0.1b6），API可能变化
3. **pynbt备选**: 如果mcstructure出现问题，可以切换到pynbt
4. **numpy依赖**: 用于NBT文件操作辅助

### 相关文件

- `requirements.txt` - 依赖声明
- `core/script_translation.py` - JavaScript解析实现
- `core/use_cases/translate_mcstructure.py` - mcstructure功能实现
- `docs/DEPENDENCY_NOTES.md` - 本文档
