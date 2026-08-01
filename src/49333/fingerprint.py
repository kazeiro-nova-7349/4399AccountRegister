# -*- coding: utf-8 -*-
"""
Android 设备指纹生成器 — 模拟真实浏览器完整会话流程
包含：设备池、浏览器指纹、会话预热、Cookie 管理、请求链模拟
"""
import random
import time

# ---- Android 设备池 ----
# (品牌, 型号, 设备代号, 分辨率宽, 分辨率高, dpi)
ANDROID_DEVICES = [
    # Samsung
    ("samsung", "SM-G991B", "Galaxy S21", 1080, 2400, 420),
    ("samsung", "SM-G996B", "Galaxy S21+", 1080, 2400, 420),
    ("samsung", "SM-S908B", "Galaxy S22 Ultra", 1440, 3088, 500),
    ("samsung", "SM-A546B", "Galaxy A54", 1080, 2340, 450),
    ("samsung", "SM-A145F", "Galaxy A14", 1080, 2408, 450),
    ("samsung", "SM-A256B", "Galaxy A25", 1080, 2340, 450),
    # Xiaomi
    ("Xiaomi", "2211133G", "Mi 13", 1080, 2400, 440),
    ("Xiaomi", "23049PCD8G", "13T Pro", 1440, 3200, 520),
    ("Xiaomi", "23078PND5G", "Redmi Note 12 Pro", 1080, 2400, 440),
    ("Xiaomi", "22071219CG", "Redmi Note 11", 1080, 2400, 440),
    ("Xiaomi", "2311DRK48G", "Redmi 12 5G", 1080, 2460, 440),
    # OnePlus
    ("OnePlus", "CPH2449", "11", 1440, 3216, 525),
    ("OnePlus", "NE2215", "10 Pro", 1440, 3216, 525),
    ("OnePlus", "CPH2413", "Nord 3", 1080, 2400, 440),
    # OPPO
    ("OPPO", "CPH2371", "Find X5 Pro", 1440, 3216, 525),
    ("OPPO", "CPH2477", "Reno 10", 1080, 2412, 440),
    ("OPPO", "CPH2247", "A96", 1080, 2400, 440),
    # vivo
    ("vivo", "V2309", "V29 Pro", 1080, 2400, 440),
    ("vivo", "V2244", "X90 Pro", 1080, 2400, 440),
    ("vivo", "V2165", "Y22", 720, 1612, 270),
    # realme
    ("realme", "RMX3630", "11 Pro+", 1080, 2412, 393),
    ("realme", "RMX3511", "Narzo 60", 1080, 2400, 393),
    # Google Pixel
    ("Google", "Pixel 7 Pro", "Pixel 7 Pro", 1440, 3120, 512),
    ("Google", "Pixel 8", "Pixel 8", 1080, 2400, 428),
    ("Google", "Pixel 7a", "Pixel 7a", 1080, 2400, 428),
    # Motorola
    ("motorola", "XT2343-2", "Edge 40", 1080, 2400, 393),
    ("motorola", "XT2201-3", "Edge 30 Pro", 1080, 2400, 393),
    # Huawei
    ("Huawei", "ALN-AL80", "Mate 60 Pro", 1260, 2720, 440),
    ("Huawei", "BNE-LX1", "nova 11", 1084, 2412, 392),
]

# ---- Android 版本池 ----
ANDROID_VERSIONS = [
    ("10", "29"),
    ("11", "30"),
    ("12", "31"),
    ("12L", "32"),
    ("13", "33"),
    ("14", "34"),
]

# ---- 地区/语言池 ----
REGIONS = [
    {"language": "zh-CN", "country": "CN", "timezone": "Asia/Shanghai", "locale": "zh_CN"},
    {"language": "zh-CN", "country": "CN", "timezone": "Asia/Chongqing", "locale": "zh_CN"},
    {"language": "zh-HK", "country": "HK", "timezone": "Asia/Hong_Kong", "locale": "zh_HK"},
    {"language": "en-US", "country": "US", "timezone": "America/New_York", "locale": "en_US"},
    {"language": "en-GB", "country": "GB", "timezone": "Europe/London", "locale": "en_GB"},
]

# ---- 构建号池前缀 ----
BUILD_PREFIXES = ["RP1A", "QP1A", "SP1A", "TP1A", "TQ3A", "UP1A", "V14U"]


