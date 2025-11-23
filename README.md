# CikeZZZ AutoExtract

一款由 Nuitka 打包的全独立智能解压与清理工具 —— 无需 Python，开箱即用。

---

## ✨ 核心优势

- ✅ **真正独立可执行**：单文件 `.exe`（Windows）或二进制（Linux/macOS），**无需安装 Python 或任何依赖**
- 📦 **内置 7-Zip 引擎**：程序目录自动携带 `7z.exe`（Windows）或调用系统 7z，无需额外安装
- 🔍 **智能格式识别**：自动将无扩展名或错误扩展名的文件重命名为正确压缩格式
- 🛡️ **多重安全保障**：
  - 防压缩炸弹（Zip Bomb）
  - 最大解压体积限制（默认 50 GB）
  - 最大文件数限制（默认 10,000）
  - 解压前磁盘空间检查
- 🖱️ **集成右键菜单**（Windows）：解压整个文件夹只需右键点击
- 🌐 **四语界面**：简体中文 / 繁体中文 / English / 日本語，自动匹配系统语言，也可手动指定
- 🧹 **自定义清理规则**：支持 `delete_list.txt` 删除垃圾文件（如 `@eaDir`, `Thumbs.db`）

---

## 🚀 快速开始

### Windows 用户
1. 下载 `AutoExtract.exe` 与 `7z.exe`（若未内嵌）
2. 将文件放在任意目录（如 `D:\Tools\`）
3. 双击运行，或在命令行使用：

```cmd
:: 自动解压当前目录所有压缩包（无需确认）
AutoExtract.exe -y

:: 解压后删除垃圾文件 + 空文件夹
AutoExtract.exe -y -t -e

:: 添加右键菜单（需管理员权限）
AutoExtract.exe --add-context-menu
```

> 💡 **提示**：Nuitka 打包版本已包含 `filetype` 等所有 Python 依赖，**无需 `pip install`**！

---

## ⚙️ 常用命令
```
optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -y, --yes             自动回答所有提示为“是”
  -n, --no              自动回答所有提示为“否”
  -t, --delete-target-files
                        删除指定的垃圾文件
  -e, --delete-empty-folders
                        删除空文件夹
  -l [DELETE_LIST [DELETE_LIST ...]], --delete-list [DELETE_LIST [DELETE_LIST ...]]
                        要删除的文件名（空格分隔）
  -f DELETE_LIST_FILE, --delete-list-file DELETE_LIST_FILE
  -g, --generate-delete-list-file
                        生成 delete_list.txt
  --add-context-menu    将本程序添加到 Windows 右键菜单（文件夹和空白处）
  --remove-context-menu
                        从 Windows 右键菜单中移除本程序
  --max-unpacked-gb MAX_UNPACKED_GB
                        最大允许解压大小（GB），默认 50 GB
  --max-files MAX_FILES
                        最大允许文件数，默认 10000 个
  -L {auto,zh,zh-Hant,en,ja}, --language {auto,zh,zh-Hant,en,ja}
                        界面语言（{auto|zh|zh-Hant|en|ja}）

示例：AutoExtract.exe -y
```
**示例：全自动解压清理**  
```cmd
AutoExtract.exe -y -t -e
```

---

## 📁 `delete_list.txt` 示例

首次运行可生成模板：
```cmd
AutoExtract.exe -g
```

内容示例：
```txt
// delete_list.txt
// 每行一个文件名；// 表示注释
// 编辑此文件以添加或移除要清理的文件
// 示例：
// malware.exe
// temp.tmp
// .DS_Store
// Thumbs.db
// desktop.ini
test.file
```

---

## 📦 打包说明（供开发者参考）

使用 Nuitka 编译命令示例（Windows）：
```bat
nuitka --standalone --onefile ^
       --include-data-file=7z.exe=7z.exe ^
       --include-data-file=7z.dll=7z.dll ^
       AutoExtract.py
