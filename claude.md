# Varia Next - 项目状态文档

## 项目概述
Varia 是一个基于 Python + GTK4/Libadwaita 的下载管理器，使用 aria2c 作为下载引擎。

## 最近重构（2025年）

### 已移除的功能
1. **种子下载功能**
   - 移除了所有 BitTorrent/磁力链接相关代码
   - 删除了 aria2 BT 配置参数
   - 移除了种子文件拖放处理
   - 删除了"做种中"过滤按钮

2. **视频/音频下载功能**
   - 完全删除 `src/download/videos.py` (429行)
   - 移除 yt-dlp 集成
   - 删除视频下载按钮和相关UI
   - 移除 cookies.txt 配置功能

3. **浏览器扩展**
   - 完全删除 `browser-extension/` 目录
   - 移除 Firefox 和 Chrome 扩展
   - 删除首选项中的扩展按钮

### 保留的核心功能
- ✅ URL 直接下载（HTTP/HTTPS/FTP）
- ✅ 多线程下载
- ✅ 暂停/恢复功能
- ✅ 速度限制
- ✅ 远程 aria2 模式
- ✅ 计划任务下载
- ✅ 下载历史记录
- ✅ 同时下载数量限制
- ✅ 关机/退出模式

## 关键文件说明

### 核心文件
- `src/variamain.py` - 主窗口类，处理应用程序主逻辑
- `src/window/sidebar.py` - 侧边栏UI，包含下载输入框
- `src/window/preferences.py` - 首选项窗口（已简化为605行）
- `src/download/thread.py` - 下载线程管理（仅保留 regular 模式）
- `src/download/listen.py` - aria2 监听和状态管理
- `src/download/actionrow.py` - 下载项UI行
- `src/download/details.py` - 下载详情窗口（已简化为143行）

### 构建配置
- `.github/workflows/flatpak-package.yml` - Flatpak 构建（仅手动触发）
- `.github/workflows/windows-package.yml` - Windows 构建（仅手动触发）
- `io.github.giantpinkrobots.varia.json` - Flatpak manifest
- `actions-inno-install-script.iss` - Windows 安装程序脚本

## 已修复的Bug

### Bug #1: 首选项中浏览器扩展仍然显示
**问题**: 删除浏览器扩展后，首选项窗口仍显示扩展相关UI
**修复**: 从 `preferences.py` 删除浏览器扩展 ActionRow (第57-78行) 和 `on_extension_selected()` 函数

### Bug #2: 点击过滤按钮导致崩溃
**问题**: 点击"进行中"或"已完成"过滤按钮时应用闪退
**原因**: 代码引用了已删除的 `filter_button_show_seeding` 和 `video_status` 变量
**修复**:
- 从 `variamain.py:filter_download_list()` 移除 `self.filter_button_show_seeding.set_active(False)`
- 移除所有 `download.seeder` 检查
- 移除 "show_seeding" 过滤模式
- 移除 `video_status` 状态检查
- 简化过滤逻辑，仅处理 "regular" 模式下载

## 代码统计
- **删除总行数**: ~1200+ 行
- **删除文件**: 2个（videos.py + browser-extension/）
- **修改文件**: 10+ 个核心Python文件

## Git 仓库信息
- **远程仓库**: https://github.com/onlylss/baidu
- **默认分支**: main
- **最新提交**: 将GitHub Actions工作流改为仅手动触发 (354c522)

## GitHub Actions 工作流
两个工作流均已改为**仅手动触发** (`workflow_dispatch`)：
1. **Flatpak 构建** - 使用 GNOME 49 容器
2. **Windows 构建** - 使用 MSYS2 UCRT64，生成安装包和便携版

手动触发方式：
1. 访问 GitHub Actions 页面
2. 选择对应工作流
3. 点击 "Run workflow" 按钮

## 技术栈
- **语言**: Python 3
- **UI框架**: GTK 4 + Libadwaita
- **下载引擎**: aria2c (通过 aria2p 库)
- **构建系统**: Flatpak (Linux), Inno Setup (Windows)
- **依赖管理**: 使用 Flatpak modules / MSYS2 packages

## 重要配置项
```python
# aria2 配置 (variamain.py)
aria2_config = [
    "--enable-rpc",
    "--rpc-listen-port=6801",
    "--allow-overwrite=false",
    "--auto-file-renaming=true",
    "--min-split-size=1M",
    "--http-accept-gzip=true",
    "--disk-cache=128M",
    "--split=32",
    "--max-connection-per-server=16"
]
```

## 注意事项
1. 所有 Python 代码语法已验证，无语法错误
2. 远程模式下不再有视频下载功能限制提示
3. 过滤功能仅支持：全部、进行中、已完成、失败
4. 所有下载模式统一为 "regular" 模式

## 待办事项
- [ ] 测试 Flatpak 构建流程
- [ ] 测试 Windows 安装包生成
- [ ] 更新用户文档（如果存在）
- [ ] 考虑是否需要更新应用截图和说明

## 联系信息
- **GitHub**: https://github.com/onlylss/baidu
- **原始项目**: varia (由 giantpinkrobots 开发)

---
*最后更新: 2025-11-05*
*文档创建: 自动生成，用于 AI 上下文*
