#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esprima版本兼容性测试

测试esprima 4.0.1是否兼容现有代码
"""

import esprima


def test_basic_parsing():
    """测试基本的JavaScript解析"""
    program = 'const answer = 42'

    # 词法分析
    tokens = esprima.tokenize(program)
    assert len(tokens) == 4
    print("✅ 词法分析测试通过")

    # 句法分析
    ast = esprima.parseScript(program)
    assert hasattr(ast, 'type') and ast.type == 'Program'
    print("✅ 句法分析测试通过")

def test_minecraft_script():
    """测试Minecraft脚本解析"""
    # 模拟Minecraft基岩版脚本
    script = """
    system.runInterval(() => {
        const players = world.getAllPlayers();
        for (const player of players) {
            player.runCommand("say Hello");
        }
    });
    """

    try:
        esprima.parseScript(script)
        print("✅ Minecraft脚本解析测试通过")
        return True
    except Exception as e:
        print(f"❌ Minecraft脚本解析测试失败: {e}")
        return False

def test_modern_js_features():
    """测试现代JavaScript特性支持"""
    # ES6+ 特性
    features = [
        "const func = () => {}",  # 箭头函数
        "const {a, b} = obj",     # 解构赋值
        "const arr = [...items]", # 展开运算符
        "class MyClass {}",       # 类定义
        "async function f() {}",  # async/await
    ]

    all_passed = True
    for feature in features:
        try:
            esprima.parseScript(feature)
            print(f"✅ 支持: {feature}")
        except Exception as e:
            print(f"❌ 不支持: {feature} - {e}")
            all_passed = False

    return all_passed

if __name__ == "__main__":
    print("=" * 60)
    print("esprima版本兼容性测试")
    print("=" * 60)
    print(f"esprima版本: {esprima.__version__}")
    print()

    test_basic_parsing()
    print()

    test_minecraft_script()
    print()

    test_modern_js_features()
    print()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)
