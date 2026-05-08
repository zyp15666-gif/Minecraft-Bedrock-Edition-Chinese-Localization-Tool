#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用更新检查模块

功能：
- 检查 GitHub Releases 是否有新版本
- 支持后台静默检查和用户手动检查
- 提供下载链接和更新日志
- 记录检查时间，避免频繁请求

配置项（config.yml）：
  update:
    check_on_startup: true      # 启动时检查更新
    check_interval_hours: 24    # 检查间隔（小时）
    repo_owner: "your-github-username"  # GitHub 仓库所有者
    repo_name: "wodeshijie"     # GitHub 仓库名
"""

import json
import logging
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests 未安装，更新检查功能不可用")


@dataclass
class UpdateInfo:
    """更新信息"""
    latest_version: str
    current_version: str
    has_update: bool
    release_url: str
    download_url: Optional[str]
    release_notes: str
    published_at: str
    check_time: datetime


class UpdateChecker:
    """应用更新检查器"""

    DEFAULT_REPO_OWNER = "your-github-username"
    DEFAULT_REPO_NAME = "MinecraftBedrockLocalizer"

    def __init__(
        self,
        current_version: str,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        check_interval_hours: int = 24,
    ):
        """初始化更新检查器

        Args:
            current_version: 当前应用版本
            repo_owner: GitHub 仓库所有者
            repo_name: GitHub 仓库名
            check_interval_hours: 检查间隔（小时）
        """
        self.current_version = current_version
        self.repo_owner = repo_owner or self.DEFAULT_REPO_OWNER
        self.repo_name = repo_name or self.DEFAULT_REPO_NAME
        self.check_interval_hours = check_interval_hours

        self._last_check_file = self._get_last_check_file()
        self._last_check_time: Optional[datetime] = None
        self._cached_update_info: Optional[UpdateInfo] = None

    def _get_last_check_file(self) -> Path:
        """获取上次检查时间记录文件路径"""
        from core.app_paths import get_update_check_state_path
        return get_update_check_state_path()

    def _load_last_check_time(self) -> Optional[datetime]:
        """加载上次检查时间"""
        try:
            if self._last_check_file.exists():
                with open(self._last_check_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data.get('last_check', ''))
        except Exception as e:
            logger.debug(f"加载上次检查时间失败: {e}")
        return None

    def _save_last_check_time(self):
        """保存检查时间"""
        try:
            with open(self._last_check_file, 'w') as f:
                json.dump({
                    'last_check': datetime.now().isoformat(),
                    'version': self.current_version
                }, f)
        except Exception as e:
            logger.debug(f"保存检查时间失败: {e}")

    def _should_check(self) -> bool:
        """判断是否应该检查更新"""
        self._last_check_time = self._load_last_check_time()

        if self._last_check_time is None:
            return True

        next_check = self._last_check_time + timedelta(hours=self.check_interval_hours)
        return datetime.now() >= next_check

    def _get_github_api_url(self) -> str:
        """获取 GitHub API URL"""
        return f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"

    def _get_github_releases_url(self) -> str:
        """获取 GitHub Releases 页面 URL"""
        return f"https://github.com/{self.repo_owner}/{self.repo_name}/releases"

    def check_for_update(self, force: bool = False) -> Optional[UpdateInfo]:
        """检查更新

        Args:
            force: 是否强制检查（忽略时间间隔）

        Returns:
            更新信息，如果检查失败返回 None
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests 未安装，无法检查更新")
            return None

        if not force and not self._should_check():
            logger.debug("未到检查时间，跳过更新检查")
            return self._cached_update_info

        try:
            api_url = self._get_github_api_url()
            logger.info(f"正在检查更新: {api_url}")

            response = requests.get(
                api_url,
                timeout=10,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )

            if response.status_code == 403:
                logger.warning("GitHub API 速率限制，稍后重试")
                return None

            if response.status_code == 404:
                logger.warning("未找到 Release，请检查仓库设置")
                return None

            response.raise_for_status()

            release_data = response.json()

            latest_version = release_data.get('tag_name', '').lstrip('v')
            release_url = release_data.get('html_url', self._get_github_releases_url())
            release_notes = release_data.get('body', '无更新说明')
            published_at = release_data.get('published_at', '')

            download_url = None
            assets = release_data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'setup' in name or 'installer' in name:
                    download_url = asset.get('browser_download_url')
                    break

            has_update = self._compare_versions(latest_version, self.current_version)

            self._cached_update_info = UpdateInfo(
                latest_version=latest_version,
                current_version=self.current_version,
                has_update=has_update,
                release_url=release_url,
                download_url=download_url,
                release_notes=release_notes[:500] + "..." if len(release_notes) > 500 else release_notes,
                published_at=published_at,
                check_time=datetime.now()
            )

            self._save_last_check_time()

            if has_update:
                logger.info(f"发现新版本: {latest_version} (当前: {self.current_version})")
            else:
                logger.info(f"已是最新版本: {self.current_version}")

            return self._cached_update_info

        except requests.RequestException as e:
            logger.error(f"检查更新失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析更新信息失败: {e}")
            return None

    def _compare_versions(self, latest: str, current: str) -> bool:
        """比较版本号

        Returns:
            True 表示有更新
        """
        try:
            def parse_version(v):
                parts = v.split('.')
                return tuple(int(p) for p in parts if p.isdigit())

            latest_parts = parse_version(latest)
            current_parts = parse_version(current)

            return latest_parts > current_parts
        except Exception:
            return False

    def check_async(
        self,
        callback: Optional[Callable[[Optional[UpdateInfo]], None]] = None,
        force: bool = False
    ):
        """异步检查更新

        Args:
            callback: 检查完成后的回调函数
            force: 是否强制检查
        """
        def _check():
            result = self.check_for_update(force=force)
            if callback:
                callback(result)

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def open_download_page(self, update_info: Optional[UpdateInfo] = None):
        """打开下载页面

        Args:
            update_info: 更新信息，如果为 None 则打开 Releases 页面
        """
        if update_info and update_info.download_url:
            url = update_info.download_url
        elif update_info:
            url = update_info.release_url
        else:
            url = self._get_github_releases_url()

        try:
            webbrowser.open(url)
            logger.info(f"已打开下载页面: {url}")
        except Exception as e:
            logger.error(f"打开下载页面失败: {e}")


