# Windows 测试指南

## 前提条件

### 1. 安装 MSYS2
下载并安装 MSYS2：https://www.msys2.org/

安装完成后，打开 **MSYS2 UCRT64** 终端（重要：必须是 UCRT64，不是 MINGW64）。

### 2. 安装依赖

在 MSYS2 UCRT64 终端中运行：

```bash
# 更新包数据库
pacman -Syu

# 安装必需的依赖
pacman -S --noconfirm --needed \
    mingw-w64-ucrt-x86_64-python \
    mingw-w64-ucrt-x86_64-gtk4 \
    mingw-w64-ucrt-x86_64-libadwaita \
    mingw-w64-ucrt-x86_64-python-pillow \
    mingw-w64-ucrt-x86_64-python-gobject \
    mingw-w64-ucrt-x86_64-python-pip \
    unzip \
    wget

# 安装 Python 依赖
pip install aria2p requests pyjwt
```

### 3. 下载 aria2c 和 ffmpeg

在项目根目录运行：

```bash
cd /d/code/varia-next

# 下载 aria2
wget "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"
unzip -d aria2 aria2-1.37.0-win-64bit-build1.zip

# 下载 ffmpeg
wget "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.0-latest-win64-lgpl-shared-8.0.zip"
unzip -d ffmpeg ffmpeg-n8.0-latest-win64-lgpl-shared-8.0.zip

# 复制到 src 目录
cp aria2/aria2-1.37.0-win-64bit-build1/aria2c.exe src/
cp ffmpeg/ffmpeg-n8.0-latest-win64-lgpl-shared-8.0/bin/ffmpeg.exe src/
cp ffmpeg/ffmpeg-n8.0-latest-win64-lgpl-shared-8.0/bin/*.dll src/
```

## 快速测试（开发模式）

### 方法 1：直接运行（推荐用于快速测试验证功能）

1. **准备语言文件（如果需要）**
```bash
cd /d/code/varia-next

# 生成 locale 文件
rm -rf locale
mkdir -p locale
for po in po/*.po; do
    lang=$(basename "$po" .po)
    mkdir -p "locale/$lang/LC_MESSAGES"
    msgfmt -o "locale/$lang/LC_MESSAGES/varia.mo" "$po"
done
```

2. **创建测试启动脚本**

创建 `test_run.sh`：
```bash
#!/bin/bash
cd "$(dirname "$0")/src"

# 确保 aria2c 和 ffmpeg 在当前目录
if [ ! -f "aria2c.exe" ]; then
    echo "错误: 未找到 aria2c.exe，请先下载并复制到 src 目录"
    exit 1
fi

if [ ! -f "ffmpeg.exe" ]; then
    echo "错误: 未找到 ffmpeg.exe，请先下载并复制到 src 目录"
    exit 1
fi

# 运行应用
python variamain.py
```

3. **运行测试**
```bash
chmod +x test_run.sh
./test_run.sh
```

### 方法 2：使用 Python 直接运行

在 MSYS2 UCRT64 终端中：

```bash
cd /d/code/varia-next/src
python variamain.py
```

**注意**：确保 `aria2c.exe` 和 `ffmpeg.exe` 在 `src` 目录下。

## 测试验证功能

### 测试未登录流程

1. **删除认证 token**
```bash
rm -f ~/.config/varia/auth.json
```

2. **启动应用**
```bash
cd /d/code/varia-next/src
python variamain.py
```

3. **预期结果**
   - 应用启动后，主窗口显示 **嵌入式验证视图**（不是弹窗）
   - 可以看到 QQ 号输入框和验证说明
   - **aria2 进程不应该启动**（重要！）

4. **完成验证**
   - 输入 QQ 号
   - 点击"获取验证码"
   - 复制验证码到 QQ 群或私聊机器人
   - 点击"我已发送验证码"
   - 验证成功后，界面应该平滑切换到主界面
   - **此时 aria2 才会启动**

### 测试已登录流程

1. **确保 token 存在**
```bash
# 如果已经完成过验证，token 应该在这里
cat ~/.config/varia/auth.json
```

2. **启动应用**
```bash
cd /d/code/varia-next/src
python variamain.py
```

3. **预期结果**
   - 应用直接显示主界面（跳过验证视图）
   - aria2 自动启动
   - 可以正常使用所有下载功能

## 完整构建测试

如果需要测试打包后的应用：

```bash
cd /d/code/varia-next
bash build-for-windows.sh
```

构建完成后，可执行文件在：
```
src/dist/variamain/variamain.exe
```

## 常见问题

### 1. 找不到 GTK 库
确保使用 **MSYS2 UCRT64** 终端，不是 MINGW64 或 MSYS。

### 2. aria2c 启动失败
检查 `aria2c.exe` 是否在正确位置：
```bash
ls -la src/aria2c.exe
```

### 3. 验证界面未显示
检查日志输出，确认：
```bash
# 检查认证状态
cat ~/.config/varia/auth.json

# 如果想强制显示验证界面
rm ~/.config/varia/auth.json
```

### 4. 窗口显示异常
确保已安装 libadwaita：
```bash
pacman -S mingw-w64-ucrt-x86_64-libadwaita
```

## 调试技巧

### 查看详细日志

在 MSYS2 终端运行时，所有 Python 的 `print()` 输出都会显示在终端中。

### 检查 aria2 进程

在另一个终端中：
```bash
# 检查 aria2c 是否在运行
ps aux | grep aria2c

# 或者在 Windows CMD/PowerShell 中
tasklist | findstr aria2c
```

### 检查 RPC 连接

```bash
# 测试 aria2 RPC 是否可访问
curl http://localhost:6801/jsonrpc
```

## 测试清单

- [ ] 未登录状态启动，显示验证视图
- [ ] 验证视图嵌入在主窗口（不是独立弹窗）
- [ ] 未验证前 aria2 未启动
- [ ] 输入 QQ 号并获取验证码
- [ ] 复制验证码功能正常
- [ ] 完成验证后自动切换到主界面
- [ ] 验证后 aria2 成功启动
- [ ] 已登录状态重启，直接显示主界面
- [ ] 下载功能正常工作
- [ ] 关闭软件后 aria2c.exe 正确终止

## 技术支持

如果遇到问题，请提供以下信息：
1. 错误日志（终端输出）
2. `~/.config/varia/auth.json` 内容（如果存在）
3. 使用的 MSYS2 版本和终端类型
4. Python 版本：`python --version`
5. GTK4 版本：`pacman -Q mingw-w64-ucrt-x86_64-gtk4`
