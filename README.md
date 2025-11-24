# AutoExtract

> **一款由 Nuitka 打包的全独立智能解压与清理工具 —— 无需 Python，开箱即用。**  
> **A fully standalone intelligent archive extractor compiled with Nuitka — no Python required.**

---

## ✨ 核心优势 / Key Advantages

| 中文 | English |
|------|--------|
| ✅ **真正独立可执行**：单文件 `.exe`| ✅ **Truly standalone**: Single `.exe` |
| 📦 **内置 7-Zip**：内置 `7z.exe`和 `7z.dll` | 📦 **Bundled 7-Zip**: Built-in '7z.exe' and '7z.dll' |
| 🔍 **智能格式识别**：自动将无扩展名或错误扩展名的文件重命名为正确压缩格式（如 `.zip`, `.7z`, `.rar`） | 🔍 **Smart format detection**: Fixes missing/wrong extensions (e.g., `.zip`, `.7z`, `.rar`) |
| 🛡️ **多重安全保障**：<br>• 防压缩炸弹（Zip Bomb）<br>• 默认最大解压体积 50 GB<br>• 默认最大文件数 10,000<br>• 解压前检查磁盘剩余空间 | 🛡️ **Multi-layer safety**:<br>• Anti zip bomb<br>• Max unpacked size: 50 GB (default)<br>• Max file count: 10,000 (default)<br>• Disk space validation before extraction |
| 🖱️ **集成右键菜单**（Windows）：支持文件夹和桌面背景右键，一键解压整个目录 | 🖱️ **Context menu integration** (Windows): Right-click on folders or desktop background to extract entire directories |
| 🌐 **四语界面**：简体中文 / 繁体中文 / English / 日本語，自动匹配系统语言，也可通过 `-L` 手动指定 | 🌐 **4-language UI**: Simplified Chinese / Traditional Chinese / English / Japanese — auto-detects system language or set manually with `-L` |
| 🧹 **自定义清理规则**：通过 `delete_list.txt` 或自定义文件删除指定文件（如 `@eaDir`, `Thumbs.db`, `.DS_Store`） | 🧹 **Custom Cleanup Rules**: Delete specified files (such as `@eaDir`, `Thumbs.db`, `.DS_Store`) by using `delete_list.txt` or a custom file. |

---

## 🚀 快速开始 / Quick Start

### Windows
1. 下载 `AutoExtract.exe`  
   Download `AutoExtract.exe`
2. 将 `AutoExtract.exe` 放入目标文件夹，双击运行；或将其所在目录添加到系统环境变量后，在任意位置通过命令行调用。你也可以在目标文件夹中按住 Shift + 右键，选择 “在此处打开终端”（或“在此处打开 PowerShell”），然后执行命令：  
   Place `AutoExtract.exe` in your target folder and double-click to run it;alternatively, add its directory to your system’s PATH and run it from any location via the command line.You can also hold Shift + right-click inside the target folder, select “Open terminal here” (or “Open PowerShell here”), and run the command:

```cmd
:: 自动解压当前目录所有压缩包（无需确认）
:: Automatically extract all compressed packages in the current directory (no confirmation required)
AutoExtract.exe -y

:: 添加右键菜单（需管理员权限）
:: Add a right-click menu (Administrator privileges required)
AutoExtract.exe --add-context-menu
```

> 💡 **提示**：Release 版本已包含 `filetype` 等所有 Python 依赖，**无需 `pip install`**！
> 💡 **Note**: The Release version already includes all Python dependencies such as' filetype ', ** No need for 'pip install' **!
> 💡 **提示**：右键解压的时候，相当于`-y`，即是，全部确认  
> 💡 **Note**: When right-clicking to extract the file, it is equivalent to `-y`, which means to confirm all operations.

---

## ⚙️ 常用命令 / Common Commands

```text
optional arguments:
  -h, --help            显示帮助信息并退出
                        Show this help message and exit
  -v, --version         显示程序版本
                        Show program's version number and exit
  -y, --yes             自动回答所有提示为“是”
                        Auto-answer yes to all prompts
  -n, --no              自动回答所有提示为“否”
                        Auto-answer no to all prompts
  -t, --delete-target-files
                        删除匹配 delete_list.txt 的文件
                        Delete files matching delete_list.txt
  -e, --delete-empty-folders
                        删除空文件夹
                        Delete empty directories
  -l ..., --delete-list ...
                        手动指定要删除的文件名（空格分隔）
                        Specify filenames to delete (space-separated)
  -f FILE, --delete-list-file FILE
                        从指定文件加载删除列表
                        Load delete list from file
  -g, --generate-delete-list-file
                        生成 delete_list.txt 模板
                        Generate delete_list.txt template
  --add-context-menu    添加到 Windows 右键菜单（文件夹 & 背景）
                        Add to Windows context menu (folders & background)
  --remove-context-menu 移除右键菜单项
                        Remove from Windows context menu
  --max-unpacked-gb N   最大解压体积（GB，默认 50）
                        Max unpacked size in GB (default: 50)
  --max-files N         最大文件数量（默认 10000）
                        Max number of files (default: 10000)
  -L {auto,zh,zh-Hant,en,ja}
                        界面语言（auto|zh|zh-Hant|en|ja）
                        Interface language (auto|zh|zh-Hant|en|ja)
```

**全自动解压 + 清理示例 / Full automation example:**  
```cmd
AutoExtract.exe -y
```

---

## 📁 `delete_list.txt` 示例 / Sample `delete_list.txt`

生成模板：
```cmd
AutoExtract.exe -g
```

文件内容示例：
```txt
// delete_list.txt
// 每行一个文件名；// 表示注释
// One filename per line; // means comment
// 示例 / Example:
Thumbs.db
.DS_Store
@eaDir
.SynologyWorkingDirectory
```

> 程序会自动查找当前目录下的 `delete_list.txt`，无需额外指定。  
> The program automatically loads `delete_list.txt` from the current directory.

---

## 📦 打包说明（开发者） / Build Info (for Developers)

Windows 编译命令（Nuitka）：
```bat
nuitka --standalone --onefile ^
       --include-data-file=7z.exe=7z.exe ^
       --include-data-file=7z.dll=7z.dll ^
       AutoExtract.py
```

> 发布时建议将 `7z.exe` 和 `7z.dll` 与主程序放在同一目录，确保开箱即用。  
> For distribution, bundle `7z.exe` and `7z.dll` with the executable for zero-setup experience.

---

## ❤️ 致谢 / Acknowledgements

- [Nuitka](https://nuitka.net/) — 将 Python 编译为高效本地代码  
  Compiles Python into efficient native code  
- [7-Zip](https://www.7-zip.org/) — 开源压缩/解压引擎  
  Open-source compression/decompression engine  
- [filetype](https://github.com/h2non/filetype.py) — 高精度文件类型检测库  
  High-accuracy file type detection library

---
## 💬 作者说

> 欢迎提出各种问题!  
> Questions? Suggestions?  
> 一起进步！  
> Let’s learn and improve together!  
> 程序运行时有彩蛋！😆  
> There are Easter eggs when the program is running! 😆

## 📜 许可证 / License

**MIT License** — 自由使用、修改、分发。  
**MIT License** — Free to use, modify, and distribute.

---
