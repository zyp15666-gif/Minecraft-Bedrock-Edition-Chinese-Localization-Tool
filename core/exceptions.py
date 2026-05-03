"""
自定义异常层次结构 — 区分可恢复与致命错误
"""


class TranslationError(Exception):
    """翻译相关异常基类"""
    pass


class TranslatorNotInitializedError(TranslationError):
    """翻译管道未初始化"""
    pass


class APIAuthError(TranslationError):
    """API认证失败（401/403）"""
    pass


class APITimeoutError(TranslationError):
    """API请求超时"""
    pass


class APIRateLimitError(TranslationError):
    """API速率限制（429）"""
    pass


class APIConnectionError(TranslationError):
    """API连接失败（网络不可达）"""
    pass


class APIResponseError(TranslationError):
    """API返回非预期格式"""
    pass


class AllAPIsExhaustedError(TranslationError):
    """所有API均已尝试并失败"""
    pass


class FileProcessingError(Exception):
    """文件处理相关异常"""
    pass


class FileAccessError(FileProcessingError):
    """文件访问权限错误"""
    pass


class FileFormatError(FileProcessingError):
    """文件格式错误（如JSON解析失败）"""
    pass


class ConfigError(Exception):
    """配置相关异常"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证失败"""
    pass


def classify_http_error(status_code: int, message: str = "") -> TranslationError:
    """根据HTTP状态码映射到自定义异常"""
    if status_code == 401 or status_code == 403:
        return APIAuthError(message or f"API认证失败 (HTTP {status_code})")
    elif status_code == 429:
        return APIRateLimitError(message or f"API速率限制 (HTTP {status_code})")
    elif 500 <= status_code < 600:
        return APIResponseError(message or f"API服务器错误 (HTTP {status_code})")
    else:
        return APIResponseError(message or f"API请求失败 (HTTP {status_code})")
