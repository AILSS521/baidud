"""
百度网盘文件浏览器窗口
显示分享链接的文件列表并支持下载
"""

import threading
from gi.repository import Gtk, Adw, GLib, Gio


class FileBrowserWindow(Adw.Window):
    """文件浏览器窗口"""

    def __init__(self, parent, api_client, surl, pwd, on_download_callback):
        """
        初始化文件浏览器窗口

        Args:
            parent: 父窗口
            api_client: BaiduAPIClient实例
            surl: 分享链接的surl
            pwd: 提取码
            on_download_callback: 下载回调函数 callback(file_info)
        """
        super().__init__()

        self.api = api_client
        self.surl = surl
        self.pwd = pwd
        self.on_download = on_download_callback

        # 文件列表数据
        self.current_dir = "/"
        self.uk = None
        self.shareid = None
        self.randsk = None
        self.file_items = []

        # 窗口设置
        self.set_transient_for(parent)
        self.set_default_size(900, 700)
        self.set_title("百度网盘 - 文件浏览")

        # 构建UI
        self._build_ui()

        # 加载文件列表
        self._load_file_list()

    def _build_ui(self):
        """构建用户界面"""
        # 主容器
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # 工具栏
        toolbar = self._create_toolbar()
        main_box.append(toolbar)

        # 面包屑导航
        self.breadcrumb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.breadcrumb_box.set_margin_start(12)
        self.breadcrumb_box.set_margin_end(12)
        self.breadcrumb_box.set_margin_top(12)
        self.breadcrumb_box.set_margin_bottom(12)

        breadcrumb_frame = Gtk.Frame()
        breadcrumb_frame.set_child(self.breadcrumb_box)
        main_box.append(breadcrumb_frame)

        # 文件列表区域
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.list_box.add_css_class("boxed-list")
        scrolled.set_child(self.list_box)

        main_box.append(scrolled)

        # 底部操作栏
        action_bar = self._create_action_bar()
        main_box.append(action_bar)

        # 加载指示器（初始隐藏）
        self.loading_revealer = Gtk.Revealer()
        self.loading_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_margin_top(12)
        loading_box.set_margin_bottom(12)

        spinner = Gtk.Spinner()
        spinner.start()
        loading_box.append(spinner)

        loading_label = Gtk.Label(label="正在加载...")
        loading_box.append(loading_label)

        self.loading_revealer.set_child(loading_box)
        main_box.append(self.loading_revealer)

        self.set_content(main_box)

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = Adw.HeaderBar()

        # 返回上级目录按钮
        self.back_btn = Gtk.Button()
        self.back_btn.set_icon_name("go-previous-symbolic")
        self.back_btn.set_tooltip_text("返回上级目录")
        self.back_btn.connect("clicked", self.on_back_clicked)
        self.back_btn.set_sensitive(False)  # 初始在根目录，禁用
        toolbar.pack_start(self.back_btn)

        # 刷新按钮
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("刷新")
        refresh_btn.connect("clicked", lambda _: self._load_file_list())
        toolbar.pack_end(refresh_btn)

        return toolbar

    def _create_action_bar(self):
        """创建底部操作栏"""
        action_bar = Gtk.ActionBar()

        # 选择信息标签
        self.selection_label = Gtk.Label(label="未选择文件")
        self.selection_label.add_css_class("dim-label")
        action_bar.pack_start(self.selection_label)

        # 下载按钮
        self.download_btn = Gtk.Button(label="下载选中文件")
        self.download_btn.add_css_class("suggested-action")
        self.download_btn.set_sensitive(False)
        self.download_btn.connect("clicked", self.on_download_clicked)
        action_bar.pack_end(self.download_btn)

        # 监听选择变化
        self.list_box.connect("selected-rows-changed", self.on_selection_changed)

        return action_bar

    def _update_breadcrumb(self):
        """更新面包屑导航"""
        # 清空现有面包屑
        while self.breadcrumb_box.get_first_child():
            self.breadcrumb_box.remove(self.breadcrumb_box.get_first_child())

        # 分割路径
        if self.current_dir == "/":
            parts = ["/"]
        else:
            parts = ["/"] + self.current_dir.strip("/").split("/")

        # 创建面包屑按钮
        for i, part in enumerate(parts):
            if i > 0:
                # 添加分隔符
                separator = Gtk.Label(label="›")
                separator.add_css_class("dim-label")
                self.breadcrumb_box.append(separator)

            # 创建路径按钮
            btn = Gtk.Button(label=part if part != "/" else "根目录")
            btn.add_css_class("flat")

            # 构建完整路径
            if i == 0:
                path = "/"
            else:
                path = "/" + "/".join(parts[1:i+1])

            btn.connect("clicked", lambda b, p=path: self._navigate_to(p))
            self.breadcrumb_box.append(btn)

        # 更新返回按钮状态
        self.back_btn.set_sensitive(self.current_dir != "/")

    def _navigate_to(self, path):
        """
        导航到指定路径

        Args:
            path: 目标路径
        """
        self.current_dir = path
        self._load_file_list()

    def _load_file_list(self):
        """加载文件列表"""
        # 显示加载指示器
        self.loading_revealer.set_reveal_child(True)
        self.list_box.set_sensitive(False)

        def request_thread():
            try:
                result = self.api.get_file_list(self.surl, self.current_dir, self.pwd)
                GLib.idle_add(self._on_file_list_loaded, result)
            except Exception as e:
                GLib.idle_add(self._on_request_error, str(e))

        threading.Thread(target=request_thread, daemon=True).start()

    def _on_file_list_loaded(self, result):
        """文件列表加载成功回调"""
        # 隐藏加载指示器
        self.loading_revealer.set_reveal_child(False)
        self.list_box.set_sensitive(True)

        if result.get('code') != 200:
            message = result.get('message', '获取文件列表失败')
            self._show_error_dialog(message)
            return

        data = result.get('data', {})
        self.uk = data.get('uk')
        self.shareid = data.get('shareid')
        self.randsk = data.get('randsk')
        self.file_items = data.get('list', [])

        # 清空列表
        while self.list_box.get_first_child():
            self.list_box.remove(self.list_box.get_first_child())

        # 添加文件项
        for item in self.file_items:
            row = self._create_file_row(item)
            self.list_box.append(row)

        # 更新面包屑
        self._update_breadcrumb()

        # 如果没有文件，显示提示
        if not self.file_items:
            empty_label = Gtk.Label(label="此目录为空")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(48)
            empty_label.set_margin_bottom(48)
            self.list_box.append(empty_label)

    def _on_request_error(self, error_msg):
        """请求错误回调"""
        self.loading_revealer.set_reveal_child(False)
        self.list_box.set_sensitive(True)
        self._show_error_dialog(f"网络错误：{error_msg}")

    def _create_file_row(self, item):
        """
        创建文件行

        Args:
            item: 文件信息字典

        Returns:
            Adw.ActionRow实例
        """
        row = Adw.ActionRow()

        # 图标
        if item['isdir'] == 1:
            icon_name = "folder-symbolic"
        else:
            # 根据文件扩展名选择图标
            filename = item.get('server_filename', '')
            if any(filename.endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz']):
                icon_name = "package-x-generic-symbolic"
            elif any(filename.endswith(ext) for ext in ['.mp4', '.avi', '.mkv', '.mov']):
                icon_name = "video-x-generic-symbolic"
            elif any(filename.endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.aac']):
                icon_name = "audio-x-generic-symbolic"
            elif any(filename.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.bmp']):
                icon_name = "image-x-generic-symbolic"
            else:
                icon_name = "text-x-generic-symbolic"

        icon = Gtk.Image.new_from_icon_name(icon_name)
        row.add_prefix(icon)

        # 文件名
        row.set_title(item.get('server_filename', '未知文件'))

        # 副标题（文件大小）
        if item['isdir'] == 0:
            size = item.get('size', 0)
            size_str = self._format_file_size(size)
            row.set_subtitle(size_str)
        else:
            row.set_subtitle("文件夹")

        # 存储文件信息
        row.file_data = item

        # 如果是文件夹，双击可进入
        if item['isdir'] == 1:
            row.set_activatable(True)
            row.connect("activated", self.on_folder_activated)

        return row

    def _format_file_size(self, size):
        """
        格式化文件大小

        Args:
            size: 字节数

        Returns:
            格式化后的字符串（如 "1.5 MB"）
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / 1024 / 1024:.2f} MB"
        else:
            return f"{size / 1024 / 1024 / 1024:.2f} GB"

    def on_folder_activated(self, row):
        """文件夹行激活事件（双击）"""
        folder_path = row.file_data.get('path', '')
        if folder_path:
            self.current_dir = folder_path
            self._load_file_list()

    def on_back_clicked(self, button):
        """返回上级目录按钮点击事件"""
        if self.current_dir == "/":
            return

        # 计算上级目录
        parent_dir = "/".join(self.current_dir.rstrip("/").split("/")[:-1])
        if not parent_dir:
            parent_dir = "/"

        self.current_dir = parent_dir
        self._load_file_list()

    def on_selection_changed(self, list_box):
        """选择变化事件"""
        selected_rows = list_box.get_selected_rows()

        # 只统计文件（非文件夹）
        file_count = 0
        for row in selected_rows:
            if hasattr(row, 'file_data') and row.file_data.get('isdir') == 0:
                file_count += 1

        if file_count > 0:
            self.selection_label.set_text(f"已选择 {file_count} 个文件")
            self.download_btn.set_sensitive(True)
        else:
            self.selection_label.set_text("未选择文件")
            self.download_btn.set_sensitive(False)

    def on_download_clicked(self, button):
        """下载按钮点击事件"""
        selected_rows = self.list_box.get_selected_rows()

        # 收集文件ID
        fs_ids = []
        for row in selected_rows:
            if hasattr(row, 'file_data') and row.file_data.get('isdir') == 0:
                fs_ids.append(row.file_data.get('fs_id'))

        if not fs_ids:
            self._show_error_dialog("请选择要下载的文件")
            return

        if len(fs_ids) > 10:
            self._show_error_dialog("一次最多下载10个文件")
            return

        # 禁用下载按钮
        button.set_sensitive(False)
        button.set_label("获取下载链接中...")

        def request_thread():
            try:
                result = self.api.get_download_links(
                    self.randsk, self.uk, self.shareid,
                    fs_ids, self.surl, self.current_dir, self.pwd
                )
                GLib.idle_add(self._on_download_links_received, result, button)
            except Exception as e:
                GLib.idle_add(self._on_download_error, str(e), button)

        threading.Thread(target=request_thread, daemon=True).start()

    def _on_download_links_received(self, result, button):
        """下载链接获取成功回调"""
        button.set_sensitive(True)
        button.set_label("下载选中文件")

        if result.get('code') != 200:
            message = result.get('message', '获取下载链接失败')
            self._show_error_dialog(message)
            return

        files = result.get('data', [])

        # 添加下载任务
        success_count = 0
        for file_info in files:
            if file_info.get('url') != '失败请重试':
                self.on_download(file_info)
                success_count += 1

        # 显示结果
        if success_count > 0:
            self._show_info_dialog(f"成功添加 {success_count} 个下载任务")
            # 可选：关闭窗口
            # self.close()
        else:
            self._show_error_dialog("所有文件获取下载链接失败，请重试")

    def _on_download_error(self, error_msg, button):
        """下载链接获取错误回调"""
        button.set_sensitive(True)
        button.set_label("下载选中文件")
        self._show_error_dialog(f"网络错误：{error_msg}")

    def _show_error_dialog(self, message):
        """显示错误对话框"""
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("错误")
        dialog.set_body(message)
        dialog.add_response("ok", "确定")
        dialog.set_default_response("ok")
        dialog.present()

    def _show_info_dialog(self, message):
        """显示信息对话框"""
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("提示")
        dialog.set_body(message)
        dialog.add_response("ok", "确定")
        dialog.set_default_response("ok")
        dialog.present()
