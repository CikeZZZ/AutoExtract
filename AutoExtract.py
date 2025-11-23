#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = "1.1.0"

# =============================================================================
# 多语言支持 (I18N)(目前以支持简体中文、繁体中文、英文和日文)
# =============================================================================
import os
import sys

# 禁用输出缓冲（必须在最开始！）
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
else:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

# 从 i18n 模块导入
from i18n import get_system_language, MESSAGES, get_available_languages

class I18N:
    def __init__(self, lang: str):
        if lang == 'auto':
            self.lang = get_system_language()
        else:
            self.lang = lang
        self._ = self._get_message

    def _get_message(self, key: str, **kwargs) -> str:
        msg = MESSAGES.get(self.lang, MESSAGES['en']).get(key, f"[MISSING_KEY: {key}]")
        try:
            return msg.format(**kwargs)
        except KeyError as e:
            return f"[FORMAT_ERROR: {key} - {e}] {msg}"

# =============================================================================
# 初始化与依赖导入
# =============================================================================
import shutil
import subprocess
import time
import re
import filetype
import logging
import argparse
import platform
from dataclasses import dataclass
from typing import Set, Dict, Tuple, List, Optional

# Windows 注册表支持
if platform.system() == "Windows":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

# =============================================================================
# 配置与常量
# =============================================================================
CONTEXT_MENU_KEY = "CikeZZZ_AutoExtract"

@dataclass
class Config:
    delete_target_files: bool            # 是否删除目标文件
    delete_empty_folders: bool           # 是否删除空文件夹
    auto_yes: bool                       # 是否自动确认（是）
    auto_no: bool                        # 是否自动确认（否）
    delete_list: List[str]               # 删除列表
    delete_list_file: Optional[str]      # 删除列表文件路径
    generate_delete_list_file: bool      # 是否生成删除列表文件
    language: str                        # 语言
    add_context_menu: bool               # 是否添加右键菜单
    remove_context_menu: bool            # 是否移除右键菜单
    max_unpacked_gb: int                 # 最大允许解压大小（GB）
    max_files: int                       # 最大允许文件数
# ---------------- 全局状态 ----------------
DETECTED_FILES: Set[str] = set()
FAILED_ARCHIVES: Dict[str, str] = {}
DETECTION_FAILED: Dict[str, str] = {}

# ---------------- 日志配置 ----------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True
)
logger = logging.getLogger(__name__)

# ---------------- 安全配置 ----------------
SAFE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    '.txt', '.log', '.ini', '.cfg', '.md',
    '.mp3', '.wav', '.mp4', '.avi', '.mkv',
    '.exe', '.dll', '.bat', '.sh',
    '.pdf', '.psd', '.ai', '.svg'
}

ARCHIVE_EXTENSIONS = {
    '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.lz',
    '.rar', '.zip', '.7z', '.tar',
    '.gz', '.bz2', '.xz', '.lz', '.lzma', '.z'
}

SUPPORTED_ARCHIVE_TYPES = {'rar', 'zip', '7z', 'gz', 'bz2', 'xz', 'lzma', 'tar', 'z'}

VOLUME_PATTERNS = [
    re.compile(r'(part|vol|volume)[_-]?(\d+)', re.IGNORECASE | re.UNICODE),
    re.compile(r'\.z(\d+)', re.IGNORECASE | re.UNICODE),
    re.compile(r'\.(\d{3})$', re.IGNORECASE | re.UNICODE)
]

# =============================================================================
# 工具函数
# =============================================================================

def mark_file_as_processed(
    file_path: str,
    *,
    failed_reason: Optional[str] = None,
    is_detection_failed: bool = False
) -> None:
    """标记文件为已处理，记录失败原因（如果有）"""
    DETECTED_FILES.add(file_path)
    if failed_reason:
        if is_detection_failed:
            DETECTION_FAILED[file_path] = failed_reason
        else:
            FAILED_ARCHIVES[file_path] = failed_reason

