# 百度网盘下载器集成方案

## 项目概述

将 varia-next 下载管理器改造为百度网盘专用下载客户端，通过新建网页端 API（duapi.linglong521.cn）实现用户认证、文件列表获取和下载链接解析。

## 架构设计

```
┌─────────────────┐      HTTPS/JSON      ┌──────────────────┐
│  varia-next     │ ◄──────────────────► │  duapi.linglong  │
│  (GTK客户端)    │                      │  (PHP API服务器) │
└─────────────────┘                      └──────────────────┘
        │                                        │
        │ aria2c                                 │
        │ RPC                                    │
        ▼                                        ▼
┌─────────────────┐                      ┌──────────────────┐
│  aria2c         │                      │  Redis + 百度API │
│  (下载引擎)     │                      │  + 解析服务      │
└─────────────────┘                      └──────────────────┘
```

## 一、网页端 API 开发 (duapi.linglong521.cn)

### 1.1 技术栈

- **语言**: PHP 7.4+
- **数据库**: Redis (多DB支持)
- **依赖**: Composer + firebase/php-jwt
- **部署**: LAMP/LNMP + SSL证书

### 1.2 目录结构

```
duapi.linglong521.cn/
├── api/
│   ├── auth/
│   │   ├── generate-code.php      # 生成验证码
│   │   ├── check-status.php       # 检查验证状态
│   │   └── validate-token.php     # 验证Token有效性
│   ├── baidu/
│   │   ├── file-list.php          # 获取文件列表
│   │   └── download-links.php     # 获取下载链接
│   ├── config.php                 # 配置文件
│   └── common.php                 # 公共函数(JWT、响应等)
├── composer.json
└── .htaccess
```

### 1.3 API 端点规范

#### 1.3.1 POST /api/auth/generate-code

生成QQ验证码

**请求体**:
```json
{
  "qq": "12345678",
  "device_id": "device_abc123_1699999999"
}
```

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "verify_code": "1234567"
  }
}
```

**错误响应**:
- 400: QQ号格式不正确
- 403: 用户无有效捐赠
- 451: 用户已被封禁

**Redis 存储**:
- DB2: `verify:{qq}:{device_id}` → `{"code": "xxx", "ip": "xxx", "time": timestamp}`

---

#### 1.3.2 GET /api/auth/check-status

检查验证状态并获取Token

**请求参数**:
- `qq`: QQ号
- `code`: 验证码
- `device_id`: 设备ID

**成功响应** (200):
```json
{
  "code": 200,
  "message": "验证成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 432000
  }
}
```

**等待验证** (202):
```json
{
  "code": 202,
  "message": "等待验证"
}
```

**Token 内容**:
```json
{
  "qq": "12345678",
  "device_id": "device_xxx",
  "ip": "1.2.3.4",
  "city": "杭州",
  "province": "浙江",
  "exp": 1699999999
}
```

---

#### 1.3.3 POST /api/baidu/file-list

获取百度网盘分享文件列表

**请求头**:
```
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "surl": "1abcdefg",
  "dir": "/",
  "pwd": "1234"
}
```

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "uk": "123456789",
    "shareid": "987654321",
    "randsk": "random_key_string",
    "list": [
      {
        "fs_id": 123456,
        "server_filename": "文件夹A",
        "isdir": 1,
        "path": "/文件夹A"
      },
      {
        "fs_id": 789012,
        "server_filename": "文件.zip",
        "isdir": 0,
        "size": 1024000
      }
    ]
  }
}
```

**错误响应**:
- 401: Token无效或过期
- 404: 文件不存在
- 403: 提取码错误

---

#### 1.3.4 POST /api/baidu/download-links

获取文件下载链接

**请求头**:
```
Authorization: Bearer {token}
```

