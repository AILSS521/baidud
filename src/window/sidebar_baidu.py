"""
修改后的侧边栏 - 百度网盘版本
用于替换 sidebar.py 中的 window_create_sidebar 函数

使用方法：
1. 备份原 sidebar.py
2. 将此文件中的 window_create_sidebar_baidu 函数内容替换到 sidebar.py 的 window_create_sidebar
3. 或者在 variamain.py 中导入此函数替代原函数
"""

import os
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio
from stringstorage import gettext as _

from window.preferences import show_preferences


def window_create_sidebar_baidu(self, variaapp, variaVersion):
    """创建百度网盘版侧边栏（替换原 window_create_sidebar）"""

    sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    self.sidebar_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

    header_bar = Adw.HeaderBar()
    header_bar.add_css_class('flat')
    sidebar_box.append(header_bar)

    preferences_button = Gtk.Button(tooltip_text=_("Preferences"))
    preferences_button.set_icon_name("applications-system-symbolic")
    preferences_button.connect("clicked", show_preferences, self, variaapp, variaVersion)

    hamburger_button = Gtk.MenuButton(tooltip_text=_("Other"))
    hamburger_button.set_icon_name("open-menu-symbolic")
    hamburger_menu_model = Gio.Menu()

    # ==================== 百度网盘功能区域 ====================

    # 用户信息和操作区
    user_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    user_info_box.set_margin_start(8)
    user_info_box.set_margin_end(8)
    user_info_box.set_margin_top(8)
    user_info_box.set_margin_bottom(8)

    # 用户信息显示
    if self.auth.is_authenticated():
        user_info = self.auth.get_user_info()
        qq_number = user_info.get('qq', '未知')

        user_label = Gtk.Label()
        user_label.set_markup(f"<b>当前用户</b>\nQQ: {qq_number}")
        user_label.set_halign(Gtk.Align.START)
        user_info_box.append(user_label)

        # 注销按钮
        logout_btn = Gtk.Button(label="注销登录")
        logout_btn.connect("clicked", on_logout_clicked, self)
        user_info_box.append(logout_btn)
    else:
        # 未登录状态（理论上不应该出现，因为启动时已检查）
        login_label = Gtk.Label(label="未登录")
        user_info_box.append(login_label)

    user_info_frame = Gtk.Frame()
    user_info_frame.set_margin_bottom(8)
    user_info_frame.set_child(user_info_box)

    # 打开分享链接按钮
    share_link_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    share_link_box.set_margin_start(8)
    share_link_box.set_margin_end(8)
    share_link_box.set_margin_top(8)
    share_link_box.set_margin_bottom(8)

    open_share_btn = Gtk.Button(label="打开百度网盘分享链接")
    open_share_btn.add_css_class("suggested-action")
    open_share_btn.connect("clicked", on_open_share_link_clicked, self)
    share_link_box.append(open_share_btn)

    share_link_frame = Gtk.Frame()
    share_link_frame.set_margin_bottom(8)
    share_link_frame.set_child(share_link_box)

    # ==================== 原有功能区域（保留） ====================

    # 菜单项
    background_action = Gio.SimpleAction.new("background_mode", None)
    background_action.connect("activate", background_mode, self, variaapp)
    variaapp.add_action(background_action)

    cancel_all_action = Gio.SimpleAction.new("cancel_all_downloads", None)
    cancel_all_action.connect("activate", self.stop_all)
    variaapp.add_action(cancel_all_action)

    about_action = Gio.SimpleAction.new("downloads_folder", None)
    about_action.connect("activate", open_downloads_folder, self, self.appconf)
    variaapp.add_action(about_action)

    quit_action = Gio.SimpleAction.new("quit_varia", None)
    quit_action.connect("activate", quit_varia, self)
    variaapp.add_action(quit_action)

    downloads_folder_action = Gio.SimpleAction.new("about", None)
    downloads_folder_action.connect("activate", show_about, self, variaVersion)
    variaapp.add_action(downloads_folder_action)

    self.shutdown_action = Gio.SimpleAction.new("shutdown_on_completion", None)
    self.shutdown_action.connect("activate", shutdown_on_completion, self)
    self.shutdown_action.set_enabled(False)
    variaapp.add_action(self.shutdown_action)

    self.exit_action = Gio.SimpleAction.new("exit_on_completion", None)
    self.exit_action.connect("activate", exit_on_completion, self)
    self.exit_action.set_enabled(False)
    variaapp.add_action(self.exit_action)

    hamburger_menu_item_background = Gio.MenuItem.new(_("Background Mode"), "app.background_mode")
    hamburger_menu_model.append_item(hamburger_menu_item_background)

    hamburger_menu_item_cancel_all = Gio.MenuItem.new(_("Cancel All"), "app.cancel_all_downloads")
    hamburger_menu_model.append_item(hamburger_menu_item_cancel_all)

    hamburger_menu_item_open_downloads_folder = Gio.MenuItem.new(_("Open Download Folder"), "app.downloads_folder")
    hamburger_menu_model.append_item(hamburger_menu_item_open_downloads_folder)

    completion_submenu_model = Gio.Menu()

    completion_submenu_item_exit = Gio.MenuItem.new(_("Exit on Completion"), "app.exit_on_completion")
    completion_submenu_model.append_item(completion_submenu_item_exit)

    completion_submenu_item_shutdown = Gio.MenuItem.new(_("Shutdown on Completion"), "app.shutdown_on_completion")
    completion_submenu_model.append_item(completion_submenu_item_shutdown)

    hamburger_menu_model.append_submenu(_("Completion Options"), completion_submenu_model)

    hamburger_menu_item_about = Gio.MenuItem.new(_("About Varia"), "app.about")
    hamburger_menu_model.append_item(hamburger_menu_item_about)

    hamburger_menu_item_quit = Gio.MenuItem.new(_("Quit"), "app.quit_varia")
    hamburger_menu_model.append_item(hamburger_menu_item_quit)

    hamburger_button.set_menu_model(hamburger_menu_model)

    header_bar.pack_start(preferences_button)
    header_bar.pack_end(hamburger_button)

    # 过滤按钮（保留原有功能）
    self.filter_button_show_all = Gtk.ToggleButton()
    self.filter_button_show_all.add_css_class('flat')
    filter_button_show_all_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    filter_button_show_all_box.set_margin_top(8)
    filter_button_show_all_box.set_margin_bottom(8)
    filter_button_show_all_box.append(Gtk.Image.new_from_icon_name("radio-symbolic"))
    filter_button_show_all_label = Gtk.Label(label=_("All"))
    filter_button_show_all_label.add_css_class('body')
    filter_button_show_all_box.append(filter_button_show_all_label)
    self.filter_button_show_all.set_child(filter_button_show_all_box)
    self.filter_button_show_all.set_active(True)
    self.filter_button_show_all.connect("clicked", self.filter_download_list, "show_all")

    self.filter_button_show_downloading = Gtk.ToggleButton()
    self.filter_button_show_downloading.add_css_class('flat')
    filter_button_show_downloading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    filter_button_show_downloading_box.set_margin_top(8)
    filter_button_show_downloading_box.set_margin_bottom(8)
    filter_button_show_downloading_box.append(Gtk.Image.new_from_icon_name("content-loading-symbolic"))
    filter_button_show_downloading_label = Gtk.Label(label=_("In Progress"))
    filter_button_show_downloading_label.add_css_class('body')
    filter_button_show_downloading_box.append(filter_button_show_downloading_label)
    self.filter_button_show_downloading.set_child(filter_button_show_downloading_box)
    self.filter_button_show_downloading.connect("clicked", self.filter_download_list, "show_downloading")

    self.filter_button_show_completed = Gtk.ToggleButton()
    self.filter_button_show_completed.add_css_class('flat')
    filter_button_show_completed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    filter_button_show_completed_box.set_margin_top(8)
    filter_button_show_completed_box.set_margin_bottom(8)
    filter_button_show_completed_box.append(Gtk.Image.new_from_icon_name("object-select-symbolic"))
    filter_button_show_completed_label = Gtk.Label(label=_("Completed"))
    filter_button_show_completed_label.add_css_class('body')
    filter_button_show_completed_box.append(filter_button_show_completed_label)
    self.filter_button_show_completed.set_child(filter_button_show_completed_box)
    self.filter_button_show_completed.connect("clicked", self.filter_download_list, "show_completed")

    filter_buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    filter_buttons_box.set_margin_start(8)
    filter_buttons_box.set_margin_end(8)
    filter_buttons_box.append(self.filter_button_show_all)
    filter_buttons_box.append(self.filter_button_show_downloading)
    filter_buttons_box.append(self.filter_button_show_completed)

    self.sidebar_scheduler_label = Gtk.Label(label=_("Scheduler Mode On"))
    self.sidebar_scheduler_label.add_css_class('flat')
    self.sidebar_scheduler_label.set_margin_top(8)
    self.sidebar_scheduler_label.set_margin_bottom(8)

    # 组装侧边栏
    self.sidebar_content_box.append(user_info_frame)
    self.sidebar_content_box.append(share_link_frame)
    self.sidebar_content_box.append(filter_buttons_box)

    sidebar_box.append(self.sidebar_content_box)

    self.sidebar = sidebar_box