def _random_build_id():
    """生成随机 BUILD ID"""
    prefix = random.choice(BUILD_PREFIXES)
    suffix = ''.join(random.choices('0123456789', k=6))
    return f"{prefix}.{suffix}"


# ---- Chrome 版本池 ----
CHROME_VERSIONS = [
    (120, 0, 6099, (80, 150)),
    (121, 0, 6167, (80, 150)),
    (122, 0, 6268, (80, 150)),
    (123, 0, 6312, (80, 150)),
    (124, 0, 6367, (80, 150)),
    (125, 0, 6422, (80, 150)),
    (126, 0, 6478, (80, 150)),
    (127, 0, 6533, (80, 150)),
    (128, 0, 6588, (80, 150)),
    (129, 0, 6643, (80, 150)),
    (130, 0, 6698, (80, 150)),
    (131, 0, 6753, (80, 150)),
]


def _random_chrome_version():
    """生成随机 Chrome 版本号"""
    major, minor, build, patch_range = random.choice(CHROME_VERSIONS)
    patch = random.randint(*patch_range)
    return major, minor, build, patch


def generate_android_fingerprint():
    """
    生成一个完整的 Android 浏览器指纹
    Returns: dict 包含所有指纹字段
    """
    brand, model, name, width, height, dpi = random.choice(ANDROID_DEVICES)
    android_ver, sdk = random.choice(ANDROID_VERSIONS)
    region = random.choice(REGIONS)
    build_id = _random_build_id()
    chrome_major, chrome_minor, chrome_build, chrome_patch = _random_chrome_version()

    # ---- User-Agent (Android Chrome WebView) ----
    ua_string = (
        f"Mozilla/5.0 (Linux; Android {android_ver}; {model} Build/{build_id}; wv) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
        f"Chrome/{chrome_major}.{chrome_minor}.{chrome_build}.{chrome_patch} "
        f"Mobile Safari/537.36"
    )

    # ---- Sec-Ch-Ua 头 (与 UA 匹配) ----
    sec_ch_ua = (
        f'"Not_A Brand";v="8", "Chromium";v="{chrome_major}", '
        f'"Google Chrome";v="{chrome_major}"'
    )

    # ---- Accept-Language ----
    accept_lang = f"{region['language']};q=0.9, {region['language'].split('-')[0]};q=0.8"

    # ---- 屏幕/视口 ----
    viewport_width = width
    viewport_height = height - random.randint(80, 200)

    # ---- WebGL / Canvas 指纹 (随机化渲染器) ----
    gpu_renderers = [
        "ANGLE (Mesa, Intel (R) UHD Graphics 630, OpenGL 4.6)",
        "ANGLE (Qualcomm, Adreno (TM) 650, OpenGL ES 3.2)",
        "ANGLE (ARM, Mali-G78, OpenGL ES 3.2)",
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650, OpenGL 4.5)",
        "ANGLE (Samsung, Mali-G77, OpenGL ES 3.2)",
    ]
    webgl_renderer = random.choice(gpu_renderers)
    webgl_vendor = "Google Inc." if "ANGLE" in webgl_renderer else "Unknown"

    # ---- 请求头 ----
    headers = {
        "User-Agent": ua_string,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": accept_lang,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": sec_ch_ua,
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Ch-Ua-Platform-Version": f'"{android_ver}"',
    }

    fingerprint = {
        "brand": brand,
        "model": model,
        "name": name,
        "android_version": android_ver,
        "sdk": sdk,
        "build_id": build_id,
        "chrome_version": f"{chrome_major}.{chrome_minor}.{chrome_build}.{chrome_patch}",
        "resolution": f"{width}x{height}",
        "dpi": dpi,
        "viewport": f"{viewport_width}x{viewport_height}",
        "user_agent": ua_string,
        "accept_language": accept_lang,
        "headers": headers,
        "region": region,
        "webgl_vendor": webgl_vendor,
        "webgl_renderer": webgl_renderer,
        "platform": "Linux aarch64",
        "mobile": True,
    }

    return fingerprint