**请求体**:
```json
{
  "randsk": "random_key_string",
  "uk": "123456789",
  "shareid": "987654321",
  "fs_ids": [789012, 345678],
  "surl": "1abcdefg",
  "dir": "/",
  "pwd": "1234"
}
```

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "filename": "文件.zip",
      "fs_id": 789012,
      "url": "https://d.pcs.baidu.com/file/xxx",
      "urls": [
        "https://d.pcs.baidu.com/file/xxx",
        "https://d2.pcs.baidu.com/file/xxx"
      ],
      "ua": "Mozilla/5.0..."
    }
  ]
}
```

**限制**:
- 单次最多10个文件
- 并发请求上限5个

---

### 1.4 认证机制

#### JWT Token 生成
```php
// composer require firebase/php-jwt
use Firebase\JWT\JWT;

$payload = [
    'qq' => $qq,
    'device_id' => $device_id,
    'ip' => $ip,
    'city' => $city,
    'province' => $province,
    'exp' => time() + 432000 // 5天
];

$token = JWT::encode($payload, SECRET_KEY, 'HS256');
```

#### Token 验证
```php
try {
    $decoded = JWT::decode($token, new Key(SECRET_KEY, 'HS256'));

    // 验证IP和地理位置
    $current_location = get_location(get_real_ip());
    if ($decoded->province !== $current_location['province']) {
        throw new Exception('地理位置异常');
    }
} catch (Exception $e) {
    return errorResponse('Token无效', 401);
}
```

---

## 二、varia-next 客户端开发

### 2.1 新增依赖

在 `io.github.giantpinkrobots.varia.json` 中添加:

```json
{
  "name": "python3-requests",
  "buildsystem": "simple",
  "build-commands": ["pip3 install --prefix=/app requests"]
},
{
  "name": "python3-pyjwt",
  "buildsystem": "simple",
  "build-commands": ["pip3 install --prefix=/app pyjwt"]
}
```

### 2.2 目录结构

```
src/
├── auth/
│   ├── __init__.py
│   ├── manager.py           # 认证管理器
│   └── storage.py           # Token存储
├── api/
│   ├── __init__.py
│   └── client.py            # API客户端
├── window/
│   ├── login.py             # 登录窗口 (新建)
│   ├── filebrowser.py       # 文件浏览器 (新建)
│   ├── sharelinks.py        # 分享链接管理 (新建)
│   ├── sidebar.py           # 侧边栏 (修改)
│   └── preferences.py       # 首选项 (保持)
├── download/
│   ├── thread.py            # 下载线程 (修改)
│   └── ...
└── variamain.py             # 主窗口 (修改)
```

### 2.3 核心模块实现

#### 2.3.1 认证管理器 (src/auth/manager.py)

```python
import requests
import jwt
import json
from pathlib import Path

class AuthManager:
    def __init__(self):
        self.api_base = "https://duapi.linglong521.cn/api"
        self.token = None
        self.device_id = self._get_or_create_device_id()
        self._load_token()

    def _get_or_create_device_id(self):
        """生成或获取设备ID"""
        config_dir = Path.home() / ".config" / "varia"
        config_dir.mkdir(parents=True, exist_ok=True)
        device_file = config_dir / "device_id"

        if device_file.exists():
            return device_file.read_text().strip()

        import uuid
        device_id = f"device_{uuid.uuid4().hex[:16]}"
        device_file.write_text(device_id)
        return device_id

    def generate_code(self, qq):
        """生成验证码"""
        response = requests.post(
            f"{self.api_base}/auth/generate-code.php",
            json={"qq": qq, "device_id": self.device_id},
            timeout=10
        )
        return response.json()

    def check_status(self, qq, code):
        """检查验证状态"""
        response = requests.get(
            f"{self.api_base}/auth/check-status.php",
            params={"qq": qq, "code": code, "device_id": self.device_id},
            timeout=10
        )
        data = response.json()
        if data.get('code') == 200:
            self.token = data['data']['token']
            self._save_token()
        return data

    def _save_token(self):
        """保存Token到本地"""
        config_file = Path.home() / ".config" / "varia" / "auth.json"
        config_file.write_text(json.dumps({"token": self.token}))

    def _load_token(self):
        """从本地加载Token"""
        config_file = Path.home() / ".config" / "varia" / "auth.json"
        if config_file.exists():
            data = json.loads(config_file.read_text())
            self.token = data.get('token')

    def is_authenticated(self):
        """检查是否已认证"""
        if not self.token:
            return False
        try:
            # 解码JWT不验证签名，只检查过期时间
            payload = jwt.decode(self.token, options={"verify_signature": False})
            import time
            return payload['exp'] > time.time()
        except:
            return False

    def logout(self):
        """注销"""
        self.token = None
        config_file = Path.home() / ".config" / "varia" / "auth.json"
        if config_file.exists():
            config_file.unlink()
