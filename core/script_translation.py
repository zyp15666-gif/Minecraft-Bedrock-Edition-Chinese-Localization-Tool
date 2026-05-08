#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本文件夹硬编码汉化模块 - 使用 esprima AST 精确定位 + 无占位符颜色代码翻译
"""

import hashlib
import json
import logging
import math
import os
import re
import shutil
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import esprima
    HAS_ESPRIMA = True
except ImportError:
    HAS_ESPRIMA = False

try:
    import pyjsparser
    HAS_PYJSPARSER = True
except ImportError:
    HAS_PYJSPARSER = False


# -- 辅助函数 -------------------------------------------------

def split_text_by_color_codes(text: str) -> List[tuple]:
    segments = []
    cur_codes, cur_text = '', ''
    i = 0
    while i < len(text):
        code = ''
        code_len = 0

        if text[i] == '§' and i + 1 < len(text):
            next_char = text[i + 1].lower()
            if next_char in '0123456789abcdefklmnor':
                code = text[i:i+2]
                code_len = 2
        elif text[i:i+2] == '\\x' and i + 4 < len(text):
            hex_part = text[i+2:i+4].lower()
            if len(hex_part) == 2:
                try:
                    char_val = int(hex_part, 16)
                    if char_val == 0xA7 and i + 4 < len(text):
                        next_char = text[i + 4].lower()
                        if next_char in '0123456789abcdefklmnor':
                            code = text[i:i+5]
                            code_len = 5
                except ValueError:
                    pass

        if code_len > 0:
            if cur_text:
                segments.append((cur_codes, cur_text))
                cur_codes, cur_text = '', ''
            cur_codes += code
            i += code_len
        else:
            cur_text += text[i]
            i += 1
    if cur_text or cur_codes:
        segments.append((cur_codes, cur_text))
    return [(c, t) for c, t in segments if c or t]


def _try_translate(text: str, api_manager) -> str:
    """调用翻译，失败或返回 None 时用原文，并清洗可能混入的颜色代码"""
    if not text:
        return text
    try:
        res = api_manager.multi_api_translate(text)
        if res:
            res = re.sub(r'§[0-9a-zA-Z]', '', res)
            res = re.sub(r'\\xA7[0-9a-zA-Z]', '', res)
        return res if res else text
    except Exception as e:
        logger.warning(f"翻译异常: {e}")
        return text


def translate_with_color_codes_v2(text: str, api_manager) -> Optional[str]:
    """分段翻译带 § 或 \\xA7 的文本，只翻纯文本部分，完成后拼回"""
    from core.utils import has_color_codes

    if not text or not has_color_codes(text):
        return _try_translate(text, api_manager)

    segments = split_text_by_color_codes(text)
    # 收集需要翻译的纯文本片段（非空）
    plain_list = []
    for codes, part in segments:
        if part.strip():
            plain_list.append(part)
        else:
            plain_list.append(None)

    # 逐个翻译（避免分隔符被破坏）
    translated = []
    for p in plain_list:
        if p is None:
            translated.append(None)
        else:
            translated.append(_try_translate(p, api_manager))

    # 拼回
    result_parts = []
    for idx, (codes, orig) in enumerate(segments):
        tr = translated[idx]
        if tr is not None:
            result_parts.append(codes + tr)
        else:
            result_parts.append(codes + orig)
    return ''.join(result_parts)


def _strip_surrounding_quotes(content: str, quote: str) -> str:
    """去除字符串内容外围的引号"""
    if quote and content:
        while len(content) > 1 and content[0] == quote and content[-1] == quote:
            content = content[1:-1]
        if quote != '`':
            while content and content[0] in ('"', "'", '`'):
                content = content[1:]
            while content and content[-1] in ('"', "'", '`'):
                content = content[:-1]
    return content


def _escape_dollar_curly(text: str, placeholders: dict) -> str:
    """转义 ${ 但跳过占位符中的模板表达式"""
    result = []
    i = 0
    while i < len(text):
        is_placeholder = False
        for ph in placeholders:
            if text[i:].startswith(ph):
                result.append(placeholders[ph])
                i += len(ph)
                is_placeholder = True
                break
        if is_placeholder:
            continue
        if text[i:i+2] == '${':
            result.append('\\${')
            i += 2
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)


def _build_backtick_literal(content: str) -> str:
    """构建反引号字符串字面量，处理占位符和转义"""
    placeholder_pattern = re.compile(r'\[\[(\d+)\]\]')
    placeholders = {}

    def replace_placeholder(match):
        idx = match.group(1)
        placeholder = f'__PH_{idx}__'
        placeholders[placeholder] = f'${{{idx}}}'
        return placeholder

    content = placeholder_pattern.sub(replace_placeholder, content)
    content = content.replace('\\', '\\\\')
    content = content.replace('`', '\\`')
    content = _escape_dollar_curly(content, placeholders)
    return f'`{content}`'


def _build_double_quote_literal(content: str) -> str:
    """构建双引号字符串字面量"""
    content = content.replace('\\', '\\\\').replace('"', '\\"')
    content = content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{content}"'


def _build_single_quote_literal(content: str) -> str:
    """构建单引号字符串字面量"""
    content = content.replace('\\', '\\\\').replace("'", "\\'")
    content = content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f"'{content}'"


def _build_string_literal(content: str, quote: str, original_content: str = None) -> str:
    content = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', content)

    content = _strip_surrounding_quotes(content, quote)

    if quote == '`':
        return _build_backtick_literal(content)
    elif quote == '"':
        return _build_double_quote_literal(content)
    elif quote == "'":
        return _build_single_quote_literal(content)
    return f'"{content}"'


# -- AST 提取器 -------------------------------------------------

class JSASTExtractor:
    _cache_lock = threading.Lock()
    _strings_cache = {}
    _strings_cache_timestamps = {}
    _strings_cache_maxsize = 100
    _strings_cache_keys = []
    _CACHE_TTL_SECONDS = 1800

    _SKIP_PATH_PREFIXES = (
        'textures/', 'sounds/', 'materials/', 'particles/',
        'entity/', 'models/', 'animations/', 'blocks/',
        'items/', 'block/', 'item/', 'entity_',
        'minecraft:', 'sgs_farm:', 'sgs_'
    )
    _SKIP_SHORT_WORDS = {
        'ok','yes','no','on','off','true','false',
        'id','name','type','form','key','val','icon',
        'ui','bp','rp','mc','js','json','png','txt'
    }

    @classmethod
    def extract_strings(cls, js_code, term_service=None, mode=2):
        all_strs = cls._extract_strings_internal(js_code, term_service)
        all_strs = [s for s in all_strs if not s.get('hasExpressions', False)]
        return [s for s in all_strs if '§' in s['text']] if mode == 1 else all_strs

    @classmethod
    def _extract_strings_internal(cls, js_code, term_service=None):
        content_hash = hashlib.md5(('ast_' + js_code).encode()).hexdigest()
        if term_service:
            terms_str = str(sorted(term_service.terms.items()))
            terms_hash = hashlib.md5(terms_str.encode()).hexdigest()
            content_hash = f"{content_hash}_{terms_hash}"
        with cls._cache_lock:
            if content_hash in cls._strings_cache:
                if time.time() - cls._strings_cache_timestamps.get(content_hash,0) < cls._CACHE_TTL_SECONDS:
                    return cls._strings_cache[content_hash].copy()
        strings = cls._parse_js_ast(js_code)
        cls._store_strings_in_cache(content_hash, strings)
        return strings

    @classmethod
    def _parse_js_ast(cls, js_code):
        """使用可用解析器解析 JavaScript AST 并提取字符串"""
        errors = []

        # 预处理：将 ES2020 语法转换为 ES6 兼容语法
        preprocessed_code = cls._preprocess_es2020(js_code)

        if HAS_ESPRIMA:
            try:
                return cls._run_esprima_extraction(preprocessed_code)
            except Exception as e:
                errors.append(f"esprima: {e}")

        if HAS_PYJSPARSER:
            try:
                return cls._run_pyjsparser_extraction(preprocessed_code)
            except Exception as e:
                errors.append(f"pyjsparser: {e}")

        raise RuntimeError(f"所有解析器都失败了: {'; '.join(errors)}")

    @classmethod
    def _preprocess_es2020(cls, js_code):
        """预处理 ES2020 语法，转换为兼容语法"""
        # 将可选链 ?. 替换为普通访问 .
        # 注意：这只是为了让解析器能解析，实际替换时会使用原始代码
        result = js_code

        # 替换 ?. 为 . （仅用于解析）
        result = re.sub(r'\?\.', '.', result)

        # 替换 ?? 为 || （仅用于解析）
        result = re.sub(r'\?\?', '||', result)

        return result

    @classmethod
    def _run_pyjsparser_extraction(cls, js_code):
        """使用 pyjsparser 提取 JavaScript 字符串（支持 ES6+）"""
        try:
            parser = pyjsparser.PyJsParser()
            tree = parser.parse(js_code)
        except Exception as e:
            raise RuntimeError(f"pyjsparser 解析失败: {e}")

        raw = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                return

            node_type = node.get('type')
            if node_type == 'Literal':
                value = node.get('value')
                if isinstance(value, str):
                    raw.append({
                        'text': value,
                        'raw': node.get('raw', ''),
                        'range': (node.get('start', 0), node.get('end', 0)),
                        'quote': node.get('raw', '"')[0] if node.get('raw') else '"',
                        'context': ''
                    })
            elif node_type == 'TemplateLiteral':
                quasis = node.get('quasis', [])
                expressions = node.get('expressions', [])
                if quasis and len(expressions) == 0:
                    quasi = quasis[0]
                    cooked = quasi.get('value', {}).get('cooked', '') or ''
                    raw_value = quasi.get('value', {}).get('raw', '') or ''
                    raw.append({
                        'text': cooked,
                        'raw': raw_value,
                        'range': (node.get('start', 0), node.get('end', 0)),
                        'quote': '`',
                        'context': ''
                    })

            for key, value in node.items():
                if key in ('type', 'loc', 'range', 'start', 'end'):
                    continue
                if isinstance(value, list):
                    walk(value)
                elif isinstance(value, dict):
                    walk(value)

        walk(tree)
        return raw

    @classmethod
    def _handle_esprima_parse_error(cls, error_msg: str, js_code: str):
        """处理 esprima 解析错误，转换为有意义的 RuntimeError"""
        if 'Unexpected token' in error_msg:
            match = re.search(r'line (\d+)', error_msg)
            line_info = f"第{match.group(1)}行" if match else "未知行"
            if '?.' in js_code or '??' in js_code:
                raise RuntimeError(f"JavaScript 语法错误 ({line_info}): 文件使用了 ES2020 新特性（可选链 ?. 或空值合并 ??），当前解析器不支持。请使用功能10批量处理，或手动翻译此文件。")
            raise RuntimeError(f"JavaScript 语法错误 ({line_info}): {error_msg}")
        raise RuntimeError(f"AST 解析失败: {error_msg}")

    @classmethod
    def _extract_esprima_literal(cls, node) -> Optional[dict]:
        """从 esprima Literal 节点提取字符串信息"""
        value = getattr(node, 'value', None)
        if not isinstance(value, str):
            return None
        return {
            'text': value,
            'raw': getattr(node, 'raw', ''),
            'range': getattr(node, 'range', None),
            'quote': getattr(node, 'raw', '"')[0] if getattr(node, 'raw', '') else '"',
            'context': ''
        }

    @classmethod
    def _extract_esprima_template(cls, node) -> Optional[dict]:
        """从 esprima TemplateLiteral 节点提取字符串信息"""
        quasis = getattr(node, 'quasis', [])
        expressions = getattr(node, 'expressions', [])
        if not quasis or len(expressions) != 0:
            return None
        quasi = quasis[0]
        value_obj = getattr(quasi, 'value', None)
        if not value_obj:
            return None
        raw_value = getattr(value_obj, 'raw', '') or ''
        cooked = getattr(value_obj, 'cooked', '') or raw_value
        return {
            'text': cooked,
            'raw': raw_value,
            'range': getattr(node, 'range', None),
            'quote': '`',
            'context': ''
        }

    @classmethod
    def _walk_esprima_node(cls, node, raw: list):
        """递归遍历 esprima AST 节点，提取字符串"""
        if node is None:
            return

        if isinstance(node, list):
            for item in node:
                cls._walk_esprima_node(item, raw)
            return

        node_type = getattr(node, 'type', None)
        if node_type is None:
            return

        if node_type == 'Literal':
            result = cls._extract_esprima_literal(node)
            if result:
                raw.append(result)
            return

        if node_type == 'TemplateLiteral':
            result = cls._extract_esprima_template(node)
            if result:
                raw.append(result)
            return

        if hasattr(node, '__dict__'):
            for key, value in node.__dict__.items():
                if key in ('type', 'loc', 'range', 'start', 'end'):
                    continue
                if isinstance(value, list):
                    cls._walk_esprima_node(value, raw)
                elif hasattr(value, 'type'):
                    cls._walk_esprima_node(value, raw)

    @classmethod
    def _run_esprima_extraction(cls, js_code):
        """使用 esprima 提取 JavaScript 字符串"""
        try:
            tree = esprima.parseModule(js_code, {'range': True, 'tolerant': True, 'loc': True})
        except esprima.Error as e:
            cls._handle_esprima_parse_error(str(e), js_code)
        except Exception as e:
            raise RuntimeError(f"AST parse error: {e}")

        raw = []
        cls._walk_esprima_node(tree.body, raw)
        return raw

    @classmethod
    def _should_skip(cls, text, code, start):
        s = text.strip()
        if not s or s in ('\n', '\t', ' '):
            return True
        lo = s.lower()
        for p in cls._SKIP_PATH_PREFIXES:
            if lo.startswith(p.lower()):
                return True
        if len(s) <= 3 and lo in cls._SKIP_SHORT_WORDS:
            return True
        if lo in ('form', 'function', 'type', 'g'):
            return True
        if s == '§':
            return True
        clean = re.sub(r'§[0-9a-zA-Z]', '', s)
        clean = clean.replace('\\n', '').replace('\\r', '').replace('\\t', '')
        if not clean.strip():
            return True
        if cls._detect_context(code, start) == 'property_key':
            return True
        if s.isdigit():
            return True
        if re.match(r'^[\W_]+$', s):
            return True
        return False

    @classmethod
    def _detect_context(cls, code, quote_pos):
        pre = code[max(0, quote_pos-50):quote_pos]
        if re.search(r'[\{,]\s*$', pre):
            if re.match(r'"[^"]*"\s*:', code[quote_pos:]):
                return 'property_key'
        if re.search(r'[\.\[]$', pre):
            return 'property_name'
        if re.search(r'\(\s*$', pre):
            return 'function_argument'
        return ''

    @classmethod
    def _store_strings_in_cache(cls, hash_val, strings):
        with cls._cache_lock:
            if len(cls._strings_cache) >= cls._strings_cache_maxsize:
                old = cls._strings_cache_keys.pop(0)
                del cls._strings_cache[old]
                cls._strings_cache_timestamps.pop(old, None)
            cls._strings_cache[hash_val] = strings.copy()
            cls._strings_cache_timestamps[hash_val] = time.time()
            cls._strings_cache_keys.append(hash_val)

    @classmethod
    def clear_cache(cls):
        with cls._cache_lock:
            cls._strings_cache.clear()
            cls._strings_cache_timestamps.clear()
            cls._strings_cache_keys.clear()


# -- AI 判断（无 § 字符串） -------------------------------------------------

def judge_strings_with_ai(strings_no_color, api_manager, log_callback=None, progress_callback=None, batch_size=50):
    from api.translation_prompts import JS_AST_JUDGE_PROMPT

    if not strings_no_color:
        return {}
    data = [{'id': s['id'], 'text': s['text'], 'context': s.get('context','')} for s in strings_no_color]
    total = len(data)
    batches = [data[i*batch_size:(i+1)*batch_size] for i in range(math.ceil(total/batch_size))]
    id_orig = {s['id']:s['text'] for s in strings_no_color}
    id_ctx = {s['id']:s.get('context','') for s in strings_no_color}
    mapping = {}

    def do_batch(batch):
        api = api_manager.get_next_api()
        if not api:
            return {}
        for attempt in range(3):
            try:
                resp = api_manager.api_client.translate(
                    api_config=api,
                    text=json.dumps(batch, ensure_ascii=False),
                    is_test=False,
                    system_prompt=JS_AST_JUDGE_PROMPT
                )
                result = json.loads(resp)
                local = {}
                for item in result:
                    tid = item['id']
                    trans = item.get('translation')
                    local[tid] = {
                        'translate': item.get('translate',False),
                        'translation': trans if item.get('translate') else None,
                        'original': id_orig.get(tid,''),
                        'context': id_ctx.get(tid,'')
                    }
                return local
            except Exception:
                if attempt == 2:
                    return {}
                time.sleep(2)
        return {}

    with ThreadPoolExecutor(max_workers=min(len(batches),5)) as ex:
        futs = [ex.submit(do_batch, b) for b in batches]
        for f in as_completed(futs):
            mapping.update(f.result())
    if log_callback:
        n = sum(1 for v in mapping.values() if v['translate'])
        log_callback(f"✅ AI 判断完成，{n} 个需要翻译")
    return mapping


# -- 精确替换 -------------------------------------------------

def replace_strings_in_code(js_code, strings, trans_map):
    COMMON_KEYS = {
        'form','name','type','id','class','src','href','alt','title',
        'value','placeholder','label','text','icon','color','size',
        'width','height','x','y','z','min','max','default','enabled',
        'disabled','visible','active','hover','focus','blur','click',
        'mouse','key','event','data','options','items','children',
        'parent','node','element','widget','button','menu','item',
        'action','callback','handler','listener'
    }
    def unsafe(orig, trans, ctx):
        if ctx == 'property_key':
            return True
        if len(orig) <= 3 and orig.lower() in COMMON_KEYS:
            return True
        if trans and ('{' in trans or '}' in trans or ';' in trans):
            return True
        return False

    replacements = []
    for s in strings:
        info = trans_map.get(s['id'])
        if not info or not info.get('translate'):
            continue
        trans = info.get('translation')
        if not trans:
            continue
        ctx = s.get('context', '')
        if unsafe(s.get('original_text', s['text']), trans, ctx):
            continue
        start, end = s['range']
        quote = s.get('quote', '"')
        original_content = js_code[start:end]
        literal = _build_string_literal(trans, quote, original_content)
        replacements.append((start, end, literal))

    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, lit in replacements:
        js_code = js_code[:start] + lit + js_code[end:]
    return js_code


# -- 核心类 -------------------------------------------------

class ScriptTranslation:
    def __init__(self, translator=None):
        self.translator = translator

    @property
    def api_manager(self):
        return self.translator.api_manager if self.translator else None

    def scan_js_files(self, bp_path, log_callback=None):
        folder = os.path.join(bp_path, "scripts")
        if not os.path.exists(folder):
            return []
        files = []
        for root,_,fnames in os.walk(folder):
            for f in fnames:
                if f.lower().endswith('.js'):
                    files.append(os.path.join(root, f))
        return files

    def translate_js_files_with_ast(self, js_files, mode=2,
                                    progress_callback=None, log_callback=None,
                                    clear_cache_before=True):
        def log(msg):
            if log_callback:
                log_callback(msg)
        def progress(v, r=0, t=0):
            if progress_callback:
                progress_callback(v, r, t)

        if clear_cache_before:
            JSASTExtractor.clear_cache()

        if not js_files:
            return {'success': True, 'message': '没有需要处理的文件',
                    'translated_files': [], 'backup_files': [], 'failed_files': []}

        to_process = self._filter_js_files(js_files, mode, log)
        log(f"需处理 {len(to_process)} 个文件")
        progress(0.1)

        translated_files, failed_files, backup_files, unchanged_files = [], [], [], []
        total_tr = 0

        for i, js_file in enumerate(to_process):
            try:
                log(f"处理 {i+1}/{len(to_process)}: {os.path.basename(js_file)}")
                with open(js_file, 'r', encoding='utf-8') as f:
                    original = f.read()

                term_service = getattr(self.api_manager, 'term_service', None)
                strings = JSASTExtractor.extract_strings(original, term_service, mode=mode)
                if not strings:
                    unchanged_files.append(js_file)
                    continue

                trans_map = self._translate_strings(strings, mode, log, progress)
                total_tr += sum(1 for v in trans_map.values() if v.get('translate'))

                new_code = replace_strings_in_code(original, strings, trans_map)
                if new_code == original:
                    unchanged_files.append(js_file)
                    log("  无变化")
                    continue

                backup = js_file + ".bak"
                shutil.copy2(js_file, backup)
                backup_files.append(backup)
                with open(js_file, 'w', encoding='utf-8') as f:
                    f.write(new_code)
                translated_files.append(js_file)
                log(f"  完成，翻译 {len(trans_map)} 处")

                progress(0.1 + (i+1)/len(to_process) * 0.8)

            except Exception as e:
                log(f"  失败: {e}")
                traceback.print_exc()
                failed_files.append((js_file, str(e)))

        progress(1.0)
        msg = f"成功 {len(translated_files)} 个，失败 {len(failed_files)} 个"
        if unchanged_files:
            msg += f"，无变化 {len(unchanged_files)} 个"
        return {
            'success': True, 'message': msg,
            'translated_files': translated_files,
            'backup_files': backup_files,
            'failed_files': failed_files,
            'unchanged_files': unchanged_files,
            'total_translated_count': total_tr
        }

    def _filter_js_files(self, js_files, mode, log):
        to_process = []
        for f in js_files:
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                if mode == 1 and '§' not in content:
                    continue
                to_process.append(f)
            except Exception as e:
                log(f"读取失败 {f}: {e}")
        return to_process

    def _translate_strings(self, strings, mode, log, progress):
        color_strs = [s for s in strings if '§' in s['text']]
        no_color = [s for s in strings if '§' not in s['text']]
        trans_map = {}

        if color_strs and self.api_manager:
            log(f"  🎨 翻译 {len(color_strs)} 个带颜色代码的字符串")
            color_map = self._translate_color_strings(color_strs, log)
            trans_map.update(color_map)

        if mode == 2 and no_color and self.api_manager:
            log(f"  🤖 AI 判断 {len(no_color)} 个无颜色字符串")
            ai_map = judge_strings_with_ai(
                no_color, self.api_manager,
                log_callback=log, progress_callback=progress, batch_size=50
            )
            trans_map.update(ai_map)

        return trans_map

    def _translate_color_strings(self, color_strs, log):
        available_apis = self.api_manager.get_available_apis()
        max_threads_per_api = 3
        max_workers = len(available_apis) * max_threads_per_api if available_apis else 1
        log(f"     线程数: {max_workers}, 可用API: {len(available_apis)}")

        trans_map = {}

        def translate_single_string(s_item):
            try:
                translated = translate_with_color_codes_v2(s_item['text'], self.api_manager)
                if translated and translated != s_item['text']:
                    return s_item['id'], {
                        'translate': True,
                        'translation': translated,
                        'original': s_item['text'],
                        'context': s_item.get('context', '')
                    }
            except Exception as e:
                logger.warning(f"翻译失败 [{s_item['id']}]: {str(e)[:50]}")
            return None, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(translate_single_string, s): s
                for s in color_strs
            }
            for future in as_completed(future_to_item):
                item_id, result = future.result()
                if item_id and result:
                    trans_map[item_id] = result

        return trans_map

    def analyze_js_files_for_preview(self, js_files, mode=2,
                                     progress_callback=None, log_callback=None):
        def log(msg):
            if log_callback:
                log_callback(msg)
        def progress(v, r=0, t=0):
            if progress_callback:
                progress_callback(v, r, t)
        if not js_files:
            return {'success':True, 'file_analyses':[], 'summary':{}}
        log(f"🔍 分析 {len(js_files)} 个文件")
        analyses, total_str, total_need = [], 0, 0
        for i,f in enumerate(js_files):
            try:
                with open(f,'r',encoding='utf-8') as fp:
                    code = fp.read()
                strings = JSASTExtractor.extract_strings(code, mode=mode)
                color_cnt = sum(1 for s in strings if '§' in s['text'])
                need = color_cnt if mode==1 else color_cnt + int(len(strings)*0.3)
                analyses.append({'file_path':f,'strings':strings,
                                 'needs_translation_count':need,'total_strings':len(strings)})
                total_str += len(strings)
                total_need += need
                progress(0.1+(i+1)/len(js_files)*0.8)
            except Exception as e:
                analyses.append({'file_path':f,'error':str(e),'needs_translation_count':0})
        progress(1.0)
        return {
            'success':True,
            'file_analyses': analyses,
            'summary': {
                'total_files': len(js_files),
                'total_strings': total_str,
                'needs_translation_count': total_need,
                'estimated_time': total_need * 2.0
            }
        }

    def script_hardcode_translation(self, bp_path, mode=2, **kwargs):
        js_files = self.scan_js_files(bp_path, kwargs.get('log_callback'))
        if not js_files:
            return {'success': True, 'message': '未找到 JS 文件'}
        kwargs.pop('ui_keywords', None)
        return self.translate_js_files_with_ast(js_files, mode=mode, **kwargs)


def create_script_translation(translator=None):
    return ScriptTranslation(translator)
