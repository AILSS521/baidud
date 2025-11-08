"""
百度网盘登录视图
提供可嵌入主窗口的QQ验证码登录界面
"""

import threading
from gi.repository import Gtk, Adw, GLib


class LoginView(Gtk.Box):
    """登录视图 - 可嵌入主窗口的验证组件"""

    def __init__(self, parent_window, auth_manager, on_success_callback):
        """
        初始化登录视图

        Args:
            parent_window: 父窗口（用于显示对话框）
            auth_manager: 认证管理器实例
            on_success_callback: 登录成功后的回调函数
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.parent_window = parent_window
        self.auth = auth_manager
        self.on_success = on_success_callback
        self.verify_code = None
        self.qq = None
        self.countdown_timeout_id = None
        self.check_status_timeout_id = None

        # 设置视图属性
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)

        # 构建UI
        self._build_ui()

    def _build_ui(self):
        """构建用户界面"""
        # 主容器 - 居中显示
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_size_request(450, -1)

        # 头部区域
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header_box.set_margin_top(48)
        header_box.set_margin_bottom(32)
        header_box.set_margin_start(24)
        header_box.set_margin_end(24)

        # 标题
        title_label = Gtk.Label(label="登录百度网盘下载器")
        title_label.add_css_class("title-1")
        header_box.append(title_label)

        # 副标题
        subtitle_label = Gtk.Label(label="使用QQ号验证码登录")
        subtitle_label.add_css_class("dim-label")
        header_box.append(subtitle_label)

        center_box.append(header_box)

        # 内容区域
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content_box.set_margin_bottom(24)

        # QQ号输入组
        self.qq_entry = Adw.EntryRow()
        self.qq_entry.set_title("QQ号")
        self.qq_entry.set_input_purpose(Gtk.InputPurpose.NUMBER)
        self.qq_entry.connect("activate", lambda _: self.on_generate_code_clicked(None))

        input_group = Adw.PreferencesGroup()
        input_group.add(self.qq_entry)
        content_box.append(input_group)

        # 生成验证码按钮
        self.gen_code_btn = Gtk.Button(label="获取验证码")
        self.gen_code_btn.add_css_class("suggested-action")
        self.gen_code_btn.add_css_class("pill")
        self.gen_code_btn.set_halign(Gtk.Align.CENTER)
        self.gen_code_btn.connect("clicked", self.on_generate_code_clicked)
        content_box.append(self.gen_code_btn)

        # 验证码显示区域（初始隐藏）
        self.code_revealer = Gtk.Revealer()
        self.code_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.code_revealer.set_transition_duration(300)

        code_content = self._create_code_display()
        self.code_revealer.set_child(code_content)
        content_box.append(self.code_revealer)

        # 说明文字
        instructions_label = Gtk.Label()
        instructions_label.set_markup(
            "<b>验证步骤：</b>\n\n"
            "1. 点击「获取验证码」按钮\n"
            "2. 复制生成的验证码（包含「验证码」三个字）\n"
            "3. 在QQ群或私聊机器人发送验证码\n"
            "4. 发送后点击「我已发送验证码」按钮\n"
            "5. 验证成功后将自动进入主界面"
        )
        instructions_label.set_wrap(True)
        instructions_label.set_justify(Gtk.Justification.LEFT)
        instructions_label.set_halign(Gtk.Align.START)
        instructions_label.add_css_class("dim-label")
        instructions_label.add_css_class("caption")

        instructions_frame = Gtk.Frame()
        instructions_frame.set_margin_top(12)

        instructions_box = Gtk.Box()
        instructions_box.set_margin_top(12)
        instructions_box.set_margin_bottom(12)
        instructions_box.set_margin_start(12)
        instructions_box.set_margin_end(12)
        instructions_box.append(instructions_label)
        instructions_frame.set_child(instructions_box)

        content_box.append(instructions_frame)

        center_box.append(content_box)

        # 添加到主视图
        self.append(center_box)

    def _create_code_display(self):
        """创建验证码显示区域"""
        code_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # 验证码卡片
        code_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        code_card.add_css_class("card")
        code_card.set_margin_top(6)
        code_card.set_margin_bottom(6)
        code_card.set_margin_start(6)
        code_card.set_margin_end(6)

        # 提示文字
        hint_label = Gtk.Label(label="请在QQ群或私聊机器人发送以下验证码：")
        hint_label.set_halign(Gtk.Align.START)
        hint_label.add_css_class("dim-label")
        code_card.append(hint_label)

        # 验证码标签
        self.code_label = Gtk.Label()
        self.code_label.set_selectable(True)
        self.code_label.add_css_class("title-1")
        self.code_label.add_css_class("monospace")
        self.code_label.set_halign(Gtk.Align.CENTER)
        self.code_label.set_margin_top(12)
        self.code_label.set_margin_bottom(12)
        code_card.append(self.code_label)

        # 倒计时标签
        self.countdown_label = Gtk.Label(label="剩余时间: 120秒")
        self.countdown_label.add_css_class("dim-label")
        self.countdown_label.add_css_class("caption")
        self.countdown_label.set_halign(Gtk.Align.CENTER)
        code_card.append(self.countdown_label)

        code_box.append(code_card)

        # 按钮组
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # 复制按钮
        self.copy_btn = Gtk.Button(label="复制验证码")
        self.copy_btn.add_css_class("pill")
        self.copy_btn.connect("clicked", self.on_copy_code_clicked)
        button_box.append(self.copy_btn)

        # 验证按钮
        self.verify_btn = Gtk.Button(label="我已发送验证码")
        self.verify_btn.add_css_class("suggested-action")
        self.verify_btn.add_css_class("pill")
        self.verify_btn.connect("clicked", self.on_verify_clicked)
        button_box.append(self.verify_btn)

        # 返回按钮
        back_btn = Gtk.Button(label="返回")
        back_btn.connect("clicked", self.on_back_clicked)
        button_box.append(back_btn)

        code_box.append(button_box)

        return code_box

    def on_generate_code_clicked(self, button):
        """生成验证码按钮点击事件"""
        self.qq = self.qq_entry.get_text().strip()

        if not self.qq or len(self.qq) < 5 or not self.qq.isdigit():
            self._show_error_dialog("请输入正确的QQ号（5-11位数字）")
            return

        # 禁用按钮和输入框
        self.gen_code_btn.set_sensitive(False)
        self.gen_code_btn.set_label("生成中...")
        self.qq_entry.set_sensitive(False)

        # 异步请求
        def request_thread():
            try:
                result = self.auth.generate_code(self.qq)
                GLib.idle_add(self._on_code_generated, result)
            except Exception as e:
                GLib.idle_add(self._on_request_error, str(e))

        threading.Thread(target=request_thread, daemon=True).start()

    def _on_code_generated(self, result):
        """验证码生成成功回调"""
        if result.get('code') == 200 and 'data' in result:
            self.verify_code = result['data']['verify_code']
            self.code_label.set_text(f"验证码{self.verify_code}")

            # 显示验证码区域
            self.code_revealer.set_reveal_child(True)

            # 开始倒计时
            self.start_countdown(120)
        else:
            message = result.get('message', '获取验证码失败')
            self._show_error_dialog(message)

            # 重置按钮
            self.gen_code_btn.set_sensitive(True)
            self.gen_code_btn.set_label("获取验证码")
            self.qq_entry.set_sensitive(True)

    def _on_request_error(self, error_msg):
        """请求错误回调"""
        self._show_error_dialog(f"网络错误：{error_msg}")

        # 重置按钮
        self.gen_code_btn.set_sensitive(True)
        self.gen_code_btn.set_label("获取验证码")
        self.qq_entry.set_sensitive(True)

    def start_countdown(self, seconds):
        """
        开始倒计时

        Args:
            seconds: 倒计时秒数
        """
        self.remaining_seconds = seconds

        def tick():
            if self.remaining_seconds > 0:
                self.countdown_label.set_text(f"剩余时间: {self.remaining_seconds}秒")
                self.remaining_seconds -= 1
                return True  # 继续定时器
            else:
                # 倒计时结束，重置界面
                self.on_back_clicked(None)
                return False

        # 清除旧的定时器
        if self.countdown_timeout_id:
            GLib.source_remove(self.countdown_timeout_id)

        # 立即更新一次
        tick()

        # 启动新的定时器
        self.countdown_timeout_id = GLib.timeout_add_seconds(1, tick)

    def on_copy_code_clicked(self, button):
        """复制验证码按钮点击事件"""
        clipboard = self.parent_window.get_clipboard()
        clipboard.set(f"验证码{self.verify_code}")

        # 临时改变按钮文字
        button.set_label("✓ 已复制")
        GLib.timeout_add_seconds(2, lambda: button.set_label("复制验证码"))

    def on_verify_clicked(self, button):
        """验证按钮点击事件"""
        button.set_sensitive(False)
        button.set_label("验证中...")

        def check_status_thread(retry=0):
            if retry >= 5:  # 最多检查5次
                GLib.idle_add(self._on_verify_failed)
                return

            try:
                result = self.auth.check_status(self.qq, self.verify_code)

                if result.get('code') == 200:
                    # 验证成功
                    GLib.idle_add(self._on_verify_success)
                else:
                    # 继续等待，1秒后重试
                    GLib.timeout_add_seconds(1, lambda: check_status_thread(retry + 1))
            except Exception as e:
                # 1秒后重试
                GLib.timeout_add_seconds(1, lambda: check_status_thread(retry + 1))

        threading.Thread(target=check_status_thread, daemon=True).start()

    def _on_verify_success(self):
        """验证成功回调"""
        # 清理定时器
        if self.countdown_timeout_id:
            GLib.source_remove(self.countdown_timeout_id)
        if self.check_status_timeout_id:
            GLib.source_remove(self.check_status_timeout_id)

        # 调用成功回调
        self.on_success()

    def _on_verify_failed(self):
        """验证失败回调"""
        self._show_error_dialog("验证超时，请确认已在QQ群或私聊机器人发送验证码")
        self.verify_btn.set_sensitive(True)
        self.verify_btn.set_label("我已发送验证码")

    def on_back_clicked(self, button):
        """返回按钮点击事件"""
        # 清理定时器
        if self.countdown_timeout_id:
            GLib.source_remove(self.countdown_timeout_id)
        if self.check_status_timeout_id:
            GLib.source_remove(self.check_status_timeout_id)

        # 隐藏验证码区域
        self.code_revealer.set_reveal_child(False)

        # 重置按钮和输入框
        self.gen_code_btn.set_sensitive(True)
        self.gen_code_btn.set_label("获取验证码")
        self.qq_entry.set_sensitive(True)
        self.verify_btn.set_sensitive(True)
        self.verify_btn.set_label("我已发送验证码")

    def _show_error_dialog(self, message):
        """显示错误对话框"""
        dialog = Adw.MessageDialog(transient_for=self.parent_window)
        dialog.set_heading("错误")
        dialog.set_body(message)
        dialog.add_response("ok", "确定")
        dialog.set_default_response("ok")
        dialog.present()

    def cleanup(self):
        """清理资源"""
        if self.countdown_timeout_id:
            GLib.source_remove(self.countdown_timeout_id)
        if self.check_status_timeout_id:
            GLib.source_remove(self.check_status_timeout_id)
