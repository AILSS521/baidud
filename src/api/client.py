"""
百度网盘API客户端
负责与后端API通信，获取文件列表和下载链接
"""

from typing import Dict, List, Optional
import requests


class BaiduAPIClient:
    """百度网盘API客户端"""

    def __init__(self, auth_manager, api_base_url: str = "https://duapi.linglong521.cn/api"):
        """
        初始化API客户端

        Args:
            auth_manager: 认证管理器实例
            api_base_url: API基础URL
        """
        self.auth = auth_manager
        self.api_base = api_base_url

    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头

        Returns:
            包含Authorization和Content-Type的请求头字典
        """
        token = self.auth.get_token()
        if not token:
            raise ValueError("未登录，请先进行身份认证")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get_file_list(self, surl: str, dir: str = "/", pwd: str = "") -> Dict:
        """
        获取百度网盘分享文件列表

        Args:
            surl: 分享链接的surl部分（如：1abcdefg）
            dir: 目录路径，默认为根目录
            pwd: 提取码，如果有的话

        Returns:
            API响应字典，包含uk、shareid、randsk和文件列表

        Raises:
            requests.RequestException: 网络请求失败
            ValueError: 参数错误或未登录
        """
        response = requests.post(
            f"{self.api_base}/baidu/file-list.php",
            headers=self._get_headers(),
            json={
                "surl": surl,
                "dir": dir,
                "pwd": pwd
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def get_download_links(
        self,
        randsk: str,
        uk: str,
        shareid: str,
        fs_ids: List[int],
        surl: str,
        dir: str = "/",
        pwd: str = ""
    ) -> Dict:
        """
        获取文件下载链接

        Args:
            randsk: 从file_list获取的randsk
            uk: 从file_list获取的uk
            shareid: 从file_list获取的shareid
            fs_ids: 文件ID列表（最多10个）
            surl: 分享链接的surl部分
            dir: 目录路径
            pwd: 提取码

        Returns:
            API响应字典，包含下载链接列表

        Raises:
            requests.RequestException: 网络请求失败
            ValueError: 参数错误或未登录
        """
        if len(fs_ids) > 10:
            raise ValueError("一次最多获取10个文件的下载链接")

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
        response.raise_for_status()
        return response.json()

    def extract_surl(self, share_link: str) -> Optional[str]:
        """
        从分享链接中提取surl

        Args:
            share_link: 完整的百度网盘分享链接

        Returns:
            surl部分，如果解析失败则返回None

        Examples:
            >>> client.extract_surl("https://pan.baidu.com/s/1abcdefg")
            "1abcdefg"
            >>> client.extract_surl("pan.baidu.com/s/1xyz")
            "1xyz"
        """
        import re

        # 匹配 /s/ 后面的部分
        pattern = r'/s/([a-zA-Z0-9_-]+)'
        match = re.search(pattern, share_link)

        if match:
            return match.group(1)

        # 如果没有匹配到，检查是否直接就是surl
        if share_link and len(share_link) > 5 and share_link[0] == '1':
            return share_link

        return None