```

#### 2.3.2 API 客户端 (src/api/client.py)

```python
import requests

class BaiduAPIClient:
    def __init__(self, auth_manager):
        self.auth = auth_manager
        self.api_base = "https://duapi.linglong521.cn/api"

    def _get_headers(self):
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.auth.token}",
            "Content-Type": "application/json"
        }

    def get_file_list(self, surl, dir="/", pwd=""):
        """获取文件列表"""
        response = requests.post(
            f"{self.api_base}/baidu/file-list.php",
            headers=self._get_headers(),
            json={"surl": surl, "dir": dir, "pwd": pwd},
            timeout=30
        )
        return response.json()

    def get_download_links(self, randsk, uk, shareid, fs_ids, surl, dir="/", pwd=""):
        """获取下载链接"""
        response = requests.post(
            f"{self.api_base}/baidu/download-links.php",
            headers=self._get_headers(),
            json={
                "randsk": randsk,
                "uk": uk,
                "shareid": shareid,
                "fs_ids": fs_ids,
                "surl": surl,
                "dir": dir,
                "pwd": pwd,
                "url": f"https://pan.baidu.com/s/{surl}"
            },
            timeout=60
        )
        return response.json()
```

#### 2.3.3 登录窗口 (src/window/login.py)

```python
from gi.repository import Gtk, Adw, GLib

