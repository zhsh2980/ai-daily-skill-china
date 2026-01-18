#!/usr/bin/env python3
"""
钉钉通知模块
发送每日科技简报到钉钉群
"""
import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import re
import requests
from typing import Optional


# 环境变量配置
DINGTALK_WEBHOOK_URL = os.environ.get("DINGTALK_WEBHOOK_URL")
DINGTALK_SECRET = os.environ.get("DINGTALK_SECRET")
ENABLE_DINGTALK = os.environ.get("ENABLE_DINGTALK", "false").lower() == "true"
GITHUB_PAGES_URL = os.environ.get("GITHUB_PAGES_URL", "")


class DingTalkNotifier:
    """钉钉机器人通知器"""

    def __init__(self, webhook_url: str = None, secret: str = None):
        """
        初始化钉钉通知器

        Args:
            webhook_url: Webhook URL，以 https://oapi.dingtalk.com/robot/send?access_token= 开头
            secret: 加签密钥，以 SEC 开头
        """
        self.webhook_url = webhook_url or DINGTALK_WEBHOOK_URL
        self.secret = secret or DINGTALK_SECRET

    def _generate_sign(self) -> tuple:
        """
        生成加签参数

        Returns:
            (timestamp, sign) 元组
        """
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(
            secret_enc,
            string_to_sign_enc,
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def _get_webhook_url(self) -> str:
        """获取带签名的 Webhook URL"""
        if not self.secret:
            return self.webhook_url
        timestamp, sign = self._generate_sign()
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def _is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.webhook_url and ENABLE_DINGTALK)

    def send_markdown(self, title: str, content: str) -> bool:
        """
        发送 Markdown 消息

        Args:
            title: 消息标题（会在通知中显示）
            content: Markdown 格式的消息内容

        Returns:
            是否发送成功
        """
        if not self._is_configured():
            print("[钉钉] 未配置或未启用，跳过发送")
            return False

        url = self._get_webhook_url()
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get("errcode") == 0:
                print(f"✅ 钉钉消息发送成功: {title}")
                return True
            else:
                print(f"❌ 钉钉消息发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"❌ 钉钉消息发送异常: {e}")
            return False


def extract_highlights(digest_content: str) -> list:
    """
    从简报内容中提取今日热点

    Args:
        digest_content: Markdown 格式的简报内容

    Returns:
        热点标题列表
    """
    highlights = []
    
    # 查找今日热点部分
    lines = digest_content.split('\n')
    in_highlights = False
    
    for line in lines:
        # 检测今日热点标题
        if '今日热点' in line or '热点' in line and '#' in line:
            in_highlights = True
            continue
        
        # 检测下一个板块标题，结束提取
        if in_highlights and line.startswith('###'):
            break
        
        # 提取加粗的标题
        if in_highlights and '**' in line:
            # 匹配 **标题** 格式
            match = re.search(r'\*\*(.+?)\*\*', line)
            if match:
                highlights.append(match.group(1))
    
    return highlights[:5]  # 最多返回5条


def send_dingtalk_digest(digest_content: str, date: str) -> bool:
    """
    发送简报到钉钉

    Args:
        digest_content: Markdown 格式的简报内容
        date: 日期字符串，如 "2026-01-18"

    Returns:
        是否发送成功
    """
    notifier = DingTalkNotifier()
    
    if not notifier._is_configured():
        print("[钉钉] 未配置或未启用，跳过发送")
        return False

    # 提取今日热点
    highlights = extract_highlights(digest_content)
    
    # 构建钉钉消息
    content = f"## 📰 每日科技简报 · {date}\n\n"
    
    # 添加热点摘要
    if highlights:
        content += "### 📌 今日热点\n"
        for h in highlights:
            content += f"- {h}\n"
    
    # 添加链接
    if GITHUB_PAGES_URL:
        page_url = GITHUB_PAGES_URL.rstrip('/')
        content += f"\n---\n\n[🔗 点击查看完整简报]({page_url})"
    
    title = f"📰 每日科技简报 · {date}"
    return notifier.send_markdown(title, content)


if __name__ == "__main__":
    # 测试代码
    test_content = """
# 科技简报 | 2026-01-18

### 1. 今日热点

**Cursor "浏览器实验"数据造假风波**
测试内容

**Cloudflare 收购 Astro**
测试内容

### 2. 技术趋势
测试
"""
    send_dingtalk_digest(test_content, "2026-01-18")
