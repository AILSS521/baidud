# Varia Next - 项目文档

## 项目概述
Varia 是一个基于 Python + GTK4/Libadwaita 的现代下载管理器，使用 aria2c 作为下载引擎。

## 核心功能
- ✅ URL 直接下载（HTTP/HTTPS/FTP）
- ✅ 多线程并发下载
- ✅ 暂停/恢复功能
- ✅ 速度限制控制
- ✅ 远程 aria2 模式
- ✅ 计划任务下载
- ✅ 下载历史记录
- ✅ 同时下载数量限制
- ✅ 关机/退出模式

## 关键文件说明

### 核心文件
- `src/variamain.py` - 主窗口类，应用程序主逻辑和 aria2c 进程管理
- `src/window/sidebar.py` - 侧边栏UI，包含下载输入框
- `src/window/preferences.py` - 首选项窗口
- `src/download/thread.py` - 下载线程管理
- `src/download/listen.py` - aria2 RPC 监听和状态管理
- `src/download/actionrow.py` - 下载项UI行
- `src/download/details.py` - 下载详情窗口

### 构建配置
- `.github/workflows/flatpak-package.yml` - Flatpak 构建工作流（手动触发）
- `.github/workflows/windows-package.yml` - Windows 构建工作流（手动触发）
- `io.github.giantpinkrobots.varia.json` - Flatpak manifest
- `actions-inno-install-script.iss` - Windows 安装程序脚本

## 技术栈
- **语言**: Python 3
- **UI框架**: GTK 4 + Libadwaita
- **下载引擎**: aria2c (通过 aria2p 库)
- **构建系统**: Flatpak (Linux), Inno Setup (Windows)
- **依赖管理**: Flatpak modules / MSYS2 packages

## aria2 配置参数
```python
# 默认 aria2c 配置
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

## GitHub Actions 构建
两个工作流均支持手动触发 (`workflow_dispatch`)：
- **Flatpak 构建** - 使用 GNOME 49 容器
- **Windows 构建** - 使用 MSYS2 UCRT64，生成安装包和便携版

## 仓库信息
- **GitHub**: https://github.com/onlylss/baidu
- **默认分支**: main
- **原始项目**: varia (由 giantpinkrobots 开发)

---
*文档用于 AI 上下文*
