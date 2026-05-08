# type: ignore
"""mcstructure 汉化功能 UseCase"""

import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from mcstructure import NBTFile


class McstructureTranslationUseCase:
    """mcstructure 汉化用例"""

    def __init__(self, api_manager):
        """
        初始化用例

        Args:
            api_manager: APIManager实例
        """
        self.api_manager = api_manager

    def execute(
        self,
        bp_folder_path: str,
        backup: bool = True,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行翻译操作

        Args:
            bp_folder_path: BP文件夹路径
            backup: 是否备份文件
            progress_callback: 进度回调
            log_callback: 日志回调

        Returns:
            执行结果
        """

        def log(msg):
            if log_callback:
                log_callback(msg)

        def progress(value, remaining_count=0, remaining_time=0):
            if progress_callback:
                progress_callback(value, remaining_count, remaining_time)

        structures_path = Path(bp_folder_path) / "structures"
        if not structures_path.exists():
            return {
                "success": False,
                "message": f"structures 文件夹不存在: {structures_path}"
            }

        mcstructure_files = list(structures_path.rglob("*.mcstructure"))
        total_files = len(mcstructure_files)

        if total_files == 0:
            return {
                "success": True,
                "message": "未找到任何 mcstructure 文件"
            }

        log(f"📦 开始处理 {total_files} 个 mcstructure 文件...")

        start_time = time.time()

        # ========== 阶段1: 收集所有待翻译文本 ==========
        log("📋 阶段1: 收集所有待翻译文本...")
        all_texts = {}  # { "filepath:path_in_file": original_text }
        file_text_map = {}  # { filepath: [ (path, original_text), ... ] }

        for i, filepath in enumerate(mcstructure_files):
            progress((i + 1) / total_files * 0.3, total_files - i, 0)

            try:
                # 仅读取 NBT 收集文本，不修改文件
                with open(filepath, 'rb') as f:
                    nbt = NBTFile(f, little_endian=True)

                texts = self._extract_strings(nbt)
                if texts:
                    file_text_map[filepath] = []
                    for path_in_file, text in texts.items():
                        unique_key = f"{filepath}:{path_in_file}"
                        all_texts[unique_key] = text
                        file_text_map[filepath].append((path_in_file, text))
            except Exception as e:
                log(f"⚠️  读取 {filepath.name} 失败: {str(e)[:50]}")

        if not all_texts:
            return {
                "success": True,
                "message": "所有文件都没有需要翻译的文本"
            }

        log(f"✅ 收集到 {len(all_texts)} 处需要翻译的文本")
        progress(0.3, len(all_texts), 0)

        # ========== 阶段2: 多线程并行翻译 ==========
        log("🚀 阶段2: 多线程并行翻译...")

        # 使用 APIManager 已经支持的多线程翻译方法
        # 首先需要把 dict 格式传给 translator 或使用 API 管理器的多线程能力
        # 我们这里实现简单的 ThreadPoolExecutor 包装
        translated_map = self._parallel_translate_texts(all_texts, log, progress, start_time, total_files)

        # ========== 阶段3: 写入翻译结果 ==========
        log("📝 阶段3: 写入翻译结果到文件...")

        translated_files = 0
        total_strings = 0
        results = []

        files_to_process = list(file_text_map.keys())
        for i, filepath in enumerate(files_to_process):
            progress(0.7 + (i + 1) / len(files_to_process) * 0.25, len(files_to_process) - i, 0)

            try:
                log(f"🔄 处理 [{i+1}/{len(files_to_process)}]: {filepath.name}")

                result = self._write_translated_file(
                    filepath,
                    file_text_map[filepath],
                    translated_map,
                    backup
                )

                results.append(result)

                if result.get("changed", False):
                    translated_files += 1
                    total_strings += result.get("translated_count", 0)
                    log(f"   ✅ 已翻译 {result.get('translated_count')} 处")

            except Exception as e:
                error_msg = f"❌ 处理 {filepath.name} 时出错: {str(e)}"
                log(error_msg)
                results.append({
                    "file": filepath.name,
                    "success": False,
                    "error": str(e)
                })

        # ========== 完成 ==========
        progress(1.0, 0, 0)

        success_count = sum(1 for r in results if r.get("success", False))
        failed_count = len(results) - success_count

        message = f"处理完成！成功: {success_count}, 失败: {failed_count}, 已翻译文件: {translated_files}, 已翻译字符串: {total_strings}"

        log(f"✅ {message}")

        return {
            'success': True,
            'message': message,
            'data': {
                "results": results,
                "translated_files": translated_files,
                "total_strings": total_strings
            }
        }

    def _parallel_translate_texts(
        self,
        all_texts: Dict[str, str],
        log_callback: Optional[Callable],
        progress_callback: Optional[Callable],
        start_time: float,
        total_files: int
    ) -> Dict[str, str]:
        """
        多线程并行翻译文本

        Args:
            all_texts: { unique_key: original_text }
            log_callback: 日志回调
            progress_callback: 进度回调
            start_time: 开始时间
            total_files: 总文件数

        Returns:
            { unique_key: translated_text }
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from core.log_manager import get_logger

        logger = get_logger(__name__)

        # 获取可用 API 数量和线程配置
        available_apis = self.api_manager.get_available_apis()
        max_threads_per_api = 3

        if len(available_apis) == 0:
            # 如果没有可用 API，退回到单线程模式
            logger.warning("没有可用 API，使用单线程模式")
            translated_map = {}
            total = len(all_texts)
            for i, (key, text) in enumerate(all_texts.items()):
                translated = self.api_manager.translate_text(text)
                translated_map[key] = translated
                if progress_callback:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (i + 1) if i > 0 else 0
                    remaining_time = int(avg_time * (total - i - 1))
                    progress_callback(0.3 + (i + 1) / total * 0.35, total - i - 1, remaining_time)
            return translated_map

        max_workers = len(available_apis) * max_threads_per_api

        if log_callback:
            log_callback(f"   线程数: {max_workers}")
            log_callback(f"   可用API: {len(available_apis)}")
            log_callback(f"   待翻译: {len(all_texts)}")

        translated_map = {}
        total = len(all_texts)
        items = list(all_texts.items())

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {
                executor.submit(self.api_manager.translate_text, text): key
                for key, text in items
            }

            for i, future in enumerate(as_completed(future_to_key)):
                key = future_to_key[future]
                try:
                    translated = future.result()
                    translated_map[key] = translated
                except Exception as e:
                    logger.warning(f"翻译失败 [{key}]: {str(e)[:50]}")
                    # 失败时保留原文
                    translated_map[key] = all_texts[key]

                # 更新进度
                if progress_callback:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (i + 1) if i > 0 else 0
                    remaining = total - (i + 1)
                    remaining_time = int(avg_time * remaining)
                    progress_callback(0.3 + (i + 1) / total * 0.35, remaining, remaining_time)

        return translated_map

    def _write_translated_file(
        self,
        filepath: Path,
        texts_to_write: list,
        translated_map: Dict[str, str],
        backup: bool
    ) -> Dict:
        """
        写回翻译后的内容到单个文件

        Args:
            filepath: 文件路径
            texts_to_write: [ (path, original_text), ... ]
            translated_map: 翻译结果字典
            backup: 是否备份

        Returns:
            处理结果
        """
        result = {
            "file": filepath.name,
            "success": False,
            "changed": False,
            "translated_count": 0
        }

        if backup:
            backup_path = filepath.with_suffix(filepath.suffix + ".bak")
            if not backup_path.exists():
                shutil.copy2(filepath, backup_path)

        with open(filepath, 'rb') as f:
            nbt = NBTFile(f, little_endian=True)

        translated_count = 0
        for path_in_file, original_text in texts_to_write:
            unique_key = f"{filepath}:{path_in_file}"
            translated_text = translated_map.get(unique_key, original_text)
            if translated_text and translated_text != original_text:
                translated_count += 1
                self._replace_string(nbt, path_in_file, translated_text)

        if translated_count > 0:
            with open(filepath, 'wb') as f:
                nbt.save(f, little_endian=True)
            result["changed"] = True
            result["translated_count"] = translated_count

        result["success"] = True
        return result

    @staticmethod
    def _safe_nbt_value(obj, default: str = "") -> str:
        try:
            return obj.value if hasattr(obj, 'value') else str(obj)
        except Exception:
            return default

    def _extract_sign_texts(self, obj, current_path: str, strings: Dict[str, str]):
        if not (hasattr(obj, 'keys') and 'id' in obj):
            return
        block_id = self._safe_nbt_value(obj['id'])
        if block_id != 'Sign':
            return
        for side in ('FrontText', 'BackText'):
            if side not in obj:
                continue
            side_data = obj[side]
            if 'Text' not in side_data:
                continue
            text = self._safe_nbt_value(side_data['Text'])
            if text and text.strip():
                strings[f"{current_path}/{side}/Text"] = text

    def _extract_book_texts(self, obj, current_path: str, strings: Dict[str, str]):
        if not (hasattr(obj, 'keys') and 'identifier' in obj):
            return
        identifier = self._safe_nbt_value(obj['identifier'])
        if identifier != 'minecraft:item' or 'Item' not in obj:
            return
        item = obj['Item']
        item_name = self._safe_nbt_value(item.get('Name', ''))
        if item_name != 'minecraft:written_book' or 'tag' not in item:
            return
        tag = item['tag']
        if 'title' in tag:
            title = self._safe_nbt_value(tag['title'])
            if title and title.strip():
                strings[f"{current_path}/Item/tag/title"] = title
        if 'author' in tag:
            author = self._safe_nbt_value(tag['author'])
            if author and author.strip():
                strings[f"{current_path}/Item/tag/author"] = author
        if 'pages' in tag:
            self._extract_book_pages(tag['pages'], current_path, strings)

    def _extract_book_pages(self, pages, current_path: str, strings: Dict[str, str]):
        try:
            for i in range(len(pages)):
                page = pages[i]
                if 'text' not in page:
                    continue
                text = self._safe_nbt_value(page['text'])
                if text and text.strip():
                    strings[f"{current_path}/Item/tag/pages[{i}]/text"] = text
        except Exception:
            pass

    def _extract_strings(self, nbt) -> Dict[str, str]:
        strings: Dict[str, str] = {}
        self._walk_nbt(nbt, "", strings)
        return strings

    def _walk_nbt(self, obj, current_path: str, strings: Dict[str, str]):
        self._extract_sign_texts(obj, current_path, strings)
        self._extract_book_texts(obj, current_path, strings)
        if hasattr(obj, 'keys'):
            for key in list(obj.keys()):
                self._walk_nbt(obj[key], f"{current_path}/{key}", strings)
        elif hasattr(obj, '__len__') and not isinstance(obj, (str, bytes, int, float)):
            try:
                for i in range(len(obj)):
                    self._walk_nbt(obj[i], f"{current_path}[{i}]", strings)
            except Exception:
                pass

    def _replace_string(self, nbt, path_in_file: str, new_text: str):
        """
        将翻译后的文本替换回 NBT

        Args:
            nbt: NBTFile 对象
            path_in_file: 在文件中的路径
            new_text: 新的文本
        """
        # 解析路径并定位到目标位置，然后替换
        parts = path_in_file.strip("/").split("/")

        obj = nbt

        try:
            # 遍历路径的每一部分，定位到目标对象
            for i, part in enumerate(parts[:-1]):
                if "[" in part:
                    # 处理数组索引，如 pages[0]
                    name_part = part[:part.index("[")]
                    index_str = part[part.index("[")+1:part.index("]")]
                    index = int(index_str)

                    if name_part and name_part in obj:
                        obj = obj[name_part][index]
                    elif hasattr(obj, "__getitem__"):
                        obj = obj[index]
                else:
                    if part in obj:
                        obj = obj[part]

            # 处理最后一部分
            last_part = parts[-1]

            if "[" in last_part:
                name_part = last_part[:last_part.index("[")]
                index_str = last_part[last_part.index("[")+1:last_part.index("]")]
                index = int(index_str)

                if name_part and name_part in obj:
                    target = obj[name_part][index]
                    if 'text' in target:
                        target['text'].value = new_text
                elif hasattr(obj, "__getitem__"):
                    target = obj[index]
                    if 'text' in target:
                        target['text'].value = new_text
            else:
                if last_part in obj:
                    obj[last_part].value = new_text
        except Exception as e:
            from core.log_manager import get_logger
            logger = get_logger(__name__)
            logger.warning(f"替换文本失败 [{path_in_file}]: {str(e)[:50]}")
