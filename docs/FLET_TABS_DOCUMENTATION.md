# Flet 0.84+ Tabs 组件官方文档

## 重要变更（从旧版本迁移）

### ⚠️ 重大API变化

**旧版本 (Flet < 0.84)**:
```python
ft.Tabs(
    selected_index=0,
    tabs=[
        ft.Tab(text="Tab 1"),
        ft.Tab(text="Tab 2"),
    ],
)
```

**新版本 (Flet 0.84+)**:
```python
ft.Tabs(
    selected_index=0,
    length=2,
    content=ft.Column(
        controls=[
            ft.TabBar(
                tabs=[
                    ft.Tab(label="Tab 1"),  # text → label
                    ft.Tab(label="Tab 2"),
                ],
            ),
            ft.TabBarView(
                controls=[
                    content_1,
                    content_2,
                ],
            ),
        ],
    ),
)
```

## 本项目的 Flet API 使用规范

本项目已完成 Flet 0.84+ 迁移，使用以下规范：

| 旧 API (已移除/弃用) | 新 API (当前) |
|----------------------|--------------|
| `ft.border.all()` | `ft.Border.all()` |
| `ft.padding.only()` | `ft.Padding(top=, bottom=, left=, right=)` |
| `ft.margin.only()` | `ft.Margin(top=, bottom=, left=, right=)` |
| `ft.app(target=main)` | `ft.run(main=main)` |
| `page.dialog = dlg; page.dialog.open = True` | `page.open(dlg)` 或 `page.show_dialog(dlg)` |
| `page.close_dialog()` | `page.pop_dialog()` |
| `ft.Tab(text=...)` | `ft.Tab(label=...)` |
| `page.run_task(lambda: ...)` | `page.run_task(async_def_func)` |
| `ft.TextStyle(size=...)` | `ft.TextStyle(size=...)` (仍有效) |

### 弃用 API 自动检查

运行 `python scripts/check_flet_deprecated.py` 扫描全部 Python 文件，或通过 `pre-commit` 钩子自动执行。

---

**文档来源**: https://flet.dev/docs/controls/tabs  
**更新时间**: 2026-04-28  
**适用版本**: Flet 0.84+
