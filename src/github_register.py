#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 GitHub Register - GitHub 批量注册模块（适用于虚拟机）
=============================================================================
功能：通过 Chrome CDP 控制浏览器自动注册 GitHub 账号
流程：打开注册页 → 填写表单 → 手动 CAPTCHA → 自动获取验证码 → 完成验证
运行：python github_register.py
说明：需要 Chrome 以 --remote-debugging-port=9222 --remote-allow-origins=* 启动
=============================================================================
"""

import re
import json
import time
import sys
import os
import urllib.request
import requests
import websocket
from datetime import datetime

# ===========================================================================
# 配置
# ===========================================================================
class Config:
    # 注册信息
    USERNAME_PREFIX = "kazeiro-nova"
    PASSWORD = "Gt#8xKp!2vLmQw9z"
    EMAIL_PREFIX = "kazeiro.nova"

    # temporam API（临时邮箱）
    TEMPORAM_API = "https://api.temporam.com/v1"
    TEMPORAM_KEY = "tm_UfIwItCE8z8l7b28n9J03-BuWegJacZq"

    # Chrome CDP
    CHROME_DEBUG = "http://localhost:9222"

    # GitHub URLs
    GITHUB_SIGNUP = "https://github.com/signup"
    GITHUB_VERIFY = "https://github.com/account_verifications"

    # 输出文件
    OUTPUT_FILE = "./github_accounts.json"

    # 验证码等待超时（秒）
    CODE_TIMEOUT = 180


def load_config(path="config.json"):
    """从配置文件加载"""
    cfg = Config()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    return cfg


# ===========================================================================
# 日志
# ===========================================================================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ===========================================================================
# temporam API（临时邮箱）
# ===========================================================================
def get_domains():
    """获取可用域名"""
    try:
        h = {"Authorization": f"Bearer {Config.TEMPORAM_KEY}"}
        r = requests.get(f"{Config.TEMPORAM_API}/domains", headers=h, timeout=15)
        if r.status_code == 200 and not r.json().get("error"):
            return [d["domain"] for d in r.json().get("data", [])]
    except Exception as e:
        log(f"获取域名失败: {e}")
    return []


def get_emails(email):
    """获取邮件列表"""
    try:
        h = {"Authorization": f"Bearer {Config.TEMPORAM_KEY}"}
        r = requests.get(f"{Config.TEMPORAM_API}/emails", headers=h,
                         params={"email": email}, timeout=15)
        if r.status_code == 200 and not r.json().get("error"):
            return r.json().get("data", [])
    except Exception as e:
        log(f"获取邮件失败: {e}")
    return []


def extract_code(emails):
    """从邮件中提取验证码"""
    for e in emails:
        subject = e.get("subject", "")
        # 邮件正文可能在 body/html/text/summary 字段
        body = (e.get("body", "") or e.get("html", "") or
                e.get("text", "") or e.get("summary", ""))
        # GitHub 验证码是 8 位数字
        for pattern in [r'(?:code|launch)[^\d]*(\d{8})',
                        r'(\d{8})[^\d]*(?:code|launch)',
                        r'>\s*(\d{8})\s*<', r'\b(\d{8})\b']:
            for text in [subject, body]:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    return m.group(1)
    return None


def wait_for_code(email, timeout=180, interval=5):
    """轮询等待验证码"""
    log(f"等待验证码到 {email}...")
    start = time.time()
    while time.time() - start < timeout:
        emails = get_emails(email)
        if emails:
            log(f"收到 {len(emails)} 封邮件")
            for e in emails:
                log(f"  主题: {e.get('subject', 'N/A')}")
            code = extract_code(emails)
            if code:
                log(f"验证码: {code}")
                return code
        time.sleep(interval)
    return None


# ===========================================================================
# Chrome CDP 控制
# ===========================================================================
class Chrome:
    """Chrome DevTools Protocol 控制器"""

    def __init__(self, debug_url=None):
        self.debug_url = debug_url or Config.CHROME_DEBUG
        self.ws = None
        self.mid = 0

    def connect(self):
        """连接到 Chrome"""
        resp = urllib.request.urlopen(f"{self.debug_url}/json")
        tabs = json.loads(resp.read())
        page = next((t for t in tabs if t.get("type") == "page"), None)
        if not page:
            raise Exception("未找到 Chrome 页面，请确保 Chrome 已启动并开放调试端口")
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"])
        log(f"已连接 Chrome: {page.get('title', '')[:40]}")

    def close(self):
        if self.ws:
            self.ws.close()

    def cmd(self, method, params=None):
        """发送 CDP 命令"""
        self.mid += 1
        msg = {"id": self.mid, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.mid:
                return r.get("result", {})

    def js(self, expr):
        """执行 JavaScript"""
        r = self.cmd("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True
        })
        if "exceptionDetails" in r:
            raise Exception(f"JS 错误: {r['exceptionDetails']}")
        return r.get("result", {}).get("value")

    def navigate(self, url):
        """导航到 URL"""
        self.cmd("Page.navigate", {"url": url})
        time.sleep(8)

    def screenshot(self, path="screenshot.png"):
        """截图"""
        import base64
        r = self.cmd("Page.captureScreenshot", {"format": "png"})
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        log(f"截图: {path}")

    def get_info(self):
        """获取页面标题和 URL"""
        return self.js("document.title"), self.js("window.location.href")


# ===========================================================================
# GitHub 注册器
# ===========================================================================
class GitHubRegister:
    """GitHub 自动注册器"""

    def __init__(self):
        self.chrome = Chrome()
        self.accounts = []
        self.load_accounts()

    def load_accounts(self):
        """加载已有账号"""
        if os.path.exists(Config.OUTPUT_FILE):
            try:
                with open(Config.OUTPUT_FILE, "r", encoding="utf-8") as f:
                    self.accounts = json.load(f)
            except:
                self.accounts = []

    def save_accounts(self):
        """保存账号列表"""
        with open(Config.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, indent=2, ensure_ascii=False)
        log(f"账号已保存到 {Config.OUTPUT_FILE}")

    def generate_username(self, index):
        """生成用户名"""
        return f"{Config.USERNAME_PREFIX}-{index}"

    def generate_email(self, index):
        """生成邮箱"""
        domains = get_domains()
        domain = domains[0] if domains else "temporam.com"
        return f"{Config.EMAIL_PREFIX}-{index}@{domain}"

    def wait_for_form(self, timeout=15):
        """等待表单加载完成"""
        log("等待表单加载...")
        start = time.time()
        while time.time() - start < timeout:
            ready = self.chrome.js("""
                (!!document.querySelector('#email') &&
                 !!document.querySelector('#password') &&
                 !!document.querySelector('#login'))
            """)
            if ready:
                return True
            time.sleep(1)
        return False

    def fill_form(self, email, username, password):
        """填写注册表单"""
        if not self.wait_for_form():
            raise Exception("表单加载超时，未找到输入框")

        self.chrome.js(f"document.querySelector('#email').value = '{email}'")
        self.chrome.js("document.querySelector('#email').dispatchEvent(new Event('input',{bubbles:true}))")
        self.chrome.js(f"document.querySelector('#password').value = '{password}'")
        self.chrome.js("document.querySelector('#password').dispatchEvent(new Event('input',{bubbles:true}))")
        self.chrome.js(f"document.querySelector('#login').value = '{username}'")
        self.chrome.js("document.querySelector('#login').dispatchEvent(new Event('input',{bubbles:true}))")
        log(f"表单已填写: {email} / {username}")

    def check_captcha(self):
        """检查是否有 CAPTCHA"""
        return self.chrome.js("""
            (!!document.querySelector('iframe[src*="captcha"]') ||
             !!document.querySelector('iframe[src*="octocaptcha"]'))
        """)

    def click_submit(self):
        """点击注册表单的提交按钮"""
        self.chrome.js("""
            (function() {
                var btns = document.querySelectorAll('button[type="submit"]');
                for (var i = 0; i < btns.length; i++) {
                    var form = btns[i].form;
                    if (form && form.method === 'post' && form.action.indexOf('/signup') !== -1) {
                        btns[i].click();
                        return 'ok';
                    }
                }
                return 'not found';
            })()
        """)
        time.sleep(8)

    def enter_verification_code(self, code):
        """输入验证码（分 8 个输入框）"""
        for i in range(8):
            digit = code[i]
            self.chrome.js(f"""
            (function() {{
                var input = document.getElementById('launch-code-{i}');
                if (input) {{
                    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, '{digit}');
                    input.dispatchEvent(new Event('input', {{bubbles:true}}));
                    input.dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
            }})()
            """)
        log(f"验证码已填入: {code}")

    def click_continue(self):
        """点击 Continue 按钮"""
        return self.chrome.js("""
            (function() {
                var btns = document.querySelectorAll('button[type="submit"]');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.trim() === 'Continue') {
                        btns[i].click();
                        return 'clicked';
                    }
                }
                return 'not found';
            })()
        """)

    def register_one(self, index):
        """注册单个账号"""
        username = self.generate_username(index)
        email = self.generate_email(index)
        password = Config.PASSWORD

        log(f"=" * 50)
        log(f"注册账号 #{index}")
        log(f"  用户名: {username}")
        log(f"  邮箱: {email}")

        # 导航到注册页
        title, url = self.chrome.get_info()
        if "signup" not in str(url).lower():
            self.chrome.navigate(Config.GITHUB_SIGNUP)
            title, url = self.chrome.get_info()

        # 填写表单
        self.fill_form(email, username, password)
        self.chrome.screenshot(f"github_{index}_form.png")

        # 检查 CAPTCHA
        if self.check_captcha():
            log("")
            log("!" * 50)
            log(f"账号 {username} 需要手动 CAPTCHA 验证")
            log("请在浏览器中完成 CAPTCHA 并点击 Create account 提交")
            log("脚本将自动检测提交结果...")
            log("!" * 50)
            # 等待用户手动完成 CAPTCHA 并提交（最多等 120 秒）
            start = time.time()
            while time.time() - start < 120:
                time.sleep(3)
                title, url = self.chrome.get_info()
                if "signup" not in str(url).lower() or "verify" in str(url).lower():
                    break
            else:
                log("等待提交超时")
                return None
        else:
            # 无 CAPTCHA 直接提交
            log("提交注册...")
            self.click_submit()

        title, url = self.chrome.get_info()
        log(f"提交后: {title} | {url}")
        self.chrome.screenshot(f"github_{index}_submit.png")

        # 检查结果
        if "verify" in str(url).lower() or "account_verifications" in str(url).lower():
            log("进入邮箱验证阶段!")
        elif "signup" in str(url).lower():
            if self.check_captcha():
                log("仍有 CAPTCHA，请手动完成")
                input("按回车: ")
                self.click_submit()
                title, url = self.chrome.get_info()

        # 等待验证码
        code = wait_for_code(email, timeout=Config.CODE_TIMEOUT)
        if not code:
            log(f"账号 {username} 未收到验证码")
            return None

        # 输入验证码
        self.enter_verification_code(code)
        time.sleep(1)
        self.click_continue()
        time.sleep(10)

        title, url = self.chrome.get_info()
        log(f"最终: {title} | {url}")

        # 判断成功
        if "login" in str(url).lower() or "dashboard" in str(url).lower():
            log(f"账号 {username} 注册成功!")
            account = {
                "username": username,
                "email": email,
                "password": password,
                "verification_code": code,
                "created_at": datetime.now().isoformat(),
                "status": "success"
            }
            self.accounts.append(account)
            self.save_accounts()
            return account
        else:
            log(f"账号 {username} 注册结果不明")
            return None

    def run(self, count=1):
        """批量注册"""
        log("=" * 60)
        log(f"GitHub 批量注册 - 目标 {count} 个")
        log("=" * 60)

        self.chrome.connect()
        try:
            start_index = len(self.accounts) + 1
            for i in range(start_index, start_index + count):
                result = self.register_one(i)
                if result:
                    log(f"✅ #{i} 注册成功: {result['username']}")
                else:
                    log(f"❌ #{i} 注册失败")
                time.sleep(2)
        finally:
            self.chrome.close()

        log("")
        log("=" * 60)
        log(f"注册完成! 共 {len(self.accounts)} 个账号")
        log(f"账号信息保存在: {Config.OUTPUT_FILE}")
        log("=" * 60)


# ===========================================================================
# 入口
# ===========================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except:
            count = 1
    else:
        count = 1

    reg = GitHubRegister()
    reg.run(count=count)
