import gi
import os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from stringstorage import gettext as _

def show_download_details_dialog(button, self, download_item):
    self.download_details_dialog_shown = True
    self.details_dialog_resize_timeout = None
    self.details_dialog_message_actionrow_added = False

    details_dialog = Adw.PreferencesDialog(title=_("Download Details"))

    prefs_page = Adw.PreferencesPage()
    details_dialog.add(prefs_page)

    group_message = Adw.PreferencesGroup()

    actionrow_download_message = Adw.ActionRow()
    label_download_message = Gtk.Label()
    label_download_message.set_selectable(True)
    label_download_message.set_wrap(True)
    actionrow_download_message.add_prefix(label_download_message)
    group_message.add(actionrow_download_message)

    if download_item.download_thread.download_message_shown and download_item.download_thread.download_details.get('message', '') != '':
        label_download_message.set_text(download_item.download_thread.download_details.get('message', ''))
        prefs_page.add(group_message)
        self.details_dialog_message_actionrow_added = True

    group_1 = Adw.PreferencesGroup()
    prefs_page.add(group_1)

    actionrow_download_type = Adw.ActionRow(title=_("Type"))
    label_download_type = Gtk.Label(label=download_item.download_thread.download_details.get('type', ''))
    actionrow_download_type.add_suffix(label_download_type)
    group_1.add(actionrow_download_type)

    actionrow_download_status = Adw.ActionRow(title=_("Status"))
    label_download_status = Gtk.Label(label=download_item.download_thread.download_details.get('status', ''))
    actionrow_download_status.add_suffix(label_download_status)
    group_1.add(actionrow_download_status)

    actionrow_download_file_name = Adw.ActionRow(title=_("File Name"))
    label_download_file_name = Gtk.Label(label=download_item.download_thread.actionrow.filename_label.get_text())
    label_download_file_name.set_wrap(True)
    actionrow_download_file_name.add_suffix(label_download_file_name)
    group_1.add(actionrow_download_file_name)

    actionrow_download_url = Adw.ActionRow(title=_("URL"))
    label_url = Gtk.Label(label=download_item.download_thread.url)
    label_url.set_wrap(True)
    label_url.set_selectable(True)
    actionrow_download_url.add_suffix(label_url)
    group_1.add(actionrow_download_url)

    actionrow_download_percentage = Adw.ActionRow(title=_("Percentage Downloaded"))
    label_percentage = Gtk.Label()
    actionrow_download_percentage.add_suffix(label_percentage)
    group_1.add(actionrow_download_percentage)

    actionrow_download_remaining = Adw.ActionRow(title=_("Remaining"))
    label_remaining = Gtk.Label()
    actionrow_download_remaining.add_suffix(label_remaining)
    group_1.add(actionrow_download_remaining)

    actionrow_download_download_speed = Adw.ActionRow(title=_("Download Speed"))
    label_download_speed = Gtk.Label()
    actionrow_download_download_speed.add_suffix(label_download_speed)
    group_1.add(actionrow_download_download_speed)

    def update_details():
        if self.download_details_dialog_shown:
            close_dialog = True

            try:
                if self.download_details_dialog_shown and download_item and download_item.download_thread and download_item.download_thread.download_details:
                    details = download_item.download_thread.download_details
                    label_download_type.set_text(details.get('type', ''))
                    label_download_status.set_text(details.get('status', ''))
                    label_percentage.set_text(details.get('percentage', ''))
                    label_remaining.set_text(details.get('remaining', ''))
                    label_download_speed.set_text(details.get('download_speed', ''))

                    if self.details_dialog_message_actionrow_added == False and download_item and download_item.download_thread.download_message_shown and download_item.download_thread.download_details.get('message', '') != '':
                        label_download_message.set_text(download_item.download_thread.download_details.get('message', ''))
                        prefs_page.insert(group_message, 0)
                        self.details_dialog_message_actionrow_added = True
                    
                    elif self.details_dialog_message_actionrow_added == True and download_item and download_item.download_thread.download_message_shown == False:
                        prefs_page.remove(group_message)
                        self.details_dialog_message_actionrow_added = False

                    close_dialog = False
                
                else:
                    close_dialog = True

            except:
                close_dialog = True

            if close_dialog:
                details_dialog.close()
                return False

            else:
                GLib.timeout_add(1000, update_details)
        
        else:
            return False

    def update_size(*_):
        GLib.idle_add(apply_update_size)

        if self.details_dialog_resize_timeout:
            GLib.source_remove(self.details_dialog_resize_timeout)
            self.details_dialog_resize_timeout = None

        self.window_resize_timeout = GLib.timeout_add(50, apply_update_size)

    def apply_update_size():
        details_dialog.set_content_width(self.get_width())
        details_dialog.set_content_height(self.get_height())

    def on_closed(dialog):
        self.download_details_dialog_shown = False
        return
    
    details_dialog.resize_timeout = None

    self.connect("notify::maximized", update_size)
    self.connect("notify::default-width", update_size)
    self.connect("notify::default-height", update_size)
    update_size()

    if os.name == 'nt':
        details_dialog.set_content_width(self.get_default_size()[0])
        details_dialog.set_content_height(self.get_default_size()[1])
    details_dialog.connect("closed", on_closed)
    details_dialog.present(self)

    GLib.idle_add(update_details)