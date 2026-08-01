"""
4399AccountRegister - Python Rewrite
纯协议全自动 4399 账号注册机（含安全与风控规避措施）
"""

import asyncio
import base64
import hashlib
import json
import os
import random
import re
import string
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter, ImageOps

# ======================== 配置 ========================

@dataclass
class Config:
    onnx_model_path: str = "./4399ocr/4399ocr.onnx"
    sfz_file_path: str = "./sfz.txt"
    output_file_path: str = "./accounts.txt"
    account_prefix: str = "User"
    password_prefix: str = "Pass"
    worker_count: int = 12
    request_timeout: int = 12
    min_delay_ms: int = 200
    max_delay_ms: int = 1200
    captcha_min_delay_ms: int = 100
    captcha_max_delay_ms: int = 400
    post_min_delay_ms: int = 50
    post_max_delay_ms: int = 200


def load_config(path: str = "config.json") -> Config:
    """读取配置文件"""
    cfg = Config()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    return cfg


# ======================== 身份证池 ========================

# IDCard = tuple[str, str]  # (number, name)  # Python 3.9+
from typing import Tuple
IDCard = Tuple[str, str]  # (number, name)


class IDCardPool:
    """线程安全的身份证池，支持轮转和随机选取"""

    def __init__(self, filepath: str):
        self._cards: list[IDCard] = []
        self._index = 0
        self._load(filepath)

    def _load(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"身份证文件不存在: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 支持多种分隔符: "----" 或 ":"
                if "----" in line:
                    name, number = line.split("----", 1)
                    self._cards.append((number.strip(), name.strip()))
                elif ":" in line:
                    number, name = line.split(":", 1)
                    self._cards.append((number.strip(), name.strip()))
        if not self._cards:
            raise ValueError("身份证文件为空或格式错误")

    def next(self) -> IDCard:
        """轮转取用"""
        card = self._cards[self._index % len(self._cards)]
        self._index += 1
        return card

    def random_pick(self) -> IDCard:
        """随机取用"""
        return random.choice(self._cards)

    def __len__(self) -> int:
        return len(self._cards)


# ======================== AES 加密 ========================

# 4399 注册接口加密密钥（与 Go 版本保持一致）
_4399_PASS = b"lzYW5qaXVjaQ"


def i4399_encrypt(text: str) -> str:
    """
    4399 注册加密函数
    算法: MD5 链式迭代派生 key+iv → AES-256-CBC → OpenSSL 格式 Base64
    """
    salt = os.urandom(8)
    key_iv = b""
    prev = b""
    while len(key_iv) < 48:
        h = hashlib.md5()
        h.update(prev)
        h.update(_4399_PASS)
        h.update(salt)
        prev = h.digest()
        key_iv += prev

    key = key_iv[:32]
    iv = key_iv[32:48]

    # PKCS7 填充
    data = text.encode("utf-8")
    pad_len = 16 - (len(data) % 16)
    data += bytes([pad_len]) * pad_len

    from Crypto.Cipher import AES
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(data)

    # OpenSSL 格式: "Salted__" + salt + ciphertext
    return base64.b64encode(b"Salted__" + salt + encrypted).decode()


# ======================== OCR 识别 ========================

# 字符集（与 4399ocr.json 保持一致）
CHARSET = [
    " ", "6", "t", "y", "w", "J", "K", "k", "p", "7", "8", "9", "n", "j",
    "P", "q", "D", "G", "c", "N", "v", "X", "H", "Y", "5", "0", "h", "R",
    "f", "r", "4", "d", "A", "E", "M", "l", "V", "m", "a", "F", "s", "i",
    "z", "U", "g", "x", "u", "o", "3", "Q", "b", "e", "T", "1", "2",
]

FIXED_W, FIXED_H = 160, 64


class OCRWorker:
    """ONNX 验证码识别器（每个 worker 独立持有 session）"""

    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def recognize(self, img_bytes: bytes) -> str:
        """识别验证码图片字节流"""
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("L")
        except Exception:
            return ""

        # 预处理：缩放 + 二值化增强 + 归一化
        img = img.resize((FIXED_W, FIXED_H), Image.LANCZOS)
        img = ImageOps.autocontrast(img)

        arr = np.array(img, dtype=np.float32) / 255.0
        tensor = arr.reshape(1, 1, FIXED_H, FIXED_W)

        outputs = self.session.run([self.output_name], {self.input_name: tensor})[0]
        return self._ctc_decode(outputs[0])

    def _ctc_decode(self, logits: np.ndarray) -> str:
        """CTC 解码：去重 + 去空白"""
        results = []
        last = -1
        for idx in logits:
            idx = int(idx)
            if idx != last and 0 < idx < len(CHARSET):
                results.append(CHARSET[idx])
            last = idx
        return "".join(results)


# ======================== 设备指纹 / UA 池 ========================

# 多平台 UA 池，随机选取以分散指纹
UA_POOL = [
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 13; SM-S918B Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.130 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.180 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; 2211133C Build/TKQ1.220905.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
    # iOS Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    # Android Firefox
    "Mozilla/5.0 (Android 13; Mobile; rv:122.0) Gecko/122.0 Firefox/122.0",
    # WeChat Mobile
    "Mozilla/5.0 (Linux; Android 13; SM-S918B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.130 Mobile Safari/537.36 XWEB/1200275 MMWEBSID/20240101 MMWEBID/1234 MicroMessenger/8.0.46.2560(0x28002E30) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN",
]

ACCEPT_LANGUAGES = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "zh-Hans-CN;q=1, zh-Hans;q=0.9, en;q=0.8",
]