def get_current_version() -> str:
    """获取当前应用版本"""
    try:
        import re
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = re.match(r'^version\s*=\s*["\']([^"\']+)["\']', line)
                    if match:
                        return match.group(1)
    except Exception as e:
        logger.debug(f"读取版本号失败: {e}")

    return "1.0.0"


def check_update_on_startup(
    repo_owner: Optional[str] = None,
    repo_name: Optional[str] = None,
    show_dialog: bool = True,
    config: Optional[Dict[str, Any]] = None
) -> Optional[UpdateInfo]:
    """启动时检查更新

    Args:
        repo_owner: GitHub 仓库所有者
        repo_name: GitHub 仓库名
        show_dialog: 是否在有更新时显示对话框
        config: 配置字典（可选），用于读取更新检查配置

    Returns:
        更新信息
    """
    try:
        if config:
            check_on_startup = config.get('update', {}).get('check_on_startup', True)
            if not check_on_startup:
                logger.debug("配置禁用了启动时更新检查")
                return None

        current_version = get_current_version()
        checker = UpdateChecker(
            current_version=current_version,
            repo_owner=repo_owner,
            repo_name=repo_name
        )

        update_info = checker.check_for_update()

        if update_info and update_info.has_update and show_dialog:
            try:
                import tkinter as tk
                from tkinter import messagebox

                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                message = (
                    f"发现新版本: {update_info.latest_version}\n"
                    f"当前版本: {update_info.current_version}\n\n"
                    f"更新内容:\n{update_info.release_notes[:200]}...\n\n"
                    f"是否立即下载？"
                )

                result = messagebox.askyesno(
                    "发现新版本",
                    message
                )

                root.destroy()

                if result:
                    checker.open_download_page(update_info)

            except ImportError:
                print(f"\n{'=' * 50}")
                print(f"🔔 发现新版本: {update_info.latest_version}")
                print(f"   当前版本: {update_info.current_version}")
                print(f"   下载地址: {update_info.release_url}")
                print(f"{'=' * 50}\n")

        return update_info

    except Exception as e:
        logger.warning(f"启动时更新检查失败（网络或配置问题）: {e}")
        return None


if __name__ == "__main__":
    print(f"当前版本: {get_current_version()}")

    checker = UpdateChecker(get_current_version())
    info = checker.check_for_update(force=True)

    if info:
        print(f"最新版本: {info.latest_version}")
        print(f"有更新: {info.has_update}")
        if info.has_update:
            print(f"下载地址: {info.release_url}")
    else:
        print("检查更新失败")