class LoginWindow(Adw.Window):
    def __init__(self, parent, auth_manager, on_success):
        super().__init__()
        self.auth = auth_manager
        self.on_success = on_success
        self.verify_code = None
        self.qq = None

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(400, 500)
        self.set_title("百度网盘下载器 - 登录")

        # 构建UI
        self._build_ui()

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        # QQ号输入
        self.qq_entry = Adw.EntryRow()
        self.qq_entry.set_title("QQ号")
        box.append(self.qq_entry)

        # 生成验证码按钮
        gen_btn = Gtk.Button(label="获取验证码")
        gen_btn.connect("clicked", self.on_generate_code)
        box.append(gen_btn)

        # 验证码显示区域
        self.code_frame = Gtk.Frame()
        self.code_frame.set_visible(False)

        code_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        code_box.set_margin_top(12)
        code_box.set_margin_bottom(12)
        code_box.set_margin_start(12)
        code_box.set_margin_end(12)

        self.code_label = Gtk.Label()
        self.code_label.set_selectable(True)
        self.code_label.add_css_class("title-1")
        code_box.append(self.code_label)

        self.countdown_label = Gtk.Label(label="剩余时间: 120秒")
        code_box.append(self.countdown_label)

        copy_btn = Gtk.Button(label="复制验证码")
        copy_btn.connect("clicked", self.on_copy_code)
        code_box.append(copy_btn)

        verify_btn = Gtk.Button(label="我已发送验证码")
        verify_btn.add_css_class("suggested-action")
        verify_btn.connect("clicked", self.on_verify)
        code_box.append(verify_btn)

        self.code_frame.set_child(code_box)
        box.append(self.code_frame)

        # 说明文字
        instructions = Gtk.Label()
        instructions.set_markup(
            "<b>验证步骤：</b>\n"
            "1. 复制验证码（包含汉字）\n"
            "2. 在QQ群或私聊机器人发送验证码\n"
            "3. 发送后点击\"我已发送验证码\"按钮\n"
            "4. 验证成功后将自动跳转"
        )
        instructions.set_wrap(True)
        box.append(instructions)

        self.set_content(box)

    def on_generate_code(self, button):
        """生成验证码"""
        self.qq = self.qq_entry.get_text().strip()
        if not self.qq or len(self.qq) < 5:
            # 显示错误提示
            return

        button.set_sensitive(False)
        button.set_label("生成中...")

        def callback(result):
            button.set_sensitive(True)
            button.set_label("获取验证码")

            if result.get('code') == 200:
                self.verify_code = result['data']['verify_code']
                self.code_label.set_text(f"验证码{self.verify_code}")
                self.code_frame.set_visible(True)
                self.start_countdown(120)
            else:
                # 显示错误
                pass

        # 异步请求
        import threading
        def request():
            try:
                result = self.auth.generate_code(self.qq)
                GLib.idle_add(callback, result)
            except Exception as e:
                GLib.idle_add(callback, {'code': 500, 'message': str(e)})

        threading.Thread(target=request, daemon=True).start()

    def start_countdown(self, seconds):
        """开始倒计时"""
        self.remaining = seconds

        def tick():
            if self.remaining > 0:
                self.countdown_label.set_text(f"剩余时间: {self.remaining}秒")
                self.remaining -= 1
                return True  # 继续定时器
            else:
                self.close()
                return False  # 停止定时器

        GLib.timeout_add_seconds(1, tick)

    def on_copy_code(self, button):
        """复制验证码"""
        clipboard = self.get_clipboard()
        clipboard.set(f"验证码{self.verify_code}")
        button.set_label("已复制")
        GLib.timeout_add_seconds(2, lambda: button.set_label("复制验证码"))

    def on_verify(self, button):
        """验证"""
        button.set_sensitive(False)
        button.set_label("验证中...")

        def check_status(retry=0):
            if retry >= 5:  # 最多检查5次
                GLib.idle_add(lambda: button.set_label("验证失败，请重试"))
                return

            try:
                result = self.auth.check_status(self.qq, self.verify_code)
                if result.get('code') == 200:
                    GLib.idle_add(self.on_success)
                    GLib.idle_add(self.close)
                else:
                    # 1秒后重试
                    GLib.timeout_add_seconds(1, lambda: check_status(retry + 1))
            except:
                GLib.timeout_add_seconds(1, lambda: check_status(retry + 1))

        import threading
        threading.Thread(target=check_status, daemon=True).start()
```

#### 2.3.4 文件浏览器 (src/window/filebrowser.py)

```python
from gi.repository import Gtk, Adw, GLib, Gio

