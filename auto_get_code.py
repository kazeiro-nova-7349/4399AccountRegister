"""
自动获取邮箱验证码
用法:
  python auto_get_code.py                    # 自动生成邮箱并等待
  python auto_get_code.py myprefix@v2proxy.com  # 指定邮箱
"""
import requests
import time
import re
import sys

API_BASE = "https://api.temporam.com/v1"
TOKEN = "tm_UfIwItCE8z8l7b28n9J03-BuWegJacZq"
headers = {"Authorization": f"Bearer {TOKEN}"}

def get_domains():
    r = requests.get(f"{API_BASE}/domains", headers=headers)
    return [x["domain"] for x in r.json()["data"]]

def gen_email():
    domains = get_domains()
    prefix = f"usr{int(time.time()) % 1000000}"
    return f"{prefix}@{domains[0]}"

def get_emails(email):
    r = requests.get(f"{API_BASE}/emails", headers=headers, params={"email": email})
    return r.json().get("data", [])

def extract_code(text):
    # GitHub: 6位数字
    m = re.search(r"\b(\d{6})\b", text)
    if m:
        return m.group(1)
    # 通用: 6-8位
    m = re.search(r"\b(\d{6,8})\b", text)
    if m:
        return m.group(1)
    return None

def wait_for_code(email, timeout=180, keyword=None):
    print(f"[{time.strftime('%H:%M:%S')}] 等待 {email} 的验证码...")
    deadline = time.time() + timeout
    seen_ids = set()
    while time.time() < deadline:
        emails = get_emails(email)
        for e in emails:
            eid = e.get("id")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)
            text = e.get("summary", "") + " " + e.get("subject", "")
            if keyword and keyword.lower() not in text.lower():
                continue
            code = extract_code(text)
            if code:
                print(f"\n[{time.strftime('%H:%M:%S')}] 收到邮件:")
                print(f"  来自: {e.get('from_email', 'N/A')}")
                print(f"  主题: {e.get('subject', 'N/A')}")
                print(f"  验证码: {code}")
                return code
        time.sleep(3)
    print("超时")
    return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = gen_email()
        print(f"自动生成邮箱: {email}")

    print(f"\n请将此邮箱填入注册页面，然后等待...")
    print("-" * 50)
    code = wait_for_code(email)
    if code:
        print(f"\n最终验证码: {code}")
    else:
        print("\n未收到验证码")