```

> 实际发布版建议将 `7z.exe` 和 `7z.dll` 内嵌或与主程序同目录分发。

---

## ❤️ 致谢

- [Nuitka](https://nuitka.net/) — 将 Python 编译为高效本地代码  
- [7-Zip](https://www.7-zip.org/) — 开源压缩引擎  
- [filetype](https://github.com/h2non/filetype.py) — 文件类型检测库

---

**MIT License** — 自由使用、修改、分发。

---

# CikeZZZ AutoExtract

A fully standalone intelligent archive extractor compiled with Nuitka — no Python required.

---

## ✨ Key Advantages

- ✅ **Truly standalone**: Single executable (`.exe` on Windows, binary on Linux/macOS) — **no Python or dependencies needed**
- 📦 **Bundled 7-Zip engine**: Includes `7z.exe` (Windows) or uses system-installed 7z — no extra setup
- 🔍 **Smart format detection**: Automatically renames files with missing or incorrect extensions to correct archive formats
- 🛡️ **Multi-layer safety**:
  - Anti zip bomb
  - Max unpacked size (50 GB default)
  - Max file count (10,000 default)
  - Disk space validation before extraction
- 🖱️ **One-click context menu** (Windows): Extract entire folders directly from right-click
- 🌐 **Four-language interface**: Simplified Chinese / Traditional Chinese / English / Japanese — auto-detects system language or can be manually set
- 🧹 **Custom cleanup**: Delete junk files via `delete_list.txt` (e.g., `@eaDir`, `Thumbs.db`)

---

## 🚀 Quick Start

### Windows Users
1. Download `AutoExtract.exe` and `7z.exe` (if not bundled)
2. Place both files in any directory (e.g., `D:\Tools\`)
3. Double-click to run, or use command line:

```cmd
:: Extract all archives in current folder without prompts
AutoExtract.exe -y

:: Extract and delete junk files + empty folders
AutoExtract.exe -y -t -e

:: Add to Windows right-click menu (requires admin)
AutoExtract.exe --add-context-menu
```

> 💡 **Note**: The Nuitka-compiled version includes all Python dependencies like `filetype` — **no `pip install` required**!

---

## ⚙️ Common Commands

```
optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -y, --yes             Auto-answer yes to all prompts
  -n, --no              Auto-answer no to all prompts
  -t, --delete-target-files
                        Delete specified junk files
  -e, --delete-empty-folders
                        Delete empty directories
  -l [DELETE_LIST [DELETE_LIST ...]], --delete-list [DELETE_LIST [DELETE_LIST ...]]
                        Filenames to delete (space-separated)
  -f DELETE_LIST_FILE, --delete-list-file DELETE_LIST_FILE
                        Read delete list from file
  -g, --generate-delete-list-file
                        Generate delete_list.txt
  --add-context-menu    Add this program to Windows right-click context menu (on folders and background)
  --remove-context-menu
                        Remove this program from Windows right-click context menu
  --max-unpacked-gb MAX_UNPACKED_GB
                        Maximum allowed unpacked size in GB (default: 50)
  --max-files MAX_FILES
                        Maximum allowed number of files (default: 10000)
  -L {auto,zh,zh-Hant,en,ja}, --language {auto,zh,zh-Hant,en,ja}
                        Interface language (auto|zh|zh-Hant|en|ja)

Example: AutoExtract.exe -y
```

**Example: Fully automated extraction and cleanup**  
```cmd
AutoExtract.exe -y -t -e
```

---

## 📁 Sample `delete_list.txt`

Generate the template on first run:
```cmd
AutoExtract.exe -g
```

Example content:
```txt
// delete_list.txt
// One filename per line; // means comment
// Edit this file to add or remove files to clean up
// Example:
// malware.exe
// temp.tmp
// .DS_Store
// Thumbs.db
// desktop.ini
test.file
```

---

## 📦 Build Info (for Developers)

Nuitka compilation command example (Windows):
```bat
nuitka --standalone --onefile ^
       --include-data-file=7z.exe=7z.exe ^
       --include-data-file=7z.dll=7z.dll ^
       AutoExtract.py
```

> For public releases, it’s recommended to bundle `7z.exe` and `7z.dll` alongside the main executable.

---

## ❤️ Acknowledgements

- [Nuitka](https://nuitka.net/) — Compiles Python into efficient native code  
- [7-Zip](https://www.7-zip.org/) — Open-source compression engine  
- [filetype](https://github.com/h2non/filetype.py) — File type detection library

---

**MIT License** — Free to use, modify, and distribute.