class RealisticBrowserSession:
    """
    模拟真实浏览器会话 — 完整请求链
    1. 访问主页获取初始 cookie
    2. 访问注册页
    3. 获取验证码
    4. 提交注册
    """

    def __init__(self, fingerprint=None):
        import requests
        self.fp = fingerprint or generate_android_fingerprint()
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": self.fp["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": self.fp["accept_language"],
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": self.fp["headers"]["Sec-Ch-Ua"],
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Ch-Ua-Platform-Version": self.fp["headers"]["Sec-Ch-Ua-Platform-Version"],
        })
        self._referer = None

    def _update_referer(self, url):
        """更新 Referer 头模拟真实导航"""
        self._referer = url

    def _get_headers(self, dest="document", mode="navigate", site=None):
        """生成当前请求的 Sec-Fetch 头"""
        h = {}
        h["Sec-Fetch-Dest"] = dest
        h["Sec-Fetch-Mode"] = mode
        h["Sec-Fetch-Site"] = site or ("same-origin" if self._referer else "none")
        h["Sec-Fetch-User"] = "?1"
        if self._referer:
            h["Referer"] = self._referer
        return h

    def warmup(self, main_url="https://www.4399.com"):
        """
        预热会话 — 模拟用户先访问主页再跳转到注册页
        """
        import time
        # 1. 访问主页
        headers = self._get_headers(dest="document", mode="navigate", site="none")
        try:
            r = self.session.get(main_url, headers=headers, timeout=15, allow_redirects=True)
            self._update_referer(main_url)
            time.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass

        # 2. 访问登录页
        login_url = "https://ptlogin.4399.com/ptlogin/login.do"
        headers = self._get_headers(dest="document", mode="navigate", site="same-origin")
        try:
            r = self.session.get(login_url, headers=headers, timeout=15, allow_redirects=True)
            self._update_referer(login_url)
            time.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass

        # 3. 访问注册页
        reg_url = "https://ptlogin.4399.com/ptlogin/register.do"
        headers = self._get_headers(dest="document", mode="navigate", site="same-origin")
        try:
            r = self.session.get(reg_url, headers=headers, timeout=15, allow_redirects=True)
            self._update_referer(reg_url)
            time.sleep(random.uniform(0.3, 0.6))
        except Exception:
            pass

        return self

    def get_captcha(self, session_id):
        """获取验证码图片"""
        import time
        url = f"https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={session_id}"
        headers = self._get_headers(dest="image", mode="no-cors", site="same-origin")
        time.sleep(random.uniform(0.2, 0.5))
        r = self.session.get(url, headers=headers, timeout=10)
        return r.content

    def register(self, username, password, realname, idcard, captcha, session_id):
        """提交注册"""
        import time
        url = "https://ptlogin.4399.com/ptlogin/register.do"
        headers = self._get_headers(dest="document", mode="navigate", site="same-origin")
        headers["Origin"] = "https://ptlogin.4399.com"

        data = {
            'postLoginHandler': 'default', 'displayMode': 'popup', 'appId': 'www_home',
            'gameId': '', 'cid': '', 'externalLogin': 'qq', 'aid': '', 'ref': '',
            'css': '', 'redirectUrl': '', 'regMode': 'reg_normal',
            'sessionId': session_id, 'regIdcard': 'true', 'noEmail': '',
            'crossDomainIFrame': '', 'crossDomainUrl': '',
            'mainDivId': 'popup_reg_div', 'showRegInfo': 'true',
            'includeFcmInfo': 'false', 'expandFcmInput': 'true',
            'fcmFakeValidate': 'false', 'realnameValidate': 'true',
            'username': username, 'password': password, 'passwordveri': password,
            'email': '', 'inputCaptcha': captcha, 'reg_eula_agree': 'on',
            'realname': realname, 'idcard': idcard
        }

        time.sleep(random.uniform(0.3, 0.7))
        r = self.session.post(url, data=data, headers=headers, timeout=15)
        return r

    def get_cookie_dict(self):
        return dict(self.session.cookies)


# ---- 便捷函数 ----
def get_ua():
    """只返回一个随机 Android UA"""
    return generate_android_fingerprint()["user_agent"]


def get_headers():
    """返回完整的 Android 浏览器请求头"""
    return generate_android_fingerprint()["headers"]


if __name__ == "__main__":
    # 测试输出
    for _ in range(3):
        fp = generate_android_fingerprint()
        print(f"[{fp['brand']}] {fp['name']} | Android {fp['android_version']} | Chrome {fp['chrome_version']}")
        print(f"  UA: {fp['user_agent'][:90]}...")
        print(f"  Lang: {fp['accept_language']}")
        print()

    # 测试会话
    print("=" * 60)
    print("测试真实浏览器会话...")
    browser = RealisticBrowserSession()
    print(f"设备: {browser.fp['brand']} {browser.fp['name']}")
    browser.warmup()
    print(f"预热后 Cookie: {browser.get_cookie_dict()}")