def get_volume_number(filename: str) -> Tuple[bool, int, Optional[re.Pattern]]:
    """分析文件名，判断是否为分卷文件，并返回分卷号及匹配的正则模式"""
    for pattern in VOLUME_PATTERNS:
        match = pattern.search(filename)
        if match:
            for group in match.groups():
                if group and group.isdigit():
                    return (True, int(group), pattern)
    return (False, 0, None)

def is_first_volume(filename: str) -> bool:
    """判断文件是否为分卷的第一卷"""
    is_volume, number, _ = get_volume_number(filename)
    return is_volume and number == 1

def get_volume_group_key(filename: str) -> Optional[str]:
    """获取分卷组的键，用于识别属于同一分卷组的文件"""
    is_volume, _, pattern = get_volume_number(filename)
    if not is_volume:
        return None
    base = pattern.sub('', filename, count=1)
    ext = next((e for e in ARCHIVE_EXTENSIONS if base.lower().endswith(e)), '')
    return f"{base[:-len(ext)].lower()}|{ext}"

def _check_files() -> Tuple[bool, bool]:
    """检查当前目录下是否有未检测的文件或压缩包"""
    has_undetected = False
    has_archives = False
    current_dir = os.getcwd()
    with os.scandir(current_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            if (entry.path in DETECTED_FILES or
                entry.path in FAILED_ARCHIVES or
                entry.path in DETECTION_FAILED):
                continue
            name = entry.name
            is_volume, _, _ = get_volume_number(name)
            is_known_archive = any(name.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS)
            if is_known_archive or is_volume:
                has_archives = True
            else:
                has_undetected = True
            if has_undetected and has_archives:
                break
    return has_undetected, has_archives

def get_executable_path() -> str:
    """获取当前可执行文件的绝对路径（Nuitka/PyInstaller/Script 均兼容）"""
    if getattr(sys, 'frozen', False):
        return os.path.abspath(sys.executable)
    else:
        return os.path.abspath(sys.argv[0])

# =============================================================================
# 右键菜单管理（仅 Windows）
# =============================================================================

def add_to_context_menu(i18n: I18N) -> None:
    """将程序添加到右键菜单（仅 Windows）"""
    if platform.system() != "Windows" or winreg is None:
        logger.error(i18n._('not_windows'))
        sys.exit(1)

    exe_path = get_executable_path()
    try:
        # 添加到文件夹右键
        key1 = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\shell\\{CONTEXT_MENU_KEY}")
        winreg.SetValue(key1, "", winreg.REG_SZ, i18n._('context_menu_folder_label'))
        winreg.SetValueEx(key1, "Icon", 0, winreg.REG_SZ, f"{exe_path},0")
        winreg.CloseKey(key1)

        cmd1 = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\shell\\{CONTEXT_MENU_KEY}\\command")
        winreg.SetValue(cmd1, "", winreg.REG_SZ, f'"{exe_path}" -y "%1"')
        winreg.CloseKey(cmd1)

        # 添加到目录背景右键
        key2 = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\Background\\shell\\{CONTEXT_MENU_KEY}")
        winreg.SetValue(key2, "", winreg.REG_SZ, i18n._('context_menu_bg_label'))
        winreg.SetValueEx(key2, "Icon", 0, winreg.REG_SZ, f"{exe_path},0")
        winreg.CloseKey(key2)

        cmd2 = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\Background\\shell\\{CONTEXT_MENU_KEY}\\command")
        winreg.SetValue(cmd2, "", winreg.REG_SZ, f'cmd /c "cd /d \"%V\" && \"{exe_path}\" -y"')
        winreg.CloseKey(cmd2)

        logger.info(i18n._('context_menu_added', path=exe_path))
        sys.exit(0)
    except OSError as e:
        logger.error(i18n._('context_menu_add_failed', error=str(e)))
        sys.exit(1)

def remove_from_context_menu(i18n: I18N) -> None:
    """从右键菜单中移除程序入口（仅 Windows）"""
    if platform.system() != "Windows" or winreg is None:
        logger.error(i18n._('not_windows'))
        sys.exit(1)

    try:
        # 删除子项再删父项
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\shell\\{CONTEXT_MENU_KEY}\\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\shell\\{CONTEXT_MENU_KEY}")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\Background\\shell\\{CONTEXT_MENU_KEY}\\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"Directory\\Background\\shell\\{CONTEXT_MENU_KEY}")
        logger.info(i18n._('context_menu_removed'))
        sys.exit(0)
    except OSError as e:
        logger.error(i18n._('context_menu_remove_failed', error=str(e)))
        sys.exit(1)

# =============================================================================
# 文件检测与重命名
# =============================================================================

def detect_and_rename_archives(i18n: I18N) -> None:
    """检测未知文件类型并重命名为正确的压缩包扩展名"""
    current_dir = os.getcwd()
    for entry in os.scandir(current_dir):
        if not entry.is_file():
            continue
        original_ext = os.path.splitext(entry.name)[1].lower()
        if original_ext not in SAFE_EXTENSIONS:
            mark_file_as_processed(entry.path)
            continue
        if (entry.path in DETECTED_FILES or
            entry.path in DETECTION_FAILED or
            any(entry.name.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS)):
            continue
        try:
            kind = filetype.guess(entry.path)
            if kind is None:
                logger.info(i18n._('file_verified', name=entry.name))
                mark_file_as_processed(entry.path)
                continue
            if kind.extension in SUPPORTED_ARCHIVE_TYPES:
                new_ext = '.' + kind.extension
                base_name = os.path.splitext(entry.name)[0]
                new_name = f"{base_name}{new_ext}"
                new_path = os.path.join(current_dir, new_name)
                if os.path.exists(new_path):
                    logger.info(i18n._('rename_skipped', new_path=new_path, old=entry.name))
                    mark_file_as_processed(entry.path)
                    continue
                shutil.move(entry.path, new_name)
                logger.info(i18n._('rename_success', old=entry.name, new=new_name, mime=kind.mime))
            else:
                logger.info(i18n._('file_verified_with_mime', name=entry.name, mime=kind.mime))
                mark_file_as_processed(entry.path)
        except (PermissionError, OSError) as e:
            error_msg = f"Exception: {str(e)}"
            mark_file_as_processed(entry.path, failed_reason=error_msg, is_detection_failed=True)
            logger.error(i18n._('detect_failed', name=entry.name, error=error_msg))

# =============================================================================
# 压缩包安全分析与解压
# =============================================================================

def locate_7zip() -> str:
    """定位 7-Zip 可执行文件路径"""
    bundled = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "7z.exe")
    if os.path.exists(bundled):
        return bundled
    # 应急: 尝试系统 7z
    return "7z"