class FileBrowserWindow(Adw.Window):
    def __init__(self, parent, api_client, surl, pwd, on_download):
        super().__init__()
        self.api = api_client
        self.surl = surl
        self.pwd = pwd
        self.on_download = on_download

        self.current_dir = "/"
        self.uk = None
        self.shareid = None
        self.randsk = None

        self.set_transient_for(parent)
        self.set_default_size(800, 600)
        self.set_title("文件浏览")

        self._build_ui()
        self._load_file_list()

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # 面包屑导航
        self.breadcrumb = Gtk.Label()
        self.breadcrumb.set_halign(Gtk.Align.START)
        self.breadcrumb.add_css_class("title-4")
        box.append(self.breadcrumb)

        # 文件列表
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled.set_child(self.listbox)
        box.append(scrolled)

        # 下载按钮
        download_btn = Gtk.Button(label="下载选中文件")
        download_btn.add_css_class("suggested-action")
        download_btn.connect("clicked", self.on_download_clicked)
        box.append(download_btn)

        self.set_content(box)

    def _load_file_list(self):
        """加载文件列表"""
        def callback(result):
            if result.get('code') == 200:
                data = result['data']
                self.uk = data['uk']
                self.shareid = data['shareid']
                self.randsk = data['randsk']

                self.listbox.remove_all()
                for item in data['list']:
                    row = self._create_file_row(item)
                    self.listbox.append(row)

                self.breadcrumb.set_text(f"路径: {self.current_dir}")

        import threading
        def request():
            try:
                result = self.api.get_file_list(self.surl, self.current_dir, self.pwd)
                GLib.idle_add(callback, result)
            except Exception as e:
                print(f"Error: {e}")

        threading.Thread(target=request, daemon=True).start()

    def _create_file_row(self, item):
        """创建文件行"""
        row = Adw.ActionRow()

        icon_name = "folder" if item['isdir'] == 1 else "text-x-generic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        row.add_prefix(icon)

        row.set_title(item['server_filename'])
        if item['isdir'] == 0:
            size_mb = item.get('size', 0) / 1024 / 1024
            row.set_subtitle(f"{size_mb:.2f} MB")

        row.file_data = item

        if item['isdir'] == 1:
            row.set_activatable(True)
            row.connect("activated", self.on_folder_activated)

        return row

    def on_folder_activated(self, row):
        """进入文件夹"""
        self.current_dir = row.file_data['path']
        self._load_file_list()

    def on_download_clicked(self, button):
        """下载选中文件"""
        selected_rows = []
        for i in range(self.listbox.get_row_at_index(0), self.listbox.get_row_at_index(-1)):
            row = self.listbox.get_row_at_index(i)
            if row and row.is_selected() and row.file_data['isdir'] == 0:
                selected_rows.append(row)

        if not selected_rows:
            return

        fs_ids = [row.file_data['fs_id'] for row in selected_rows]

        # 获取下载链接
        def callback(result):
            if result.get('code') == 200:
                for file_info in result['data']:
                    self.on_download(file_info)

        import threading
        def request():
            try:
                result = self.api.get_download_links(
                    self.randsk, self.uk, self.shareid,
                    fs_ids, self.surl, self.current_dir, self.pwd
                )
                GLib.idle_add(callback, result)
            except Exception as e:
                print(f"Error: {e}")

        threading.Thread(target=request, daemon=True).start()
```

### 2.4 主窗口修改 (src/variamain.py)

```python
# 在 VariaMainWindow.__init__ 中添加
from auth.manager import AuthManager
from api.client import BaiduAPIClient
from window.login import LoginWindow
from window.filebrowser import FileBrowserWindow

class VariaMainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 初始化认证管理器
        self.auth = AuthManager()
        self.api = BaiduAPIClient(self.auth)

        # 检查登录状态
        if not self.auth.is_authenticated():
            self.show_login()
        else:
            self.show_main_ui()

    def show_login(self):
        """显示登录窗口"""
        login_window = LoginWindow(self, self.auth, self.show_main_ui)
        login_window.present()

    def show_main_ui(self):
        """显示主界面"""
        # 这里修改侧边栏，移除URL输入，添加"打开分享链接"按钮
        pass

    def open_share_link(self):
        """打开分享链接对话框"""
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("打开百度网盘分享链接")
        dialog.set_body("请输入分享链接和提取码")

        # 添加输入框
        # ...

        dialog.connect("response", self.on_share_link_response)
        dialog.present()

    def on_share_link_response(self, dialog, response):
        """处理分享链接输入"""
        if response == "open":
            surl = self.extract_surl(link)  # 从链接提取surl
            pwd = pwd_entry.get_text()

            # 打开文件浏览器
            browser = FileBrowserWindow(
                self, self.api, surl, pwd,
                self.add_download_task
            )
            browser.present()

    def add_download_task(self, file_info):
        """添加下载任务"""
        # 调用aria2c添加下载
        # 需要设置正确的User-Agent
        options = {
            'header': [f'User-Agent: {file_info["ua"]}'],
            'out': file_info['filename']
        }

        # 调用现有的aria2下载逻辑
        # self.aria2.add_uri([file_info['url']], options)
