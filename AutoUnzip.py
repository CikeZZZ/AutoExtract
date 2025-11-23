#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = "1.0.0"
# =============================================================================
# 1. 初始化与全局配置
# =============================================================================

import os
import sys

# 禁用输出缓冲（必须在最开始！）
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
else:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

import shutil
import subprocess
import time
import re
import filetype
import logging
import argparse
from dataclasses import dataclass
from typing import Set, Dict, Tuple, List, Optional

@dataclass
class Config:
    delete_target_files: bool       # -t 删除预设垃圾文件
    delete_empty_folders: bool      # -e 删除空文件夹
    auto_yes: bool                  # -y 全局确认
    auto_no: bool                   # -n 全局拒绝
    delete_list: List[str]          # -l 命令行指定要删除的文件名列表
    delete_list_file: Optional[str] # -f 指定删除列表文件路径
    generate_delete_list_file: bool # -g 生成默认删除列表文件


# ---------------- 全局状态 ----------------
DETECTED_FILES: Set[str] = set()          # 已处理文件（避免重复）
FAILED_ARCHIVES: Dict[str, str] = {}      # 解压失败
DETECTION_FAILED: Dict[str, str] = {}     # 检测失败

# ---------------- 日志配置 ----------------
logging.basicConfig(
    format="%(asctime)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ---------------- 安全配置 ----------------
SAFE_EXTENSIONS = {
    # 图片
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    # 文本
    '.txt', '.log', '.ini', '.cfg', '.md',
    # 音视频
    '.mp3', '.wav', '.mp4', '.avi', '.mkv',
    # 可执行文件（保留但不处理）
    '.exe', '.dll', '.bat', '.sh',
    # 其他
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

FILE_NAME_SET = {
    "点我检查更新.bat",
    "更多单机游戏COS写真免费下载.txt",
    "国际机场-梯子.txt",
    "小黄油,galgame,cos福利… 每天更新！.url",
    "扫码免费下载.png",
    "橙荔游戏，免费分享.url",
    "自用梯子（VPN）推荐.url",
    "免责声明.txt",
    "免费搬运，玩前必读！！.txt",
    "免费游戏发布页steamcl.com.txt",
    "免费游戏永久发布页（双击打开我收藏）.url"
}

# =============================================================================
# 2. 状态管理工具
# =============================================================================

def mark_file_as_processed(
    file_path: str,
    *,
    failed_reason: Optional[str] = None,
    is_detection_failed: bool = False
) -> None:
    """统一标记文件为已处理"""
    DETECTED_FILES.add(file_path)
    if failed_reason:
        if is_detection_failed:
            DETECTION_FAILED[file_path] = failed_reason
        else:
            FAILED_ARCHIVES[file_path] = failed_reason

# =============================================================================
# 3. 分卷文件处理工具
# =============================================================================

def get_volume_number(filename: str) -> Tuple[bool, int, Optional[re.Pattern]]:
    """提取分卷编号"""
    for pattern in VOLUME_PATTERNS:
        match = pattern.search(filename)
        if match:
            for group in match.groups():
                if group and group.isdigit():
                    return (True, int(group), pattern)
    return (False, 0, None)

def is_first_volume(filename: str) -> bool:
    """是否为第一个分卷"""
    is_volume, number, _ = get_volume_number(filename)
    return is_volume and number == 1

def get_volume_group_key(filename: str) -> Optional[str]:
    """生成分卷组唯一标识"""
    is_volume, _, pattern = get_volume_number(filename)
    if not is_volume:
        return None
    base = pattern.sub('', filename, count=1)
    ext = next((e for e in ARCHIVE_EXTENSIONS if base.lower().endswith(e)), '')
    return f"{base[:-len(ext)].lower()}|{ext}"

# =============================================================================
# 4. 文件扫描与检测
# =============================================================================

def _check_files() -> Tuple[bool, bool]:
    """检查是否存在未处理的普通文件或压缩包"""
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

def detect_and_rename_archives() -> None:
    """检测伪装压缩包并重命名"""
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
                logger.info(f"🔍 验证: {entry.name} 是普通文件")
                mark_file_as_processed(entry.path)
                continue

            if kind.extension in SUPPORTED_ARCHIVE_TYPES:
                new_ext = '.' + kind.extension
                base_name = os.path.splitext(entry.name)[0]
                new_name = f"{base_name}{new_ext}"
                new_path = os.path.join(current_dir, new_name)
                
                if os.path.exists(new_path):
                    logger.info(f"目标文件 {new_path} 已存在，跳过 {entry.name}")
                    mark_file_as_processed(entry.path)
                    continue
                
                shutil.move(entry.path, new_name)
                logger.info(f"✅ 重命名: {entry.name} → {new_name} (类型: {kind.mime})")
            else:
                logger.info(f"🔍 验证: {entry.name} 是普通文件 ({kind.mime})")
                mark_file_as_processed(entry.path)
                
        except (PermissionError, OSError) as e:
            error_msg = f"检测异常: {str(e)}"
            mark_file_as_processed(entry.path, failed_reason=error_msg, is_detection_failed=True)
            logger.error(f"检测失败: {entry.name} → {error_msg}")

# =============================================================================
# 5. 压缩包安全分析与解压
# =============================================================================

def analyze_archive_safety(
    archive_path: str, 
    max_unpacked_gb: int = 50, 
    max_files: int = 10000
) -> Tuple[bool, str, Optional[int]]:
    """
    分析压缩包安全性，并返回解压后大小（字节）。
    返回: (is_dangerous, reason, unpacked_bytes_or_None)
    """
    try:
        result = subprocess.run(
            [SEVENZIP, 'l', '-slt', archive_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            # 7z 无法读取（如损坏文件），不视为炸弹，后续解压会失败
            return (False, "", 0)
        
        output = result.stdout
        
        # 默认值：空压缩包 → 0 字节，0 文件
        unpacked_bytes = 0
        file_count = 0
        
        # 尝试解析 Unpacked Size
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
                unpacked_bytes = 0  # 解析失败，保守设为0
        
        # 尝试解析 Files
        files_line = next((l for l in output.splitlines() if l.startswith('Files = ')), None)
        if files_line:
            try:
                file_count = int(files_line.split(' = ')[1].strip().replace(',', ''))
            except ValueError:
                file_count = 0
        
        # 🔒 仅当 unpacked_bytes > 0 时才做炸弹检查
        if unpacked_bytes > 0:
            max_bytes = max_unpacked_gb * (1024 ** 3)
            if unpacked_bytes > max_bytes:
                return (True, f"解压后体积过大 ({unpacked_bytes / (1024**3):.1f} GB > {max_unpacked_gb} GB)", None)
            if file_count > max_files:
                return (True, f"文件数量过多 ({file_count} > {max_files})", None)
            archive_size = os.path.getsize(archive_path)
            if archive_size > 0 and unpacked_bytes / archive_size > 1000:
                return (True, f"压缩比异常高 ({unpacked_bytes / archive_size:.0f}:1)", None)
        
        # ✅ 安全：返回实际或估算的解压大小（0 也是合法值）
        return (False, "", unpacked_bytes)
        
    except subprocess.TimeoutExpired:
        return (True, "元数据读取超时（可能为恶意文件）", None)
    except Exception as e:
        return (True, f"检查异常: {str(e)}", None)

def unzip() -> None:
    """安全解压压缩文件"""
    current_dir = os.getcwd()
    volume_groups: Dict[str, List[str]] = {}
    
    # 预先收集分卷组（仅针对未失败的文件）
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
        
        # 提前判断是否为压缩文件或分卷！
        name_lower = entry.name.lower()
        is_volume, _, _ = get_volume_number(entry.name)
        is_known_archive = any(name_lower.endswith(ext) for ext in ARCHIVE_EXTENSIONS)
        
        # 若既不是已知压缩格式，也不是分卷文件 → 跳过
        if not (is_known_archive or is_volume):
            continue

        # 处理分卷组逻辑
        group_key = get_volume_group_key(entry.name) if is_volume else None
        if is_volume:
            if not is_first_volume(entry.name) or group_key in processed_groups:
                continue
            processed_groups.add(group_key)
        
        # 安全分析：检查 ZIP 炸弹
        is_dangerous, reason, unpacked_bytes = analyze_archive_safety(entry.path)
        if is_dangerous:
            error_msg = f"安全检查未通过: {reason}"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.warning(f"⚠️ 跳过危险文件: {entry.name} → {reason}")
            continue

        # 动态磁盘空间检查
        try:
            free_bytes = shutil.disk_usage('.').free
            buffer_bytes = max(unpacked_bytes // 10, 1 * (1024**3))  # 10% 或至少 1GB
            required_bytes = unpacked_bytes + buffer_bytes
            
            if free_bytes < required_bytes:
                needed_gb = required_bytes / (1024**3)
                free_gb = free_bytes / (1024**3)
                error_msg = f"磁盘空间不足（需 {needed_gb:.1f} GB，剩余 {free_gb:.1f} GB）"
                mark_file_as_processed(entry.path, failed_reason=error_msg)
                logger.warning(f"⚠️ 跳过 {entry.name} → {error_msg}")
                continue
        except OSError as e:
            error_msg = f"磁盘检查失败: {e}"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.warning(f"⚠️ 跳过 {entry.name} → {error_msg}")
            continue

        # 执行解压
        try:
            logger.info(f"正在解压: {entry.name}")
            result = subprocess.run(
                [SEVENZIP, 'x', entry.path, '-y'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # 解压成功：删除源文件
                if is_volume and group_key in volume_groups:
                    for vol_path in volume_groups[group_key]:
                        if os.path.exists(vol_path):
                            os.remove(vol_path)
                            logger.info(f"已删除分卷文件: {os.path.basename(vol_path)}")
                else:
                    if os.path.exists(entry.path):
                        os.remove(entry.path)
                        logger.info(f"解压成功并删除源文件: {entry.name}")
                mark_file_as_processed(entry.path)  # 标记为已处理（成功）
            else:
                error_msg = result.stderr.strip() or "7-Zip 退出码非0"
                mark_file_as_processed(entry.path, failed_reason=error_msg)
                logger.error(f"解压失败: {entry.name} → {error_msg}")
                
        except subprocess.TimeoutExpired:
            error_msg = "解压超时 (300秒)"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.error(f"解压失败: {entry.name} → {error_msg}")
        except (PermissionError, OSError) as e:
            error_msg = f"系统错误: {str(e)}"
            mark_file_as_processed(entry.path, failed_reason=error_msg)
            logger.error(f"解压失败: {entry.name} → {error_msg}")

# =============================================================================
# 6. 清理与报告
# =============================================================================

def remove_target(
    folder_path: str,
    file_set: Set[str],
    remove_target_files: bool = True,
    remove_empty_dirs: bool = True
) -> None:
    """
    高效递归清理：可分别控制是否删除指定文件、是否删除空文件夹。
    
    参数:
        folder_path: 起始目录
        file_set: 要删除的文件名集合（如 {"a.txt", "b.bat"}）
        remove_target_files: 是否删除 file_set 中的文件
        remove_empty_dirs: 是否删除空文件夹（包括清理后变空的）
    """
    if not (remove_target_files or remove_empty_dirs):
        return  # 无操作，直接退出

    stack = [folder_path]
    
    while stack:
        current = stack.pop()
        
        try:
            with os.scandir(current) as entries:
                subdirs = []
                has_files = False  # 当前目录是否有非目标文件或子目录
                
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        subdirs.append(entry.path)
                        has_files = True  # 有子目录，不算空
                    elif entry.is_file():
                        if remove_target_files and entry.name in file_set:
                            try:
                                os.remove(entry.path)
                                logger.info(f"🗑️ 已删除文件: {entry.path}")
                            except (PermissionError, OSError) as e:
                                logger.error(f"❌ 删除失败 {entry.path}: {e}")
                        else:
                            has_files = True  # 有非目标文件，不算空
                
                # 只有需要删空文件夹时，才递归子目录
                if remove_empty_dirs:
                    stack.extend(reversed(subdirs))
                elif remove_target_files:
                    # 如果只删文件，仍需递归（因为子目录可能含目标文件）
                    stack.extend(reversed(subdirs))
                # 否则（只删空文件夹 + 不删文件）？其实 remove_empty_dirs=True 已覆盖
                
        except OSError as e:
            logger.error(f"📁 无法访问目录 {current}: {e}")
            continue

        # 尝试删除空文件夹（仅当启用且当前目录为空）
        if remove_empty_dirs and not has_files:
            try:
                os.rmdir(current)
                logger.info(f"🧹 已删除空文件夹: {current}")
            except OSError:
                # 可能被其他进程占用，或非空（竞态），忽略
                pass

def print_detection_failure_report() -> None:
    """打印检测失败报告"""
    if not DETECTION_FAILED:
        return
    logger.info(f"\n{'='*50}")
    logger.info(f"⚠️ 文件类型检测失败 (共 {len(DETECTION_FAILED)} 个文件):")
    logger.info(f"{'='*50}")
    for path, err in DETECTION_FAILED.items():
        logger.info(f"\n文件: {os.path.basename(path)}")
        logger.info(f"路径: {path}")
        logger.info(f"原因: {err}")
    logger.info(f"{'='*50}\n")

def print_failure_report() -> None:
    """打印解压失败报告"""
    if not FAILED_ARCHIVES:
        return
    logger.info(f"\n{'='*50}")
    logger.info(f"❌ 解压失败报告 (共 {len(FAILED_ARCHIVES)} 个文件):")
    logger.info(f"{'='*50}")
    for path, err in FAILED_ARCHIVES.items():
        logger.info(f"\n文件: {os.path.basename(path)}")
        logger.info(f"路径: {path}")
        logger.info(f"原因: {err}")
    logger.info(f"{'='*50}\n")

# =============================================================================
# 7. 主程序入口
# =============================================================================

def locate_7zip() -> str:
    """自动定位 7z.exe 路径"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "7z.exe")
    else:
        return os.path.join(os.path.dirname(__file__), "7z.exe")

def validate_7zip(sevenzip_path: str) -> None:
    """验证 7z.exe 是否存在且可执行"""
    if not os.path.exists(sevenzip_path):
        logger.error(f"错误：未找到 7z.exe ({sevenzip_path})")
        exit(1)
    if not os.access(sevenzip_path, os.X_OK):
        logger.error(f"错误：7z.exe 无执行权限 ({sevenzip_path})")
        exit(1)

def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="智能压缩包处理工具",
        epilog="示例: %(prog)s -y  # 自动处理"
    )
    # 添加版本参数（支持 -v 和 --version）
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
        help='显示版本号并退出'
    )
    # 全局行为控制
    parser.add_argument('-y', '--yes', action='store_true',
                        help='对所有交互式提示自动回答“是”')
    parser.add_argument('-n', '--no', action='store_true',
                        help='对所有交互式提示自动回答“否”')
    
    # 功能开关
    parser.add_argument('-t','--delete-target-files', action='store_true',
                        help='删除预设的垃圾文件（默认会询问）')
    parser.add_argument('-e','--delete-empty-folders', action='store_true',
                        help='删除空文件夹（默认会询问）')
    
    # 删除列表参数
    parser.add_argument('-l','--delete-list', nargs='*', default=[],
                        help='指定要删除的文件名（可多个）')
    parser.add_argument('-f','--delete-list-file', type=str, default=None,
                        help='从文件读取要删除的文件名列表（每行一个，// 开头为注释）')
    
    # 生成默认删除列表文件
    parser.add_argument(
        '-g', '--generate-delete-list-file',
        action='store_true',
        help='生成默认的删除列表文件 delete_list.txt 并退出'
    )

    args = parser.parse_args()
    
    # 确保 -y 和 -n 不同时出现（argparse 默认不检查，需手动处理）
    if args.yes and args.no:
        parser.error("参数 -y 和 -n 不能同时使用")
    
    return Config(
        delete_target_files= args.delete_target_files,
        delete_empty_folders=args.delete_empty_folders,
        delete_list=args.delete_list,
        delete_list_file=args.delete_list_file,
        generate_delete_list_file=args.generate_delete_list_file,
        auto_yes=args.yes,
        auto_no=args.no
    )

def generate_default_delete_list_file() -> None:
    """生成默认的删除列表文件 delete_list.txt"""
    default_content = """// 删除列表文件（每行一个文件名，// 开头为注释）
// 你可以根据需要编辑此文件，添加或删除文件名
"""
    filename = "delete_list.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(default_content)
        print(f"✅ 已生成删除列表文件: {filename}")
        print("💡 你可以编辑此文件，然后运行本程序进行清理。")
    except Exception as e:
        print(f"❌ 无法写入文件 {filename}: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)  # 成功生成后直接退出

def load_delete_list_from_file(filepath: str) -> Set[str]:
    """从文件加载要删除的文件名，忽略以 // 开头的注释行"""
    file_set = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith('//') or not stripped:
                    continue
                file_set.add(stripped)
    except Exception as e:
        logger.error(f"❌ 无法读取删除列表文件 {filepath}: {e}")
        sys.exit(1)
    return file_set

def build_delete_file_set(config: Config) -> Set[str]:
    """
    根据配置构建要删除的文件名集合。
    优先级：--delete-list（命令行） + --delete-list-file（指定文件） > 默认 delete_list.txt
    """
    file_set = set(config.delete_list)

    if config.delete_list_file:
        # 显式指定了删除列表文件，必须加载
        file_set.update(load_delete_list_from_file(config.delete_list_file))
    else:
        # 未指定文件，尝试加载默认的 delete_list.txt（仅当存在时）
        default_file = "delete_list.txt"
        if os.path.exists(default_file):
            file_set.update(load_delete_list_from_file(default_file))
        # 若不存在，默认为空，不报错（静默跳过）

    return file_set

def should_delete_target_files(config: Config) -> bool:
    """决定是否删除预设垃圾文件"""
    if config.auto_yes or config.delete_target_files:
        if FILE_NAME_SET:
            print("\n🗑️ 将删除以下指定文件：")
            for filename in sorted(FILE_NAME_SET):
                print(f" - {filename}")
        else:
            print("⚠️ 未指定任何要删除的文件（删除列表为空）")
        return True
    
    if config.auto_no:
        return False
    
    if FILE_NAME_SET:
        print("\n🗑️ 将删除以下指定文件：")
        for filename in sorted(FILE_NAME_SET):
            print(f" - {filename}")
    else:
        print("⚠️ 未指定任何要删除的文件（删除列表为空）")
    return input("❓ 是否删除这些文件？(y/N): ").lower() == 'y'

def should_delete_empty_folders(config: Config) -> bool:
    """决定是否删除空文件夹"""
    if config.auto_yes or config.delete_empty_folders:
        print("\n🗑️ 将删除空文件夹...")
        return True
    if config.auto_no:
        return False
    return input("❓ 是否删除空文件夹？(y/N): ").lower() == 'y'

def run_main_loop() -> None:
    """主处理循环：检测 → 重命名 → 解压，直到无文件可处理"""
    logger.info("\n========================================")
    logger.info("智能压缩包处理工具")
    logger.info("- 自动识别伪装压缩包（如 .jpg 实为 .zip等）")
    logger.info("- 安全解压分卷文件（.part1, .z01, .001 等）")
    logger.info("- 防御 ZIP 炸弹 + 动态磁盘空间检查")
    logger.info("- 自动清理垃圾文件")
    logger.info("- 支持分卷格式: part1/vol1、.z01、.001 等")
    logger.info("开始处理文件...")
    try:
        while True:
            has_undetected, has_archives = _check_files()
            
            if not has_undetected and not has_archives:
                logger.info("✅ 未检测到可处理的文件，处理完成")
                break
            
            if has_undetected:
                logger.info("🔍 检测到潜在压缩文件，正在识别...")
                detect_and_rename_archives()
            
            if has_archives:
                logger.info("📦 检测到压缩文件，开始安全解压...")
                unzip()
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("⚠️ 程序被用户中断")
    finally:
        logger.info("✅ 处理流程已结束")
        if not FAILED_ARCHIVES:
            logger.info("✅ 所有压缩包均已成功解压！")
            return
def print_cikezzz_colored():
    # 定义你的 ASCII 图（注意：保留原始空格和换行）
    art_lines = [
        " ____    ____      _      ______   ________   ______ ____  ____ ",
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

def main() -> None:
    """程序总入口"""

    print_cikezzz_colored()

    global SEVENZIP, FILE_NAME_SET
    
    # 解析配置
    config = parse_args()

    if config.generate_delete_list_file:
        generate_default_delete_list_file()

    # 构建删除文件名集合
    FILE_NAME_SET = build_delete_file_set(config)

    # 定位并验证 7z.exe
    SEVENZIP = locate_7zip()
    
    # 执行主处理循环
    run_main_loop()
    
    # 清理操作（分两步，独立控制）
    remove_target_files = should_delete_target_files(config)
    remove_empty_dirs = should_delete_empty_folders(config)
    remove_target(
            folder_path=".",
            file_set=FILE_NAME_SET,
            remove_target_files=remove_target_files,
            remove_empty_dirs=remove_empty_dirs
        )
    
    # 打印失败报告
    print_detection_failure_report()
    print_failure_report()
    
    logger.info("✅ 所有操作已完成！")

    # 若无交互式操作，等待用户回车退出
    if not any([
        config.auto_yes,
        config.auto_no,
        config.delete_target_files,
        config.delete_empty_folders,
        config.delete_list,          # 非空 list 为 True
        config.delete_list_file,      # 非 None 字符串为 True
        config.generate_delete_list_file
    ]):
        input("🔚 按回车键退出...")

if __name__ == "__main__":
    main()