"""
认证管理器
负责处理用户认证、Token管理和设备ID生成
"""

import json
import uuid
import time
from pathlib import Path
from typing import Optional, Dict
import requests


class AuthManager:
    """用户认证管理器"""

    def __init__(self, api_base_url: str = "https://duapi.linglong521.cn/api"):
        """
        初始化认证管理器

        Args:
            api_base_url: API基础URL
        """
        self.api_base = api_base_url
        self.token: Optional[str] = None
        self.device_id: str = self._get_or_create_device_id()
        self._load_token()

    def _get_config_dir(self) -> Path:
        """获取配置目录"""
        config_dir = Path.home() / ".config" / "varia"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _get_or_create_device_id(self) -> str:
        """
        生成或获取设备ID

        Returns:
            设备ID字符串
        """
        device_file = self._get_config_dir() / "device_id"

        if device_file.exists():
            return device_file.read_text().strip()

        # 生成新的设备ID
        device_id = f"device_{uuid.uuid4().hex[:16]}"
        device_file.write_text(device_id)
        return device_id

    def generate_code(self, qq: str) -> Dict:
        """
        生成验证码

        Args:
            qq: QQ号

        Returns:
            API响应字典

        Raises:
            requests.RequestException: 网络请求失败
        """
        response = requests.post(
            f"{self.api_base}/auth/generate-code.php",
            json={"qq": qq, "device_id": self.device_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def check_status(self, qq: str, code: str) -> Dict:
        """
        检查验证状态

        Args:
            qq: QQ号
            code: 验证码

        Returns:
            API响应字典

        Raises:
            requests.RequestException: 网络请求失败
        """
        response = requests.get(
            f"{self.api_base}/auth/check-status.php",
            params={"qq": qq, "code": code, "device_id": self.device_id},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # 如果验证成功，保存Token
        if data.get('code') == 200 and 'data' in data:
            self.token = data['data']['token']
            self._save_token()

        return data

    def _save_token(self):
        """保存Token到本地配置文件"""
        if not self.token:
            return

        config_file = self._get_config_dir() / "auth.json"
        config_file.write_text(json.dumps({
            "token": self.token,
            "saved_at": int(time.time())
        }, indent=2))

    def _load_token(self):
        """从本地配置文件加载Token"""
        config_file = self._get_config_dir() / "auth.json"

        if not config_file.exists():
            return

        try:
            data = json.loads(config_file.read_text())
            self.token = data.get('token')
        except (json.JSONDecodeError, KeyError):
            # 配置文件损坏，删除它
            config_file.unlink(missing_ok=True)

    def is_authenticated(self) -> bool:
        """
        检查是否已认证

        Returns:
            True如果已认证且Token未过期，否则False
        """
        if not self.token:
            return False

        try:
            # 解码JWT不验证签名，只检查过期时间
            import base64
            parts = self.token.split('.')
            if len(parts) != 3:
                return False

            # 解码payload（添加padding）
            payload_encoded = parts[1]
            padding = 4 - len(payload_encoded) % 4
            if padding != 4:
                payload_encoded += '=' * padding

            payload_json = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_json)

            # 检查过期时间
            exp = payload.get('exp', 0)
            return exp > time.time()
        except Exception:
            return False

    def get_user_info(self) -> Optional[Dict]:
        """
        获取当前用户信息（从Token中解码）

        Returns:
            用户信息字典，包含qq、device_id、ip、city、province等
            如果未认证或Token无效则返回None
        """
        if not self.token:
            return None

        try:
            import base64
            parts = self.token.split('.')
            if len(parts) != 3:
                return None

            payload_encoded = parts[1]
            padding = 4 - len(payload_encoded) % 4
            if padding != 4:
                payload_encoded += '=' * padding

            payload_json = base64.urlsafe_b64decode(payload_encoded)
            return json.loads(payload_json)
        except Exception:
            return None

    def logout(self):
        """注销登录，删除本地Token"""
        self.token = None
        config_file = self._get_config_dir() / "auth.json"
        config_file.unlink(missing_ok=True)

    def get_token(self) -> Optional[str]:
        """
        获取当前Token

        Returns:
            Token字符串，如果未认证则返回None
        """
        return self.token if self.is_authenticated() else None