# ==================== 回调函数 ====================

def on_logout_clicked(button, main_window):
    """注销按钮点击事件"""
    dialog = Adw.MessageDialog(transient_for=main_window)
    dialog.set_heading("确认注销")
    dialog.set_body("确定要注销登录吗？注销后需要重新启动应用程序。")
    dialog.add_response("cancel", "取消")
    dialog.add_response("logout", "注销")
    dialog.set_response_appearance("logout", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")

    def on_response(dialog, response):
        if response == "logout":
            main_window.auth.logout()
            # 显示提示
            toast = Adw.Toast(title="已注销，请重启应用")
            toast.set_timeout(3)
            if hasattr(main_window, 'toast_overlay'):
                main_window.toast_overlay.add_toast(toast)
            # 关闭应用
            main_window.get_application().quit()

    dialog.connect("response", on_response)
    dialog.present()


def on_open_share_link_clicked(button, main_window):
    """打开分享链接按钮点击事件"""
    dialog = Adw.MessageDialog(transient_for=main_window)
    dialog.set_heading("打开百度网盘分享链接")
    dialog.set_body("请输入百度网盘分享链接和提取码（如果有）")

    # 创建输入区域
    dialog_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    dialog_box.set_margin_start(12)
    dialog_box.set_margin_end(12)
    dialog_box.set_margin_top(12)
    dialog_box.set_margin_bottom(12)

    # 分享链接输入
    link_entry = Adw.EntryRow()
    link_entry.set_title("分享链接")
    link_entry.set_text("")
    dialog_box.append(link_entry)

    # 提取码输入
    pwd_entry = Adw.EntryRow()
    pwd_entry.set_title("提取码（可选）")
    pwd_entry.set_text("")
    dialog_box.append(pwd_entry)

    dialog.set_extra_child(dialog_box)

    dialog.add_response("cancel", "取消")
    dialog.add_response("open", "打开")
    dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("open")

    def on_response(dialog, response):
        if response == "open":
            link = link_entry.get_text().strip()
            pwd = pwd_entry.get_text().strip()

            if not link:
                error_dialog = Adw.MessageDialog(transient_for=main_window)
                error_dialog.set_heading("错误")
                error_dialog.set_body("请输入分享链接")
                error_dialog.add_response("ok", "确定")
                error_dialog.present()
                return

            # 提取surl
            surl = main_window.api_client.extract_surl(link)
            if not surl:
                error_dialog = Adw.MessageDialog(transient_for=main_window)
                error_dialog.set_heading("错误")
                error_dialog.set_body("无法解析分享链接，请检查链接格式")
                error_dialog.add_response("ok", "确定")
                error_dialog.present()
                return

            # 打开文件浏览器
            from baidu.filebrowser import FileBrowserWindow
            browser = FileBrowserWindow(
                main_window,
                main_window.api_client,
                surl,
                pwd,
                main_window.add_baidu_download_task
            )
            browser.present()

    dialog.connect("response", on_response)
    dialog.present()


# ==================== 原有函数（保留） ====================

def background_mode(action, user_data1, main_window, variaapp):
    # 原有代码保持不变
    pass


def open_downloads_folder(action, user_data1, main_window, appconf):
    # 原有代码保持不变
    pass


def quit_varia(action, user_data1, main_window):
    # 原有代码保持不变
    pass


def show_about(action, user_data1, main_window, variaVersion):
    # 原有代码保持不变
    pass


def shutdown_on_completion(action, user_data1, main_window):
    # 原有代码保持不变
    pass


def exit_on_completion(action, user_data1, main_window):
    # 原有代码保持不变
    pass