REFERERS = [
    "https://ptlogin.4399.com/",
    "https://ptlogin.4399.com/ptlogin/",
    "https://www.4399.com/",
]


def random_ua() -> str:
    return random.choice(UA_POOL)


def random_accept_language() -> str:
    return random.choice(ACCEPT_LANGUAGES)


def random_referer() -> str:
    return random.choice(REFERERS)


# ======================== 指纹混淆中间件 ========================

class FingerprintRandomizer:
    """
    请求指纹随机化：每次请求随机组合 UA / Accept-Language / Referer，
    避免完全相同的长连接指纹被风控关联。
    """

    @staticmethod
    def build_headers(referer: str = "") -> dict:
        headers = {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": random_accept_language(),
            "Accept-Encoding": "gzip, def, br",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    @staticmethod
    def post_headers(referer: str = "") -> dict:
        headers = FingerprintRandomizer.build_headers(referer)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Origin"] = "https://ptlogin.4399.com"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Site"] = "same-origin"
        return headers


# ======================== 代理池（可选） ========================

class ProxyPool:
    """
    代理池支持 - 有志之士可自行接入
    格式: http://user:pass@host:port 或 socks5://...
    """

    def __init__(self, proxy_file: Optional[str] = None):
        self._proxies: list[str] = []
        if proxy_file and os.path.exists(proxy_file):
            with open(proxy_file, "r") as f:
                self._proxies = [line.strip() for line in f if line.strip()]

    def get(self) -> Optional[str]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def __bool__(self) -> bool:
        return len(self._proxies) > 0


# ======================== 账号生成器 ========================

ACCOUNT_CHARS = string.digits + string.ascii_lowercase


def generate_account(prefix: str) -> str:
    length = random.randint(6, 10)
    return prefix + "".join(random.choices(ACCOUNT_CHARS, k=length))


def generate_password(prefix: str) -> str:
    length = random.randint(6, 10)
    return prefix + "".join(random.choices(ACCOUNT_CHARS, k=length))


# ======================== 注册核心 ========================

import io  # 为 OCR 的 BytesIO


class RegisterWorker:
    """单个注册 worker，持有独立的 OCR session 和 HTTP session"""

    def __init__(
        self,
        worker_id: int,
        cfg: Config,
        id_pool: IDCardPool,
        proxy_pool: ProxyPool,
    ):
        self.worker_id = worker_id
        self.cfg = cfg
        self.id_pool = id_pool
        self.proxy_pool = proxy_pool
        self.ocr = OCRWorker(cfg.onnx_model_path)
        self._output_lock = asyncio.Lock()

    async def register_once(self, session: aiohttp.ClientSession) -> Tuple[str, str, str]:
        """执行一次注册，返回 (状态, 账号, 密码)"""
        # 1. 获取 SessionID
        reg_frame = "https://ptlogin.4399.com/ptlogin/regFrame.do?regMode=reg_normal&appId=www_home"

        async with session.get(
            reg_frame,
            headers=FingerprintRandomizer.build_headers(),
            timeout=aiohttp.ClientTimeout(total=self.cfg.request_timeout),
            proxy=self.proxy_pool.get(),
        ) as resp:
            html = await resp.text()

        sid = ""
        m = re.search(r"captchaId=(.*?)'", html)
        if m:
            sid = m.group(1)
        else:
            m2 = re.search(r"UniLoginChangPIC\('(.*?)'\)", html)
            if m2:
                sid = m2.group(1)

        # 随机延时（模拟人工间隔）
        await asyncio.sleep(random.uniform(
            self.cfg.captcha_min_delay_ms / 1000,
            self.cfg.captcha_max_delay_ms / 1000,
        ))

        # 2. 获取并识别验证码
        code = ""
        if sid:
            captcha_url = f"https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={sid}"
            try:
                async with session.get(
                    captcha_url,
                    headers=FingerprintRandomizer.build_headers(reg_frame),
                    timeout=aiohttp.ClientTimeout(total=self.cfg.request_timeout),
                    proxy=self.proxy_pool.get(),
                ) as resp:
                    img_bytes = await resp.read()
                code = self.ocr.recognize(img_bytes)
            except Exception:
                code = ""

        await asyncio.sleep(random.uniform(
            self.cfg.post_min_delay_ms / 1000,
            self.cfg.post_max_delay_ms / 1000,
        ))

        # 3. 构造注册表单
        username = generate_account(self.cfg.account_prefix)
        password = generate_password(self.cfg.password_prefix)
        id_number, id_name = self.id_pool.random_pick()

        form = {
            "appId": "www_home",
            "regMode": "reg_normal",
            "sec": "1",
            "username": username,
            "password": i4399_encrypt(password),
            "passwordveri": i4399_encrypt(password),
            "realname": i4399_encrypt(id_name),
            "idcard": i4399_encrypt(id_number),
            "sessionId": sid,
            "inputCaptcha": code,
            "reg_eula_agree": "on",
        }

        # 4. POST 注册
        async with session.post(
            "https://ptlogin.4399.com/ptlogin/register.do",
            data=form,
            headers=FingerprintRandomizer.post_headers(reg_frame),
            timeout=aiohttp.ClientTimeout(total=self.cfg.request_timeout),
            proxy=self.proxy_pool.get(),
        ) as resp:
            result_html = await resp.text()

        # 5. 结果判定
        if "注册成功" in result_html or "postLoginHandler" in result_html:
            return ("成功", username, password)

        m = re.search(r'id="Msg"[^>]*>(.*?)</div>', result_html, re.DOTALL)
        if m:
            msg = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if "稍后再试" in msg or "繁忙" in msg:
                return ("IP熔断", username, msg)
            return ("失败", username, msg)

        return ("未知", username, result_html[:100])

    async def run_forever(self, output_file):
        """永久循环注册"""
        jar = aiohttp.DummyCookieJar()  # 每个 worker 独立 cookie
        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            while True:
                try:
                    status, username, info = await self.register_once(session)
                    if status == "成功":
                        msg = f"[成功] {username}:{info}"
                        print(f"\033[32m{msg}\033[0m")
                        async with self._output_lock:
                            output_file.write(f"{username}:{info}\n")
                            output_file.flush()
                    else:
                        print(f"\033[31m[失败] {username} -> {info}\033[0m")
                except Exception as e:
                    print(f"\033[31m[异常] worker-{self.worker_id}: {e}\033[0m")

                # 随机延时，避免固定频率
                await asyncio.sleep(random.uniform(
                    self.cfg.min_delay_ms / 1000,
                    self.cfg.max_delay_ms / 1000,
                ))


# ======================== 主函数 ========================

async def main():
    cfg = load_config()

    # 加载身份证池
    id_pool = IDCardPool(cfg.sfz_file_path)
    print(f"[初始化] 加载 {len(id_pool)} 条身份证信息")

    # 加载代理池（可选）
    proxy_pool = ProxyPool("./proxies.txt")
    if proxy_pool:
        print(f"[初始化] 加载 {len(proxy_pool._proxies)} 个代理")
    else:
        print("[警告] 未配置代理池，使用直连（高频可能触发 IP 熔断）")

    # 打开输出文件
    out = open(cfg.output_file_path, "a", encoding="utf-8")

    # 启动 workers
    tasks = []
    for i in range(cfg.worker_count):
        worker = RegisterWorker(i, cfg, id_pool, proxy_pool)
        tasks.append(asyncio.create_task(worker.run_forever(out)))

    print(f"[启动] {cfg.worker_count} 个 worker 已启动，按 Ctrl+C 停止")
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n[停止] 正在关闭...")
        for t in tasks:
            t.cancel()
        out.close()


if __name__ == "__main__":
    asyncio.run(main())