def analyze_archive_safety(
    archive_path: str,
    i18n: I18N,
    max_unpacked_gb: int,
    max_files: int
) -> Tuple[bool, str, Optional[int]]:
    """分析压缩包的安全性，返回 (是否危险, 原因, 预估解压大小)"""
    try:
        result = subprocess.run(
            [SEVENZIP, 'l', '-slt', archive_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return (False, "", 0)
        output = result.stdout
        unpacked_bytes = 0
        file_count = 0
        unpacked_line = next((l for l in output.splitlines() if l.startswith('Unpacked Size = ')), None)
        if unpacked_line:
            unpacked_str = unpacked_line.split(' = ')[1].strip()
            try:
                if unpacked_str.endswith(' B'):
                    unpacked_bytes = int(unpacked_str.replace(' B', '').replace(',', ''))
                elif unpacked_str.endswith(' KB'):
                    unpacked_bytes = int(float(unpacked_str.replace(' KB', '').replace(',', '')) * 1024)
                elif unpacked_str.endswith(' MB'):
                    unpacked_bytes = int(float(unpacked_str.replace(' MB', '').replace(',', '')) * 1024**2)
                elif unpacked_str.endswith(' GB'):
                    unpacked_bytes = int(float(unpacked_str.replace(' GB', '').replace(',', '')) * 1024**3)
                elif unpacked_str.endswith(' TB'):
                    unpacked_bytes = int(float(unpacked_str.replace(' TB', '').replace(',', '')) * 1024**4)
                else:
                    unpacked_bytes = int(unpacked_str.replace(',', ''))
            except (ValueError, OverflowError):
                unpacked_bytes = 0
        files_line = next((l for l in output.splitlines() if l.startswith('Files = ')), None)
        if files_line:
            try:
                file_count = int(files_line.split(' = ')[1].strip().replace(',', ''))
            except ValueError:
                file_count = 0
        if unpacked_bytes > 0:
            max_bytes = max_unpacked_gb * (1024 ** 3)
            if unpacked_bytes > max_bytes:
                return (True, f"Unpacked size too large ({unpacked_bytes / (1024**3):.1f} GB > {max_unpacked_gb} GB)", None)
            if file_count > max_files:
                return (True, f"Too many files ({file_count} > {max_files})", None)
            archive_size = os.path.getsize(archive_path)
            if archive_size > 0 and unpacked_bytes / archive_size > 1000:
                return (True, f"Compression ratio too high ({unpacked_bytes / archive_size:.0f}:1)", None)
        return (False, "", unpacked_bytes)
    except subprocess.TimeoutExpired:
        return (True, "Metadata read timeout (possibly malicious)", None)
    except Exception as e:
        return (True, f"Check exception: {str(e)}", None)

def unzip(i18n: I18N, config: Config) -> None:
    """解压操作"""
    current_dir = os.getcwd()
    volume_groups: Dict[str, List[str]] = {}
    for entry in os.scandir(current_dir):
        if entry.is_file() and entry.path not in FAILED_ARCHIVES:
            is_volume, _, _ = get_volume_number(entry.name)
            if is_volume:
                group_key = get_volume_group_key(entry.name)
                if group_key:
                    volume_groups.setdefault(group_key, []).append(entry.path)
    processed_groups = set()
    for entry in os.scandir(current_dir):
        if not entry.is_file() or entry.path in FAILED_ARCHIVES:
            continue
        name_lower = entry.name.lower()
        is_volume, _, _ = get_volume_number(entry.name)
        is_known_archive = any(name_lower.endswith(ext) for ext in ARCHIVE_EXTENSIONS)
        if not (is_known_archive or is_volume):
            continue
        group_key = get_volume_group_key(entry.name) if is_volume else None
        if is_volume:
            if not is_first_volume(entry.name) or group_key in processed_groups:
                continue
            processed_groups.add(group_key)
        is_dangerous, reason, unpacked_bytes = analyze_archive_safety(entry.path, i18n, max_unpacked_gb=config.max_unpacked_gb, max_files=config.max_files)
        if is_dangerous:
            error_msg = f"Safety check failed: {reason}"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.warning(i18n._('unsafe_archive', name=entry.name, reason=reason))
            continue
        try:
            free_bytes = shutil.disk_usage('.').free
            buffer_bytes = max(unpacked_bytes // 10, 1 * (1024**3))
            required_bytes = unpacked_bytes + buffer_bytes
            if free_bytes < required_bytes:
                needed_gb = required_bytes / (1024**3)
                free_gb = free_bytes / (1024**3)
                error_msg = f"Insufficient disk space (need {needed_gb:.1f} GB, free {free_gb:.1f} GB)"
                mark_file_as_processed(entry.path, failed_reason=error_msg)
                logger.warning(i18n._('disk_low', name=entry.name, error=error_msg))
                continue
        except OSError as e:
            error_msg = f"Disk check failed: {e}"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.warning(i18n._('disk_low', name=entry.name, error=error_msg))
            continue
        try:
            logger.info(i18n._('unzipping', name=entry.name))
            result = subprocess.run(
                [SEVENZIP, 'x', entry.path, '-y'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                if is_volume and group_key in volume_groups:
                    for vol_path in volume_groups[group_key]:
                        if os.path.exists(vol_path):
                            os.remove(vol_path)
                            logger.info(i18n._('volume_deleted', name=os.path.basename(vol_path)))
                else:
                    if os.path.exists(entry.path):
                        os.remove(entry.path)
                        logger.info(i18n._('unzip_success_delete', name=entry.name))
                mark_file_as_processed(entry.path)
            else:
                error_msg = result.stderr.strip() or "7-Zip returned non-zero exit code"
                mark_file_as_processed(entry.path, failed_reason=error_msg)
                logger.error(i18n._('unzip_failed', name=entry.name, error=error_msg))
        except subprocess.TimeoutExpired:
            error_msg = "Extraction timeout (300s)"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.error(i18n._('unzip_failed', name=entry.name, error=error_msg))
        except (PermissionError, OSError) as e:
            error_msg = f"System error: {str(e)}"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.error(i18n._('unzip_failed', name=entry.name, error=error_msg))

# =============================================================================
# 清理与报告
# =============================================================================

def remove_target(
    folder_path: str,
    file_set: Set[str],
    remove_target_files: bool,
    remove_empty_dirs: bool,
    i18n: I18N
) -> None:
    """删除目标文件和/或空文件夹"""
    if not (remove_target_files or remove_empty_dirs):
        return
    stack = [folder_path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                subdirs = []
                has_files = False
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        subdirs.append(entry.path)
                        has_files = True
                    elif entry.is_file():
                        if remove_target_files and entry.name in file_set:
                            try:
                                os.remove(entry.path)
                                logger.info(i18n._('file_deleted', path=entry.path))
                            except (PermissionError, OSError) as e:
                                logger.error(i18n._('delete_failed', path=entry.path, error=e))
                        else:
                            has_files = True
                if remove_empty_dirs or remove_target_files:
                    stack.extend(reversed(subdirs))
        except OSError as e:
            logger.error(i18n._('dir_access_failed', path=current, error=e))
            continue
        if remove_empty_dirs and not has_files:
            try:
                os.rmdir(current)
                logger.info(i18n._('folder_deleted', path=current))
            except OSError:
                pass

def print_detection_failure_report(i18n: I18N) -> None:
    """打印检测失败报告"""
    if not DETECTION_FAILED:
        return
    logger.info(f"\n{'='*50}")
    logger.info(i18n._('detect_fail_report_header', count=len(DETECTION_FAILED)))
    logger.info(f"{'='*50}")
    for path, err in DETECTION_FAILED.items():
        logger.info(f"\n{i18n._('file_label', name=os.path.basename(path))}")
        logger.info(f"{i18n._('path_label', path=path)}")
        logger.info(f"{i18n._('reason_label', reason=err)}")
    logger.info(f"{'='*50}\n")

def print_failure_report(i18n: I18N) -> None:
    """打印解压失败报告"""
    if not FAILED_ARCHIVES:
        return
    logger.info(f"\n{'='*50}")
    logger.info(i18n._('unzip_fail_report_header', count=len(FAILED_ARCHIVES)))
    logger.info(f"{'='*50}")
    for path, err in FAILED_ARCHIVES.items():
        logger.info(f"\n{i18n._('file_label', name=os.path.basename(path))}")
        logger.info(f"{i18n._('path_label', path=path)}")
        logger.info(f"{i18n._('reason_label', reason=err)}")
    logger.info(f"{'='*50}\n")

# =============================================================================
# 参数解析与主逻辑
# =============================================================================

def parse_args() -> Config:
    """解析命令行参数"""
    temp_parser = argparse.ArgumentParser(add_help=False)
    temp_parser.add_argument('-L', '--language', default='auto')
    temp_args, _ = temp_parser.parse_known_args()
    lang = get_system_language() if temp_args.language == 'auto' else temp_args.language
    if lang not in MESSAGES:
        lang = 'en'
    texts = MESSAGES[lang]['argparse']
    parser = argparse.ArgumentParser(
        description=texts['description'],
        epilog=texts['epilog'],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-y', '--yes', action='store_true', help=texts['yes'])
    parser.add_argument('-n', '--no', action='store_true', help=texts['no'])
    parser.add_argument('-t', '--delete-target-files', action='store_true', help=texts['delete_target'])
    parser.add_argument('-e', '--delete-empty-folders', action='store_true', help=texts['delete_empty'])
    parser.add_argument('-l', '--delete-list', nargs='*', default=[], help=texts['delete_list'])
    parser.add_argument('-f', '--delete-list-file', type=str, default=None, help=texts['list_file'])
    parser.add_argument('-g', '--generate-delete-list-file', action='store_true', help=texts['gen_list'])
    parser.add_argument('--add-context-menu', action='store_true', help=texts['add_context_menu'])
    parser.add_argument('--remove-context-menu', action='store_true', help=texts['remove_context_menu'])
    parser.add_argument('--max-unpacked-gb', type=int, default=50, help=texts['max_unpacked_gb'])
    parser.add_argument('--max-files', type=int, default=10000, help=texts['max_files'])
    language_choices = ['auto'] + get_available_languages()
    parser.add_argument('-L', '--language',
                        choices=language_choices,
                        default='auto',
                        help=texts['language'])
    args = parser.parse_args()
    if args.yes and args.no:
        error_msg = MESSAGES[lang].get('yes_no_conflict', "Arguments -y and -n cannot be used together")
        parser.error(error_msg)
    return Config(
        delete_target_files=args.delete_target_files,
        delete_empty_folders=args.delete_empty_folders,
        auto_yes=args.yes,
        auto_no=args.no,
        delete_list=args.delete_list,
        delete_list_file=args.delete_list_file,
        generate_delete_list_file=args.generate_delete_list_file,
        add_context_menu=args.add_context_menu,
        remove_context_menu=args.remove_context_menu,
        max_unpacked_gb=args.max_unpacked_gb,
        max_files=args.max_files,
        language=lang
    )

def generate_default_delete_list_file(i18n: I18N) -> None:
    """生成默认的删除列表文件"""
    default_content = i18n._('delete_list_template').rstrip() + '\n'
    filename = "delete_list.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(default_content)
        logger.info(i18n._('generate_success', filename=filename))
        logger.info(i18n._('generate_tip'))
    except Exception as e:
        logger.error(i18n._('generate_fail', filename=filename, error=str(e)))
        sys.exit(1)
    sys.exit(0)

def load_delete_list_from_file(filepath: str, i18n: I18N) -> Set[str]:
    """从文件加载删除列表"""
    file_set = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith('//') or not stripped:
                    continue
                file_set.add(stripped)
    except Exception as e:
        logger.error(i18n._('list_file_read_fail', filepath=filepath, error=e))
        sys.exit(1)
    return file_set

def build_delete_file_set(config: Config, i18n: I18N) -> Set[str]:
    """构建要删除的文件集合"""
    file_set = set(config.delete_list)
    if config.delete_list_file:
        file_set.update(load_delete_list_from_file(config.delete_list_file, i18n))
    else:
        default_file = "delete_list.txt"
        if os.path.exists(default_file):
            file_set.update(load_delete_list_from_file(default_file, i18n))
    return file_set

def should_delete_target_files(config: Config, i18n: I18N) -> bool:
    """询问用户是否删除目标文件"""
    
    if not FILE_NAME_SET:
        logger.info(i18n._('no_target_files')+'\n')
        return False
    
    if config.auto_no:
        return False
    
    print(i18n._('delete_target_intro'))
    for filename in sorted(FILE_NAME_SET):
        print(f" - {filename}")

    if config.auto_yes or config.delete_target_files:
        return True
    return input("\n"+i18n._('prompt_delete_files')+"\n").lower() == 'y'

def should_delete_empty_folders(config: Config, i18n: I18N) -> bool:
    """询问用户是否删除空文件夹"""
    if config.auto_yes or config.delete_empty_folders:
        print("\n" + i18n._('delete_empty_dirs_intro'))
        return True
    
    if config.auto_no:
        return False
    
    return input(i18n._('prompt_delete_dirs')+"\n").lower() == 'y'

def run_main_loop(i18n: I18N, config: Config) -> None:
    """主处理循环"""
    logger.info("="*50)
    logger.info(i18n._('welcome'))
    for feat in MESSAGES[i18n.lang]['features']:
        logger.info(feat)
    logger.info(i18n._('safety_limits', max_gb=config.max_unpacked_gb, max_files=config.max_files))
    logger.info(i18n._('start_processing'))
    try:
        while True:
            has_undetected, has_archives = _check_files()
            if not has_undetected and not has_archives:
                logger.info(i18n._('no_files_left'))
                break
            if has_undetected:
                logger.info(i18n._('detecting_undetected'))
                detect_and_rename_archives(i18n)
            if has_archives:
                logger.info(i18n._('detecting_archives'))
                unzip(i18n, config)
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info(i18n._('interrupted')+'\n')
    finally:
        logger.info(i18n._('main_loop_done'))
        if not FAILED_ARCHIVES:
            logger.info(i18n._('processing_done')+'\n')
        else:
            print()

def print_cikezzz_colored():
    """打印彩色 CikeZZZ Logo"""
    art_lines = [
        " ____    ____      _      ______   ________   ______ ____  ____  ",
        "|_   \  /   _|    / \    |_   _ `.|_   __  | |_   _ \_  _||_  _| ",
        "  |   \/   |     / _ \     | | `. \ | |_ \_|   | |_) |\ \  / /   ",
        "  | |\  /| |    / ___ \    | |  | | |  _| _    |  __'. \ \/ /    ",
        " _| |_\/_| |_ _/ /   \ \_ _| |_.' /_| |__/ |  _| |__) |_|  |_    ",
        "|_____||_____|____| |____|______.'|________| |_______/|______|   ",
        "   ______  _____ ___  ____  ________ ________ ________ ________  ",
        " .' ___  ||_   _|_  ||_  _||_   __  |  __   _|  __   _|  __   _| ",
        "/ .'   \_|  | |   | |_/ /    | |_ \_|_/  / / |_/  / / |_/  / /   ",
        "| |         | |   |  __'.    |  _| _   .'.' _   .'.' _   .'.' _  ",
        "\ `.___.'\ _| |_ _| |  \ \_ _| |__/ |_/ /__/ |_/ /__/ |_/ /__/ | ",
        " `.____ .'|_____|____||____|________|________|________|________| ",
    ]
    color1 = "\033[38;5;91m"
    color2 = "\033[38;5;69m"
    reset = "\033[0m"
    for i, line in enumerate(art_lines):
        color = color1 if i < 6 else color2
        print(color + line + reset)

# =============================================================================
# 主入口
# =============================================================================

def main() -> None:
    """程序主入口"""
    print_cikezzz_colored()
    config = parse_args()
    i18n = I18N(config.language)

    # 优先处理右键菜单命令（早退出）
    if config.add_context_menu:
        add_to_context_menu(i18n)
    if config.remove_context_menu:
        remove_from_context_menu(i18n)
    if config.generate_delete_list_file:
        generate_default_delete_list_file(i18n)

    global SEVENZIP, FILE_NAME_SET
    FILE_NAME_SET = build_delete_file_set(config, i18n)
    SEVENZIP = locate_7zip()
    run_main_loop(i18n, config)
    
    remove_target_files = should_delete_target_files(config, i18n)
    remove_empty_dirs = should_delete_empty_folders(config, i18n)
    remove_target(".", FILE_NAME_SET, remove_target_files, remove_empty_dirs, i18n)
    
    print_detection_failure_report(i18n)
    print_failure_report(i18n)
    
    logger.info(i18n._('all_done')+'\n')

    if not any([
        config.auto_yes, config.auto_no,
        config.delete_target_files, config.delete_empty_folders,
        config.delete_list, config.delete_list_file,
        config.generate_delete_list_file,
    ]):
        input(i18n._('press_enter_exit')+"\n")
if __name__ == "__main__":
    main()
