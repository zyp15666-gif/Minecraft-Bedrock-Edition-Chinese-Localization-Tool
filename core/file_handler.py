#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件处理模块
支持并行读取和解析JSON文件，提高处理速度
"""
import re
import os
import json
import shutil
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple

from core.log_manager import get_logger
from core.utils import is_protected_system_path, is_lang_key_format

logger = get_logger(__name__)


def _parse_json_file_worker(filepath_str: str) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    """进程池worker函数 - 必须在模块级别定义以便pickle

    Args:
        filepath_str: 文件路径字符串

    Returns:
        (文件路径字符串, 解析后的JSON数据或None, 错误信息或None)
    """
    try:
        with open(filepath_str, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return (filepath_str, data, None)
    except Exception as e:
        return (filepath_str, None, str(e))


class FileHandler:
    """文件处理器"""

    BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S_%f"

    def __init__(self, config: Dict[str, Any]):
        """初始化文件处理器"""
        self.config = config
        self.namespace = config.get("basic", {}).get("namespace", "sgs_farm")
        self.indent = config.get("basic", {}).get("indent", 4)

    def validate_operation_path(self, path: str) -> Tuple[bool, str]:
        """验证操作目标路径是否安全

        检查路径是否位于受保护的系统目录中，防止误操作。

        Args:
            path: 待验证的路径

        Returns:
            (is_safe, error_message) 二元组
        """
        if not path:
            return False, "路径为空"
        if is_protected_system_path(path):
            return False, f"路径 '{path}' 位于系统保护目录中，禁止操作"
        return True, ""

    def select_folder(self, title: str) -> str:
        """选择文件夹"""
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder_selected = filedialog.askdirectory(title=title)
            root.destroy()
            return folder_selected
        except Exception as e:
            logger.error(f"选择文件夹失败: {e}")
            return ""

    def select_file(self, title: str, filetypes: List[tuple]) -> str:
        """选择文件"""
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_selected = filedialog.askopenfilename(
                title=title, filetypes=filetypes)
            root.destroy()
            return file_selected
        except Exception as e:
            logger.error(f"选择文件失败: {e}")
            return ""

    def backup_folder(self, folder_path: str) -> str:
        """备份文件夹"""
        if not folder_path or not os.path.exists(folder_path):
            return ""

        is_safe, error_msg = self.validate_operation_path(folder_path)
        if not is_safe:
            logger.error(f"❌ 备份失败：{error_msg}")
            return ""

        timestamp = datetime.now().strftime(self.BACKUP_TIMESTAMP_FORMAT)
        backup_to = f"{folder_path}_BACKUP_{timestamp}"

        try:
            shutil.copytree(folder_path, backup_to, dirs_exist_ok=True)
            logger.info(f"✅ 备份完成 → {backup_to}")
            return backup_to
        except Exception as e:
            logger.error(f"❌ 备份失败：{e}")
            return ""

    def update_manifest_metadata(self, bp_folder: str, rp_folder: str, translator=None):
        """
        自动修改 BP 和 RP 目录下的 manifest.json：
        - header.name = 文件夹名称的中文翻译（AI 翻译）
        - header.description = 固定的作者信息（从配置读取）
        """
        author_config = self.config.get("author", {})
        author_name = author_config.get("name", "Minecraft基岩版汉化工具")
        author_desc = author_config.get(
            "description",
            f"由 {author_name} 自动生成"
        )

        def process_single_manifest(folder_path: str, pack_type: str) -> bool:
            """处理单个 manifest.json 文件"""
            try:
                manifest_path = os.path.join(folder_path, "manifest.json")
                if not os.path.isfile(manifest_path):
                    logger.warning(f"⚠️ {pack_type} 目录下未找到 manifest.json，跳过")
                    return False

                backup_path = manifest_path + ".bak"
                shutil.copy2(manifest_path, backup_path)
                logger.info(f"💾 已备份 {pack_type} manifest → {backup_path}")

                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)

                if "header" not in manifest_data:
                    logger.error(f"❌ {pack_type} manifest.json 缺少 'header' 字段，跳过")
                    return False

                original_name = os.path.basename(folder_path)
                logger.info(f"📁 {pack_type} 原始文件夹名: {original_name}")

                if translator:
                    try:
                        logger.info(f"🌐 正在翻译 {pack_type} 文件夹名称...")
                        translated_dict = translator.translate_entries({"name": original_name})
                        translated_name = translated_dict.get("name", original_name)
                        manifest_data["header"]["name"] = translated_name
                        logger.info(f"✅ {pack_type} header.name 已翻译为: {translated_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ 翻译失败: {str(e)}，保留原始文件夹名")
                        manifest_data["header"]["name"] = original_name
                else:
                    logger.warning(f"⚠️ 无可用翻译器，保留原始文件夹名作为 name")
                    manifest_data["header"]["name"] = original_name

                manifest_data["header"]["description"] = author_desc
                logger.info(f"📝 {pack_type} header.description 已设置为: {author_desc[:50]}...")

                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ {pack_type} manifest.json 已更新")
                return True
            except Exception as e:
                logger.error(f"❌ 处理 {pack_type} manifest 时出错: {str(e)}")
                return False

        if bp_folder:
            process_single_manifest(bp_folder, "BP")
        if rp_folder:
            process_single_manifest(rp_folder, "RP")

    def merge_and_write_lang(self, folder: str, new_entries: Dict[str, str], is_translated: bool = False, expected_count: int = 0):
        """合并并写入语言文件，含完整性校验"""
        if not folder:
            return

        os.makedirs(folder, exist_ok=True)
        texts_dir = os.path.join(folder, "texts")
        os.makedirs(texts_dir, exist_ok=True)
        lang_path = os.path.join(texts_dir, "zh_CN.lang")

        existing = {}
        if os.path.exists(lang_path):
            with open(lang_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        k, v = line.split('=', 1)
                        existing[k] = v

        old_count = len(existing)
        existing.update(new_entries)
        new_count = len(existing)

        not_translated = sum(1 for v in existing.values() if v and not any('\u4e00' <= c <= '\u9fff' for c in v))
        if is_translated and expected_count > 0 and not_translated > 0:
            logger.warning(f"⚠️ 翻译完整性警告: {not_translated}/{new_count} 条可能未正确汉化")

        with open(lang_path, 'w', encoding='utf-8') as f:
            for key in sorted(existing.keys()):
                value = existing[key].replace('\n', '\\n')
                f.write(f"{key}={value}\n")

        action = "翻译" if is_translated else "提取"
        logger.info(f"📄 {action}完成 → {lang_path} (原有 {old_count} + 新增 {len(new_entries)} = 共 {new_count} 条)")

    def ensure_languages_json(self, folder: str):
        """确保languages.json中包含zh_CN"""
        if not folder or not os.path.exists(folder):
            return

        texts_dir = os.path.join(folder, "texts")
        os.makedirs(texts_dir, exist_ok=True)
        lang_json_path = os.path.join(texts_dir, "languages.json")

        if os.path.exists(lang_json_path):
            try:
                with open(lang_json_path, 'r', encoding='utf-8') as f:
                    langs = json.load(f)
            except (json.JSONDecodeError, Exception):
                langs = []
        else:
            langs = []

        if "zh_CN" not in langs:
            langs.append("zh_CN")
            with open(lang_json_path, 'w', encoding='utf-8') as f:
                json.dump(langs, f, indent=2)
            logger.info(f"📝 已更新 {lang_json_path}，添加 zh_CN")

    def _extract_entry_from_json(self, data: dict, ident_key: str, prefix: str) -> Optional[Tuple[str, str]]:
        """从 JSON 数据中提取标准 minecraft:display_name，跳过语言键引用和纯格式代码"""
        ident = data.get(ident_key, {}).get("description", {}).get("identifier", "")
        if not ident:
            return None
        components = data.get(ident_key, {}).get("components", {})
        dn = components.get("minecraft:display_name", "")
        original = ""
        skip_reason = ""
        
        if isinstance(dn, dict) and "value" in dn:
            raw_value = dn["value"]
            # 检查 value 内容是否为语言键引用
            if isinstance(raw_value, str) and raw_value.strip():
                stripped = raw_value.strip()
                if stripped.startswith('%'):
                    original = ""
                    skip_reason = f"value 内是语言键引用 (以%开头)"
                elif is_lang_key_format(stripped):
                    original = ""
                    skip_reason = f"value 内是语言键格式"
                else:
                    original = raw_value
            else:
                original = raw_value
        elif isinstance(dn, str) and dn.strip():
            stripped = dn.strip()
            # 过滤1：以 % 开头的语言键引用
            if stripped.startswith('%'):
                original = ""
                skip_reason = f"语言键引用 (以%开头)"
            # 过滤2：纯语言键格式
            elif is_lang_key_format(stripped):
                original = ""
                skip_reason = f"语言键格式"
            # 过滤3：仅由单个完整 § 格式代码组成
            elif re.fullmatch(r'[§\u00A7][0-9a-fk-or]', stripped):
                original = ""
                skip_reason = f"纯格式代码"
            # 过滤4：移除所有有效 § 代码后不剩下任何普通字母
            elif not any(c.isalpha() and c.lower() >= 'a' for c in re.sub(r'[§\u00A7][0-9a-fk-or]', '', stripped).replace('%', '')):
                original = ""
                skip_reason = f"移除格式代码后无有效文本"
            else:
                original = dn

        if original and ident:
            print(f"[DEBUG 第1层] ✓ 提取: {prefix}.{ident}.name")
            return (f"{prefix}.{ident}.name", original)
        elif ident:
            print(f"[DEBUG 第1层] ✗ 跳过: {ident} ({skip_reason})")
        return None

    def extract_entries(self, bp_folder: str) -> Dict[str, str]:
        """三层提取：标准组件 + 战利品表书籍 + 自适应 § 扫描"""
        lang_entries = {}
        bp_path = Path(bp_folder)
        json_files = list(bp_path.rglob("*.json"))
        if not json_files:
            print("[DEBUG] 未找到任何 JSON 文件")
            return lang_entries

        print(f"[DEBUG] 开始三层提取，共发现 {len(json_files)} 个 JSON 文件")

        # 用于第3层去重的路径集合
        extracted_paths = set()

        results = self.read_json_files_parallel(json_files)

        # 第1层 + 第2层
        for filepath, data in results:
            if data is None:
                continue
            try:
                # ----- 第1层：标准 display_name 提取 -----
                for ident_key, prefix in [("minecraft:block", "tile"), ("minecraft:item", "item")]:
                    if ident_key in data:
                        result = self._extract_entry_from_json(data, ident_key, prefix)
                        if result:
                            key, original = result
                            if key not in lang_entries:
                                lang_entries[key] = original
                                extracted_paths.add(
                                    (str(filepath), (ident_key, "components", "minecraft:display_name"))
                                )

                # ----- 第2层：战利品表书籍内容提取 -----
                book_entries = self._extract_book_contents(data, str(filepath))
                if book_entries:
                    print(f"[DEBUG 第2层] ✓ 提取书籍 {Path(filepath).stem}: {len(book_entries)} 条")
                for key, original in book_entries.items():
                    if key not in lang_entries:
                        lang_entries[key] = original

                # 记录书籍页面路径
                if "pools" in data:
                    for pi, pool in enumerate(data["pools"]):
                        for ei, entry in enumerate(pool.get("entries", [])):
                            for fi, func in enumerate(entry.get("functions", [])):
                                if func.get("function") == "set_book_contents":
                                    for i in range(len(func.get("pages", []))):
                                        extracted_paths.add(
                                            (str(filepath),
                                            ("pools", pi, "entries", ei, "functions", fi, "pages", i))
                                        )
            except Exception as e:
                logger.error(f"提取失败 {filepath.name}: {e}")
                print(f"[DEBUG] 提取失败 {filepath.name}: {e}")

        # ----- 第3层：自适应 § 扫描 -----
        for filepath, data in results:
            if data is None:
                continue
            try:
                color_entries = self._extract_color_code_strings(
                    data, str(filepath), bp_folder, extracted_paths
                )
                if color_entries:
                    print(f"[DEBUG 第3层] ✓ 自适应扫描 {Path(filepath).name}: 发现 {len(color_entries)} 个新条目")
                for key, original in color_entries.items():
                    if key not in lang_entries:
                        lang_entries[key] = original
            except Exception as e:
                logger.error(f"自适应扫描失败 {filepath.name}: {e}")
                print(f"[DEBUG] 自适应扫描失败 {filepath.name}: {e}")
        print(f"[DEBUG] 三层提取完成，共提取 {len(lang_entries)} 个条目")
        return lang_entries


    def _extract_book_contents(self, data: dict, filepath: str) -> Dict[str, str]:
        """从战利品表中提取 set_book_contents 的 title、author、pages"""
        entries = {}
        if "pools" not in data:
            return entries

        file_stem = Path(filepath).stem

        for pi, pool in enumerate(data["pools"]):
            for ei, entry in enumerate(pool.get("entries", [])):
                for fi, func in enumerate(entry.get("functions", [])):
                    if func.get("function") != "set_book_contents":
                        continue
                    prefix = f"book.{file_stem}.pools.{pi}.entries.{ei}.functions.{fi}"
                    if "title" in func:
                        key = f"{prefix}.title"
                        entries[key] = func["title"]
                    if "author" in func:
                        key = f"{prefix}.author"
                        entries[key] = func["author"]
                    for i, page_text in enumerate(func.get("pages", [])):
                        key = f"{prefix}.pages.{i}"
                        entries[key] = page_text
        return entries
    def _is_lang_reference(self, text: str) -> bool:
        """判断文本是否为 % 开头的语言键引用（如 %tile.ntk.xxx）"""
        return bool(re.match(r'^%\w[\w.]*', text.strip()))

    def _extract_color_code_strings(self, data, filepath: str, bp_folder: str,
                                    extracted_paths: set) -> Dict[str, str]:
        entries = {}
        rel_path = os.path.relpath(filepath, bp_folder).replace('\\', '/').replace('/', '-')
        abs_path = str(filepath)  # 用于去重的绝对路径

        def scan(obj, path_parts):
            if isinstance(obj, str):
                if '§' in obj and not self._is_lang_reference(obj):
                    key = f"auto.{rel_path}." + '.'.join(str(p) for p in path_parts)
                    # 去重使用绝对路径 + 路径元组
                    path_tuple = (abs_path, tuple(path_parts))
                    if path_tuple not in extracted_paths and key not in entries:
                        entries[key] = obj
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan(v, path_parts + [k])
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    scan(v, path_parts + [str(i)])

        scan(data, [])
        return entries



    def parse_lang_file(self, filepath: str) -> Dict[str, str]:
        """解析lang文件"""
        entries = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip().replace('\\n', '\n')
                    entries[key.strip()] = value
        return entries

    def remove_value_from_json(self, data: Any) -> Any:
        """递归删除display_name的value对象转为字符串"""
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if key == "minecraft:display_name":
                    if isinstance(value, dict) and "value" in value:
                        data[key] = value["value"]
                else:
                    self.remove_value_from_json(value)
        elif isinstance(data, list):
            for item in data:
                self.remove_value_from_json(item)
        return data

    def restore_value_to_json(self, data: Any) -> Any:
        """递归还原display_name的字符串转为value对象格式"""
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if key == "minecraft:display_name":
                    if isinstance(value, str):
                        data[key] = {"value": value}
                else:
                    self.restore_value_to_json(value)
        elif isinstance(data, list):
            for item in data:
                self.restore_value_to_json(item)
        return data

    def remove_value_from_json_folder(self, folder_path: str):
        """批量删除文件夹内所有JSON文件的value字段（转为字符串格式）"""
        import os
        total = 0
        success = 0

        for root, _, files in os.walk(folder_path):
            for filename in files:
                if not filename.lower().endswith(".json"):
                    continue

                filepath = os.path.join(root, filename)
                total += 1

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    data = self.remove_value_from_json(data)

                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False,
                                  indent=self.indent)

                    success += 1
                except Exception as e:
                    logger.error(f"处理 {filename} 失败: {e}")

        return success

    def restore_value_to_json_folder(self, folder_path: str):
        """批量还原文件夹内所有JSON文件的value字段（转为对象格式）"""
        import os
        total = 0
        success = 0

        for root, _, files in os.walk(folder_path):
            for filename in files:
                if not filename.lower().endswith(".json"):
                    continue

                filepath = os.path.join(root, filename)
                total += 1

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    data = self.restore_value_to_json(data)

                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False,
                                  indent=self.indent)

                    success += 1
                except Exception as e:
                    logger.error(f"处理 {filename} 失败: {e}")

        return success

    def replace_display_names_with_lang_key(self, bp_folder: str):
        """全BP批量替换display_name为对象格式的lang键"""
        import os
        import json
        
        total = 0
        success = 0

        for root, _, files in os.walk(bp_folder):
            for filename in files:
                if not filename.lower().endswith(".json"):
                    continue

                filepath = os.path.join(root, filename)
                total += 1
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    modified = False
                    
                    # 查找 minecraft:block 或 minecraft:item 节点
                    for pack_type in ["minecraft:block", "minecraft:item"]:
                        if pack_type in data and isinstance(data[pack_type], dict):
                            block_item = data[pack_type]
                            description = block_item.get("description", {})
                            identifier = description.get("identifier", "")
                            
                            if not identifier or ":" not in identifier:
                                continue
                                
                            item_id = identifier.split(":")[-1]
                            if pack_type == "minecraft:block":
                                lang_key = f"tile.{self.namespace}:{item_id}.name"
                            else:
                                lang_key = f"item.{self.namespace}:{item_id}.name"
                            
                            components = block_item.get("components", {})
                            if "minecraft:display_name" in components:
                                # 无论原值是字符串还是对象，统一替换为标准的对象格式
                                components["minecraft:display_name"] = {"value": lang_key}
                                modified = True
                                # 确保 components 字典写回 block_item
                                block_item["components"] = components
                    
                    # 如果修改了数据，写回文件
                    if modified:
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=self.indent)
                        success += 1
                        logger.info(f"✅ {filename} → 已替换为对象格式的lang键")
                    else:
                        logger.debug(f"⏭️ {filename} → 未找到需要替换的display_name")

                except Exception as e:
                    logger.error(f"❌ {filename} → 错误：{str(e)}")

        logger.info(f"\n🎯 全BP替换完成：总计 {total} 个文件 | 成功 {success} 个文件被修改")
        return success

    def extract_entity_display_names(self, bp_folder: str) -> Dict[str, List[str]]:
        """扫描BP/entities子文件夹中的实体JSON，生成entity.<identifier>.name条目

        Args:
            bp_folder: BP文件夹路径

        Returns:
            Dict[str, List[str]]: 基础名称到语言键列表的映射
        """
        import json

        entities_root = Path(bp_folder) / "entities"
        if not entities_root.is_dir():
            logger.error(f"❌ BP文件夹下没有 'entities' 目录: {entities_root}")
            return {}

        # 收集所有实体JSON文件（包括entities根目录和所有子文件夹）
        json_files = []
        # 扫描根目录
        for file in entities_root.iterdir():
            if file.suffix.lower() == ".json" and file.is_file():
                json_files.append(file)
        # 扫描子文件夹
        for entry in entities_root.iterdir():
            if entry.is_dir():
                for json_file in entry.rglob("*.json"):
                    if json_file.is_file():
                        json_files.append(json_file)

        if not json_files:
            logger.warning("⚠️ 未在 entities 目录及其子文件夹中找到任何 JSON 文件")
            return {}

        logger.info(f"📂 找到 {len(json_files)} 个实体 JSON 文件，正在解析...")

        base_names_to_translate = set()
        entity_info = []

        for filepath in json_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                identifier = data.get("minecraft:entity", {}).get(
                    "description", {}).get("identifier")
                if not identifier or not isinstance(identifier, str) or ":" not in identifier:
                    logger.warning(f"⚠️ 跳过无效 identifier: {filepath}")
                    continue

                entity_name = identifier.split(":", 1)[1]
                is_male = entity_name.endswith("_m")
                base_name = entity_name[:-2] if is_male else entity_name

                lang_key = f"entity.{identifier}.name"
                entity_info.append((lang_key, base_name, is_male))
                base_names_to_translate.add(base_name)

            except Exception as e:
                logger.error(f"❌ 解析 {filepath} 失败: {e}")

        if not entity_info:
            logger.warning("⚠️ 没有提取到任何有效的实体信息")
            return {}

        # 生成最终语言条目（返回基础名和键，由调用者处理翻译）
        base_name_dict = {}
        for lang_key, base_name, _ in entity_info:
            if base_name not in base_name_dict:
                base_name_dict[base_name] = []
            base_name_dict[base_name].append(lang_key)

        return base_name_dict

    def _read_json_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """读取单个JSON文件
        
        Args:
            filepath: JSON文件路径
            
        Returns:
            JSON数据，如果读取失败返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ 读取 {filepath} 失败: {e}")
            return None

    def read_json_files_parallel(
        self,
        filepaths: List[Path],
        max_workers: Optional[int] = None
    ) -> List[Tuple[Path, Optional[Dict[str, Any]]]]:
        """并行读取多个JSON文件

        Args:
            filepaths: JSON文件路径列表
            max_workers: 最大并发数，默认为CPU核心数

        Returns:
            包含(文件路径, JSON数据)的列表，读取失败时数据为None
        """
        if not filepaths:
            return []

        if max_workers is None:
            max_workers = min(8, os.cpu_count() or 4)

        logger.info(f"📂 并行读取 {len(filepaths)} 个JSON文件，使用 {max_workers} 个线程...")

        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self._read_json_file, filepath): filepath
                for filepath in filepaths
            }

            for future in concurrent.futures.as_completed(future_to_path):
                filepath = future_to_path[future]
                try:
                    data = future.result()
                    results.append((filepath, data))
                except Exception as e:
                    logger.error(f"❌ 处理 {filepath} 时发生异常: {e}")
                    results.append((filepath, None))

        success_count = len([r for r in results if r[1] is not None])
        logger.info(f"✅ 并行读取完成，成功 {success_count}/{len(results)}")
        return results

    def read_json_files_with_process_pool(
        self,
        filepaths: List[Path],
        max_workers: Optional[int] = None
    ) -> List[Tuple[Path, Optional[Dict[str, Any]]]]:
        """使用进程池并行读取和解析JSON文件（适合CPU密集型任务）

        对于大量JSON文件，使用进程池可以更好地利用多核CPU。

        Args:
            filepaths: JSON文件路径列表
            max_workers: 最大进程数，默认为CPU核心数

        Returns:
            包含(文件路径, JSON数据)的列表，读取失败时数据为None
        """
        if not filepaths:
            return []

        if max_workers is None:
            max_workers = max(1, (os.cpu_count() or 4) - 1)

        logger.info(f"📂 进程池并行读取 {len(filepaths)} 个JSON文件，使用 {max_workers} 个进程...")

        results = []
        filepath_strs = [str(fp) for fp in filepaths]

        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_path = {
                    executor.submit(_parse_json_file_worker, fp_str): fp_str
                    for fp_str in filepath_strs
                }

                for future in concurrent.futures.as_completed(future_to_path):
                    fp_str = future_to_path[future]
                    try:
                        result_str, data, error = future.result()
                        if error:
                            logger.error(f"❌ 解析 {fp_str} 失败: {error}")
                            results.append((Path(fp_str), None))
                        else:
                            results.append((Path(fp_str), data))
                    except Exception as e:
                        logger.error(f"❌ 处理 {fp_str} 时发生异常: {e}")
                        results.append((Path(fp_str), None))
        except Exception as e:
            logger.error(f"❌ 进程池执行失败，回退到线程池: {e}")
            return self.read_json_files_parallel(filepaths, max_workers)

        success_count = len([r for r in results if r[1] is not None])
        logger.info(f"✅ 进程池并行读取完成，成功 {success_count}/{len(results)}")
        return results

    def scan_json_files_parallel(
        self, 
        folder_path: str,
        pattern: str = "*.json",
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tuple[Path, Dict[str, Any]]]:
        """并行扫描和解析文件夹中的JSON文件
        
        Args:
            folder_path: 文件夹路径
            pattern: 文件匹配模式，默认为"*.json"
            max_workers: 最大并发数
            progress_callback: 进度回调函数 (current, total)
            
        Returns:
            包含(文件路径, JSON数据)的列表
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            logger.error(f"❌ 文件夹不存在: {folder_path}")
            return []

        json_files = list(folder.rglob(pattern))
        total_files = len(json_files)

        if total_files == 0:
            logger.warning(f"⚠️ 在 {folder_path} 中未找到任何 {pattern} 文件")
            return []

        logger.info(f"📂 找到 {total_files} 个 {pattern} 文件，开始并行解析...")

        results = self.read_json_files_parallel(json_files, max_workers)

        valid_results = []
        for i, (filepath, data) in enumerate(results, 1):
            if data is not None:
                valid_results.append((filepath, data))
            if progress_callback:
                progress_callback(i, total_files)

        logger.info(f"✅ 并行扫描完成，成功解析 {len(valid_results)}/{total_files} 个文件")
        return valid_results



    def apply_hardcoded_translations(self, bp_folder: str, lang_entries: Dict[str, str]):
        """将二三层翻译结果硬编码写回原始JSON文件"""
        processed = 0
        errors = 0
        
        for key, translated_text in lang_entries.items():
            if not (key.startswith('book.') or key.startswith('auto.')):
                continue
            
            try:
                if key.startswith('book.'):
                    # 格式: book.{file_stem}.pools.{pi}.entries.{ei}.functions.{fi}.{field}[.pages.{page}]
                    parts = key.split('.')
                    # 提取文件名部分：book后面的第一个点之前是 'book'，然后文件名可能包含点？
                    # 我们规定文件名不含点，所以 parts[1] 是 file_stem。
                    file_stem = parts[1]
                    # 路径从 parts[2:] 开始，即 'pools', pi, 'entries', ei, ...
                    path_parts = []
                    i = 2
                    while i < len(parts):
                        seg = parts[i]
                        # 数组索引：尝试转为 int，若成功则为索引，否则为键
                        try:
                            path_parts.append(int(seg))
                        except ValueError:
                            path_parts.append(seg)
                        i += 1
                    
                    # 查找文件
                    filepath = self._find_loot_table_file(bp_folder, file_stem + '.json')
                    if not filepath:
                        logger.warning(f"找不到战利品表文件: {file_stem}.json")
                        errors += 1
                        continue
                    
                elif key.startswith('auto.'):
                    # 格式: auto.{rel_path_with_dashes}.{json_path_parts}
                    auto_part = key[len('auto.'):]
                    json_dot_index = auto_part.find('.json.')
                    if json_dot_index == -1:
                        logger.warning(f"无法解析auto键: {key}")
                        errors += 1
                        continue
                    
                    file_rel_part = auto_part[:json_dot_index + 5]  # 包含 .json
                    json_path_str = auto_part[json_dot_index + 6:]
                    file_rel = file_rel_part.replace('-', '/')
                    filepath = os.path.join(bp_folder, file_rel)
                    if not os.path.exists(filepath):
                        logger.warning(f"找不到文件: {filepath}")
                        errors += 1
                        continue
                    
                    # 解析路径
                    path_parts = []
                    for seg in json_path_str.split('.'):
                        try:
                            path_parts.append(int(seg))
                        except ValueError:
                            path_parts.append(seg)
                else:
                    continue
                
                # 应用修改
                self._set_json_value(filepath, path_parts, translated_text)
                processed += 1
                
            except Exception as e:
                logger.error(f"应用翻译失败 [{key}]: {e}")
                errors += 1
        
        logger.info(f"硬编码汉化完成：成功 {processed} 条，失败 {errors} 条")
        return processed
    def _find_loot_table_file(self, bp_folder: str, filename: str) -> Optional[str]:
        """在BP中搜索指定的战利品表文件"""
        matches = []
        for root, _, files in os.walk(bp_folder):
            if filename in files:
                matches.append(os.path.join(root, filename))
        if not matches:
            return None
        if len(matches) > 1:
            logger.warning(f"⚠️ 发现多个同名文件 {filename}，使用第一个: {matches[0]}")
        return matches[0]
    

    def _set_json_value(self, filepath: str, json_path: list, new_value: str):
        """根据路径列表修改JSON文件中的值（路径元素为字符串键或整数索引）"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 定位到父容器
        container = data
        for part in json_path[:-1]:
            if isinstance(container, dict):
                if part not in container:
                    raise KeyError(f"键 {part} 不存在")
                container = container[part]
            elif isinstance(container, list):
                if not isinstance(part, int):
                    raise TypeError(f"期望整数索引，得到 {part}")
                container = container[part]
            else:
                raise TypeError(f"无法在 {type(container)} 中索引")

        last_key = json_path[-1]
        if isinstance(container, dict):
            container[last_key] = new_value
        elif isinstance(container, list):
            container[last_key] = new_value
        else:
            raise TypeError("容器类型错误")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=self.indent)