```

### 2.5 移除旧功能

需要删除/修改的文件：
- `src/window/sidebar.py` - 移除URL输入框和相关代码
- 清理所有与直接URL下载相关的引用

---

## 三、实施计划

### 阶段1：网页端API开发 (预计3-5天)

**第1天**:
- [ ] 搭建项目基础框架
- [ ] 配置 Composer 和依赖
- [ ] 实现 common.php (JWT、响应函数)
- [ ] 实现 config.php

**第2天**:
- [ ] 实现 /api/auth/generate-code.php
- [ ] 实现 /api/auth/check-status.php
- [ ] 实现 /api/auth/validate-token.php
- [ ] 本地测试认证流程

**第3天**:
- [ ] 实现 /api/baidu/file-list.php
- [ ] 实现 /api/baidu/download-links.php
- [ ] 集成现有百度API调用逻辑

**第4-5天**:
- [ ] 部署到 duapi.linglong521.cn
- [ ] 配置 SSL 证书
- [ ] 端到端测试
- [ ] 错误处理完善

### 阶段2：varia-next 客户端开发 (预计5-7天)

**第1天**:
- [ ] 添加依赖 (requests, pyjwt)
- [ ] 实现 AuthManager
- [ ] 实现 BaiduAPIClient

**第2-3天**:
- [ ] 实现 LoginWindow
- [ ] 测试登录流程
- [ ] 实现 Token 本地存储

**第4-5天**:
- [ ] 实现 FileBrowserWindow
- [ ] 实现文件列表展示
- [ ] 实现文件夹导航

**第6-7天**:
- [ ] 修改主窗口集成登录
- [ ] 修改下载逻辑支持百度网盘
- [ ] 移除旧的URL下载功能

### 阶段3：集成测试和优化 (预计2-3天)

- [ ] 完整流程端到端测试
- [ ] 错误处理和边界情况测试
- [ ] UI/UX 优化
- [ ] 性能测试（并发下载）
- [ ] 编写用户文档

---

## 四、关键决策点

需要用户确认的问题：

### 1. 分享链接管理方式
- **方案A**: 临时输入，不保存历史
- **方案B**: 保存最近打开的链接，支持快速切换
- **建议**: 方案B

### 2. 文件夹下载
- 是否支持递归下载整个文件夹？
- **建议**: 先实现单文件，后续添加文件夹递归

### 3. 下载路径
- 是否保留原有的下载路径配置？
- **建议**: 保留，继续使用首选项中的路径设置

### 4. URL下载功能
- 是否完全删除还是作为隐藏功能保留？
- **建议**: 完全删除代码和UI

---

## 五、风险评估

### 高风险
1. **QQ机器人可用性**: 整个认证依赖QQ机器人
   - 缓解：确保机器人稳定运行

2. **百度API变更**: 百度可能修改API或封禁
   - 缓解：做好错误提示，考虑多个解析源

### 中风险
3. **Token安全性**: 本地存储可能被窃取
   - 缓解：绑定IP和地理位置

4. **跨平台兼容性**: GTK4在Windows上表现
   - 缓解：优先Linux，Windows延后测试

### 低风险
5. **用户体验**: 新界面学习成本
   - 缓解：提供详细文档和提示

---

## 六、前置准备清单

开始开发前请确认：

- [ ] QQ机器人验证系统已部署并可用
- [ ] 有 duapi.linglong521.cn 域名的服务器访问权限
- [ ] 服务器已安装 PHP 7.4+, Redis, Composer
- [ ] Redis 已配置多DB支持 (DB0, DB2, DB4)
- [ ] 已有SSL证书或可申请Let's Encrypt
- [ ] varia-next 本地开发环境已就绪
- [ ] 已安装 GTK4, Python 3, pip

---

## 七、后续优化方向

完成基础功能后可考虑：

1. **多账号支持**: 支持多个QQ账号切换
2. **离线浏览**: 缓存文件列表供离线查看
3. **断点续传**: 更好的断点续传支持
4. **批量操作**: 批量添加分享链接
5. **自动解压**: 下载完成后自动解压
6. **速度优化**: CDN加速、分片下载优化

---

## 八、联系方式

如有问题，请联系开发团队或提交Issue到项目仓库。
