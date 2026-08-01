# -*- coding: utf-8 -*-
"""
批量注册 50 个号，结果保存到桌面
模拟真实 Android 浏览器 + AES 加密提交
"""
import sys
import os
import hashlib
import base64
sys.stdout.reconfigure(encoding='utf-8')

from random import choice
from string import ascii_lowercase, digits
from time import sleep, time
from curl_cffi import requests
from ddddocr import DdddOcr
from fingerprint import generate_android_fingerprint
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ---- AES 加密 (匹配 CryptoJS.AES.encrypt) ----
AES_KEY = 'lzYW5qaXVqa'

def cryptojs_aes_encrypt(plaintext, passphrase=AES_KEY):
    """模拟 CryptoJS.AES.encrypt(plaintext, passphrase).toString()"""
    salt = os.urandom(8)
    key_iv = b''
    prev = b''
    while len(key_iv) < 48:
        prev = hashlib.md5(prev + passphrase.encode() + salt).digest()
        key_iv += prev
    key = key_iv[:32]
    iv = key_iv[32:48]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext.encode('utf-8'), AES.block_size)
    ciphertext = cipher.encrypt(padded)
    result = b'Salted__' + salt + ciphertext
    return base64.b64encode(result).decode('utf-8')


# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings()

# 初始化 OCR
ocr = DdddOcr(use_gpu=True, show_ad=False,
              import_onnx_path="4399ocr/4399ocr.onnx",
              charsets_path="4399ocr/4399ocr.json")

# 读取身份证
with open("sfz2.txt", "r", encoding="utf-8") as f:
    sfz_lines = [l.strip() for l in f if l.strip()]

TARGET = 50
FIXED_PASSWORD = "123456"
DEVICE_ROTATION_INTERVAL = 10

# 轮换设备状态
current_fp = generate_android_fingerprint()
fp_counter = 0

results = []
success = 0
fail = 0
fail_reasons = {}

start = time()

print(f"开始批量注册 {TARGET} 个号...")
print(f"AES 密钥: {AES_KEY}")
print(f"目标: 桌面/49333_accounts.txt")
print("=" * 60)

for i in range(1, TARGET + 1):
    # 轮换设备
    if fp_counter >= DEVICE_ROTATION_INTERVAL:
        current_fp = generate_android_fingerprint()
        fp_counter = 0
        print(f"\n[换设备] {current_fp['brand']} {current_fp['name']} (Android {current_fp['android_version']})")
    fp_counter += 1

    # 生成账号
    usr = ''.join(choice(ascii_lowercase + digits) for _ in range(9))
    pwd = FIXED_PASSWORD

    # 身份信息
    sfz = choice(sfz_lines).split('----')
    realname, idcard = sfz[0], sfz[1]

    try:
        # 创建会话
        s = requests.Session()
        s.verify = False
        s.headers.update(current_fp['headers'])

        # 预热: 访问主页
        s.get('https://www.4399.com', impersonate='chrome120', timeout=15)
        sleep(0.5)

        # 获取验证码
        sessionId = 'captchaReq' + ''.join(choice(ascii_lowercase + digits) for _ in range(19))
        sleep(0.3)

        captcha_resp = s.get(
            f'https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={sessionId}',
            impersonate='chrome120', timeout=10
        )
        captcha = ocr.classification(captcha_resp.content)

        sleep(0.4)

        # AES 加密敏感字段
        encrypted_pwd = cryptojs_aes_encrypt(pwd)
        encrypted_pwd_veri = cryptojs_aes_encrypt(pwd)
        encrypted_name = cryptojs_aes_encrypt(realname)
        encrypted_idcard = cryptojs_aes_encrypt(idcard)

        # 注册提交 (加密字段)
        data = {
            'postLoginHandler': 'default',
            'displayMode': 'popup',
            'appId': 'www_home',
            'gameId': '',
            'cid': '',
            'externalLogin': 'qq',
            'aid': '',
            'ref': '',
            'css': '',
            'redirectUrl': '',
            'regMode': 'reg_normal',
            'sessionId': sessionId,
            'regIdcard': 'true',
            'noEmail': '',
            'crossDomainIFrame': '',
            'crossDomainUrl': '',
            'mainDivId': 'popup_reg_div',
            'showRegInfo': 'true',
            'includeFcmInfo': 'false',
            'expandFcmInput': 'true',
            'fcmFakeValidate': 'false',
            'realnameValidate': 'true',
            'username': usr,
            'password': encrypted_pwd,
            'passwordveri': encrypted_pwd_veri,
            'email': '',
            'inputCaptcha': captcha,
            'reg_eula_agree': 'on',
            'realname': encrypted_name,
            'idcard': encrypted_idcard,
        }

        resp = s.post(
            'https://ptlogin.4399.com/ptlogin/register.do',
            data=data, impersonate='chrome120', timeout=15
        )
        text = resp.text

        if '注册成功' in text:
            success += 1
            status = 'OK'
            results.append(f"{usr}:{pwd}")
        elif '验证码错误' in text:
            fail += 1
            status = '验证码错误'
            fail_reasons['验证码错误'] = fail_reasons.get('验证码错误', 0) + 1
        elif '身份证实名账号数量超过限制' in text:
            fail += 1
            status = '身份证超限'
            fail_reasons['身份证超限'] = fail_reasons.get('身份证超限', 0) + 1
        elif '用户名已被注册' in text:
            fail += 1
            status = '用户名已存在'
            fail_reasons['用户名已存在'] = fail_reasons.get('用户名已存在', 0) + 1
        elif '请稍后再试' in text:
            fail += 1
            status = '反爬拦截(202)'
            fail_reasons['反爬拦截'] = fail_reasons.get('反爬拦截', 0) + 1
            sleep(3)
        else:
            fail += 1
            status = f'未知({resp.status_code})'
            fail_reasons[status] = fail_reasons.get(status, 0) + 1

    except Exception as e:
        fail += 1
        status = f'异常:{type(e).__name__}'
        fail_reasons[status] = fail_reasons.get(status, 0) + 1

    elapsed = time() - start
    print(f"[{i:2d}/{TARGET}] {usr} | {status} | 成功:{success} 失败:{fail} | {elapsed:.0f}s")

# 保存结果到桌面
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
out_path = os.path.join(desktop, "49333_accounts.txt")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"# 4399 批量注册结果\n")
    f.write(f"# 总数: {TARGET} | 成功: {success} | 失败: {fail}\n")
    f.write(f"# 密码: {FIXED_PASSWORD}\n")
    f.write(f"# 时间: {time()}\n\n")
    for line in results:
        f.write(line + "\n")

print("\n" + "=" * 60)
print(f"完成! 成功 {success}/{TARGET}")
print(f"失败原因: {fail_reasons}")
print(f"结果已保存: {out_path}")
