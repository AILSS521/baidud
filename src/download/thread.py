import ctypes
from gi.repository import GLib
import threading
from urllib.parse import urlparse
import requests
import time
import os
import json
from stringstorage import gettext as _
import re
import base64
import multiprocessing as multiprocessing

class DownloadThread(threading.Thread):
    def __init__(self, app, url, actionrow, downloadname, download, mode, paused, dir, headers=None):
        threading.Thread.__init__(self)
        self.api = app.api
        self.downloaddir = dir
        self.url = url
        self.speed_label = actionrow.speed_label
        self.download = download
        self.auth = app.appconf["auth"]
        self.auth_username = app.appconf["auth_username"]
        self.auth_password = app.appconf["auth_password"]
        self.actionrow = actionrow
        self.app = app
        self.cancelled = False
        self.mode = mode
        self.speed = 0
        self.paused_because_exceeds_limit = False
        self.total_file_size_text = ""
        self.download_message_shown = False
        self.headers = headers  # 自定义 HTTP headers（用于百度网盘下载）
        self.download_details = {
            'type': "",
            'status': _("Downloading"),
            'remaining': "∞",
            'download_speed': "0 B/s",
            'percentage': "0%",
            'messaage': "",
            'completed_length': 0,
            'upload_length': 0
        }

        if downloadname:
            self.downloadname = downloadname
        else:
            self.downloadname = ""

        try:
            self.filepath = os.path.join(app.appconf["download_directory"], downloadname)

        except:
            self.filepath = None

        self.download_temp_files = []

        self.state_file = ""
        self.is_complete = False
        self.paused = paused

        self.retry = False

    def is_valid_url(self):
        try:
            result = urlparse(self.url)
            if not ((self.url[0:7] == "http://") or (self.url[0:8] == "https://")):
                self.url = "http://" + self.url
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def run(self):
        self.download_message_shown = False

        if (self.url == "sus"):
            try:
                # Lol nice - Caleb (N0tACyb0rg)
                GLib.idle_add(self.show_message("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣤⣤⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⠟⠉⠉⠉⠉⠉⠉⠉⠙⠻⢶⣄⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣷⡀⠀⠀⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡟⠀⣠⣶⠛⠛⠛⠛⠛⠛⠳⣦⡀⠀⠘⣿⡄⠀⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⠁⠀⢹⣿⣦⣀⣀⣀⣀⣀⣠⣼⡇⠀⠀⠸⣷⠀⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⡏⠀⠀⠀⠉⠛⠿⠿⠿⠿⠛⠋⠁⠀⠀⠀⠀⣿⡄⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡇⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⣸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣧⠀\n⠀⠀⠀⠀⠀⠀⠀⢸⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⠀\n⠀⠀⠀⠀⠀⠀⠀⣾⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀\n⠀⠀⠀⠀⠀⠀⠀⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀\n⠀⠀⠀⠀⠀⠀⢰⣿⠀⠀⠀⠀⣠⡶⠶⠿⠿⠿⠿⢷⣦⠀⠀⠀⠀⠀⠀⠀⣿⠀\n⠀⠀⣀⣀⣀⠀⣸⡇⠀⠀⠀⠀⣿⡀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⣿⠀\n⣠⡿⠛⠛⠛⠛⠻⠀⠀⠀⠀⠀⢸⣇⠀⠀⠀⠀⠀⠀⣿⠇⠀⠀⠀⠀⠀⠀⣿⠀\n⢻⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⡟⠀⠀⢀⣤⣤⣴⣿⠀⠀⠀⠀⠀⠀⠀⣿⠀\n⠈⠙⢷⣶⣦⣤⣤⣤⣴⣶⣾⠿⠛⠁⢀⣶⡟⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡟⠀\n⠀⠀⠀⠀⠉⠉⠉⠉⠉⠀⠀⠀⠀⠀⠈⣿⣆⡀⠀⠀⠀⠀⠀⠀⢀⣠⣴⡾⠃⠀\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠻⢿⣿⣾⣿⡿⠿⠟⠋⠁⠀⠀⠀"))
            except:
                pass
            GLib.idle_add(self.actionrow.pause_button.set_visible, False)
            GLib.idle_add(self.actionrow.progress_bar.set_visible, False)
            GLib.idle_add(self.actionrow.info_button.set_visible, False)
            return
        
        download_options = {}

        if self.url.startswith("magnet:"):
            if self.app.appconf["torrent_enabled"] == "1":
                download_options["dir"] = self.app.appconf["torrent_download_directory"]
                download_options["follow_torrent"] = "true"
                self.downloaddir = self.app.appconf["torrent_download_directory"]

            else:
                try:
                    GLib.idle_add(self.show_message, _("Torrenting is disabled."))
                    print("Error: Can't add magnet link because torrenting is disabled.")
                except:
                    pass
                return

        else:
            if not (self.is_valid_url()):
                try:
                    GLib.idle_add(self.show_message, _("This is not a valid URL."))
                    print("Error: Not a valid url.")
                except:
                    print("Error: Couldn't display 'not a valid url' error, for some reason.")
                return
            response = requests.head(self.url)
            if ((response.status_code == 401) and (self.auth == '1')):
                if (self.url[0:7] == "http://"):
                    self.url = self.url[:7] + self.auth_username + ":" + self.auth_password + "@" + self.url[7:]
                elif (self.url[0:8] == "https://"):
                    self.url = self.url[:8] + self.auth_username + ":" + self.auth_password + "@" + self.url[8:]
                else:
                    self.url = self.auth_username + ":" + self.auth_password + "@" + self.url
                print ("Authentication enabled.")

        print(self.downloadname)

        self.app.check_all_status()

        # Regular download, use aria2p:
        if self.mode == "regular":

            if self.downloadname != None:
                download_options["out"] = self.downloadname

            # 添加自定义 HTTP headers（用于百度网盘下载）
            if self.headers:
                if isinstance(self.headers, dict):
                    # 将字典格式转换为 aria2c 需要的列表格式
                    header_list = [f"{key}: {value}" for key, value in self.headers.items()]
                    download_options["header"] = header_list
                elif isinstance(self.headers, list):
                    # 如果已经是列表格式，直接使用
                    download_options["header"] = self.headers

            if self.download == None:
                self.download = self.api.add_uris([self.url], options=download_options)

            if self.app.scheduler_currently_downloading and self.paused == False and self.download.gid:
                if self.download.is_paused:
                    self.download.resume()

                self.download_details['status'] = _("Downloading")

            else:
                self.pause(True)

            if self.download.is_torrent:
                self.download_details['type'] = _("Torrent")

            else:
                self.download_details['type'] = _("Regular")
            
            self.previous_filename = ""
            self.app.filter_download_list("no", self.app.applied_filter)
            download_began = False
            self.filepath = os.path.join(self.app.appconf["download_directory"], self.downloadname)

            if self.retry == False:
                self.save_state()

            print("Download added. | " + self.download.gid + "\n" + self.downloaddir + "\n" + self.url)
            print(download_options)

            while (self.cancelled == False):
                try:
                    self.download.update()

                    if self.download.is_paused:
                        self.download_details['status'] = _("Paused")
                    
                    else:
                        self.download_details['status'] = _("Downloading")

                    try:
                        self.total_file_size_text = self.download.total_length_string(True) # Get human readable format
                    except:
                        pass

                    if download_began == False and self.download.is_active:
                        self.actionrow.pause_button.get_child().set_from_icon_name("media-playback-pause-symbolic")
                        download_began = True
                    
                    if (self.download.is_torrent and self.download.name.startswith("[METADATA]")) == False and self.downloadname != self.download.name:
                        self.downloadname = self.download.name
                        self.save_state()
                        self.filepath = os.path.join(self.app.appconf["download_directory"], self.downloadname)
                    
                    if self.actionrow.filename_label.get_text() != self.downloadname:
                        GLib.idle_add(self.actionrow.filename_label.set_text, self.download.name)

                    self.update_labels_and_things(None)
                    if ((self.download.is_complete) and (self.download.is_metadata == False)):
                        print('Download complete: ' + self.download.gid)
                        GLib.idle_add(self.set_complete)
                        break
                    elif ((self.download.is_torrent) and (self.download.seeder)):
                        print('Torrent complete, seeding: ' + self.download.gid)
                        GLib.idle_add(self.set_complete)
                        break
                    elif (self.download.status == "error"):
                        GLib.idle_add(self.set_failed, None)
                        return
                except:
                    return
                
                time.sleep(0.5)

    def show_message(self, message):
        print(f'Download message shown: {message}')
        GLib.idle_add(self.speed_label.set_text, message)
        self.download_details['message'] = message
        self.download_message_shown = True

    def update_labels_and_things(self, object=None):
        speed_label_text = ""
        self.speed = 0
        download_remaining_string = "∞"
        percentage_label_text = ""
        speed_label_text_speed = ""

        progress = self.download.progress
        speed = self.download.download_speed
        self.speed = speed

        if self.download.is_torrent:
            self.download_details['completed_length'] = self.download.completed_length
            self.download_details['upload_length'] = self.download.upload_length

            if self.download.seeder:
                if self.app.appconf["torrent_seeding_enabled"] == "1":
                    GLib.idle_add(self.show_message(_("Seeding torrent")))
                else:
                    GLib.idle_add(self.set_complete)
                return

        download_delta = self.download.eta
        download_speed_mb = (speed / 1024 / 1024)

        download_seconds = download_delta.total_seconds()
        download_seconds = abs(int(download_seconds))
        download_hours, download_seconds = divmod(download_seconds, 3600)
        download_minutes, download_seconds = divmod(download_seconds, 60)

        download_hours = str(download_hours).zfill(2)
        download_minutes = str(download_minutes).zfill(2)
        download_seconds = str(download_seconds).zfill(2)

        if speed != 0:
            download_remaining_string = f"{download_hours}:{download_minutes}:{download_seconds}"

        percentage_label_text = _("{number}%").replace("{number}", str(round(progress)))

        if int(str(download_speed_mb)[0]) == 0:
            download_speed_kb = (speed / 1024)
            if int(str(download_speed_kb)[0]) == 0:
                speed_label_text_speed = f"{round(speed, 2)} {_(' B/s')}"
            else:
                speed_label_text_speed = f"{round(speed / 1024, 2)} {_(' KB/s')}"
        else:
            speed_label_text_speed = f"{round(speed / 1024 / 1024, 2)} {_(' MB/s')}"

        if self.download.is_torrent and hasattr(self.download, "files"):
            for file in self.download.files:
                if file not in self.download_temp_files:
                    self.download_temp_files.append(file)

        speed_label_text = f"{speed_label_text}{self.total_file_size_text}  ·  {speed_label_text_speed}  ·  {download_remaining_string} {_('remaining')}"
        self.download_details['message'] = ""

        if self.is_complete == False:
            GLib.idle_add(self.actionrow.progress_bar.set_fraction, progress / 100)
            GLib.idle_add(self.speed_label.set_text, speed_label_text)
            GLib.idle_add(self.actionrow.percentage_label.set_text, percentage_label_text)
            self.download_details['remaining'] = download_remaining_string
            self.download_details['percentage'] = percentage_label_text
            self.download_details['download_speed'] = speed_label_text_speed

    def pause(self, change_pause_button_icon):
        if self.download and self.is_complete == False:
            try:
                self.download.pause()
            except:
                pass

            if self.app.terminating == False:
                self.paused = True
                self.app.check_all_status()
                change_pause_button_icon = True

            print ("Download paused.")
            self.save_state()

            self.paused_because_exceeds_limit = False

            if change_pause_button_icon:
                self.actionrow.pause_button.get_child().set_from_icon_name("media-playback-start-symbolic")
                self.actionrow.pause_button.set_tooltip_text(_("Resume"))

            self.download_details['status'] = _("Paused")

    def resume(self):
        if self.download and self.is_complete == False:
            change_pause_button_icon = False

            if self.download.is_paused == True:

                self.paused = False
                change_pause_button_icon = True

                try:
                    self.download.resume()
                    print ("Download resumed.")
                    self.save_state()

                except:
                    try:
                        self.show_message(_("An error occurred:") + " " + self.download.error_message.split("status=")[1])
                        print ("An error occurred when resuming. " + self.download.error_message.split("status=")[1])
                    except:
                        pass

            if change_pause_button_icon:
                self.actionrow.pause_button.get_child().set_from_icon_name("media-playback-pause-symbolic")
                self.actionrow.pause_button.set_tooltip_text(_("Pause"))

        self.app.check_all_status()

        self.download_details['status'] = _("Downloading")

    def stop(self):
        if self.download:
            downloadgid = self.download.gid
            downloadname = self.download.name
            istorrent = self.download.is_torrent

            try:
                self.download.remove(force=True)
            except:
                print('Download couldn\'t be removed, probably already removed.')

            if ((istorrent and self.download.seeder) or self.download.is_complete) == False: # Delete files if incomplete

                if os.path.exists(os.path.join(self.app.appconf["download_directory"], (downloadgid + ".varia"))):
                    os.remove(os.path.join(self.app.appconf["download_directory"], (downloadgid + ".varia")))

                if istorrent == False:
                    if os.path.exists(os.path.join(self.downloaddir, downloadname)):
                        try:
                            os.remove(os.path.join(self.downloaddir, downloadname))
                        except:
                            pass

                for file in self.download_temp_files:
                    print(file.path)

                    if os.path.exists(file.path):
                        file_parentdir = file.path.parent.absolute()

                        if os.path.isfile(file.path):
                            try:
                                os.remove(file.path)
                            except:
                                pass
                        elif os.path.isdir(file.path):
                            try:
                                os.rmdir(file.path)
                            except:
                                pass

                        if file_parentdir is not self.downloaddir and os.listdir(file_parentdir) == []:
                            os.rmdir(file_parentdir)

            print ("Download stopped.")

            if os.path.exists(self.state_file):
                os.remove(self.state_file)

        self.download_temp_files.clear()

        self.app.download_list.remove(self.actionrow)
        self.app.downloads.remove(self)
        self.download = None

        self.app.check_all_status()

        self = None
        return

    def save_state(self):
        if self.download:
            state = {
                'url': self.url,
                'filename': self.downloadname,
                'type': self.mode,
                'paused': self.paused,
                'index': self.app.downloads.index(self),
                'dir': self.downloaddir
            }

            save_filename = self.download.gid

            if os.path.isfile(os.path.join(self.app.appconf["download_directory"], f'{save_filename}.varia')):
                os.remove(os.path.join(self.app.appconf["download_directory"], f'{save_filename}.varia'))

            with open(os.path.join(self.app.appconf["download_directory"], f'{save_filename}.varia'), 'w') as f:
                json.dump(state, f)

            print ("State saved for download.")

            if self.app.terminating == True:
                self.cancelled = True

            self.state_file = os.path.join(self.app.appconf["download_directory"], f'{save_filename}.varia')

    def return_gid(self):
        if self.download:
            return self.download.gid

    def return_is_paused(self):
        if self.download:
            if self.download.is_paused:
                return True
            else:
                return False
                
    def set_complete(self):
        self.is_complete = True
        self.cancelled = True
        GLib.idle_add(self.speed_label.set_text, _("Download complete."))
        self.cancelled = True
        self.app.filter_download_list("no", self.app.applied_filter)
        self.actionrow.progress_bar.set_fraction(1)
        self.actionrow.progress_bar.add_css_class("success")

        self.download_details['status'] = _("Completed")
        self.download_details['remaining'] = ""
        self.download_details['download_speed'] = ""

        is_seeding = self.download.is_torrent and self.download.seeder
        if is_seeding == False and os.path.exists(os.path.join(self.downloaddir,(self.download.gid + ".varia"))):
            os.remove(os.path.join(self.downloaddir,(self.download.gid + ".varia")))

        if os.path.exists(self.state_file):
            os.remove(self.state_file)

        GLib.idle_add(self.actionrow.stop_button.remove_css_class, "destructive-action")
        GLib.idle_add(self.actionrow.stop_button.set_icon_name, "process-stop-symbolic")
        GLib.idle_add(self.actionrow.percentage_label.set_visible, False)
        GLib.idle_add(self.actionrow.pause_button.set_open_mode, self.actionrow.pause_button, self.app, self)
    
    def set_failed(self, fraction):
        if fraction is not None:
            self.actionrow.progress_bar.set_fraction(fraction)

        self.actionrow.progress_bar.add_css_class("error")
        self.cancelled = True

        if (self.download.error_code == "24"):
            self.show_message(_("Authorization failed."))

        else:
            self.show_message(_("An error occurred:") + " " + str(self.download.error_code))

        self.download_details['status'] = _("Failed")
        self.download_details['remaining'] = ""
        self.download_details['download_speed'] = ""

        GLib.idle_add(self.actionrow.pause_button.set_retry_mode, self.actionrow.pause_button, self.app, self)
        self.app.filter_download_list("no", self.app.applied_filter)
