"""
批量运行 SakuraBot 登录所有账号
"""
import subprocess
import sys
import os
import time

sys.stdout.reconfigure(encoding='utf-8')

ACCOUNTS_FILE = "./accounts.txt"
OUTPUT_FILE = "./sakura_output.txt"
SAKURA_DIR = r"C:\Users\L\Desktop\4399AccountRegister-main\cookie"
PROJECT_ROOT = r"C:\Users\L\Desktop\4399AccountRegister-main"

# 确保 Cheese.Ocr4399.exe 在 PATH 中
env = os.environ.copy()
env['PATH'] = PROJECT_ROOT + ';' + env.get('PATH', '')

# 加载账号
accounts = []
with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if ":" in line:
            u, p = line.split(":", 1)
            accounts.append((u, p))

print(f"加载 {len(accounts)} 个账号")
print(f"开始批量登录...\n")
print("="*60)

success = 0
fail = 0
results = []

for i, (username, password) in enumerate(accounts, 1):
    print(f"\n[{i}/{len(accounts)}] {username}")
    start = time.time()
    try:
        result = subprocess.run(
            ['java', '-cp', '.', 'net.nekocurit.i4399.Demo', username, password],
            capture_output=True, timeout=60, cwd=SAKURA_DIR, env=env
        )
        elapsed = time.time() - start
        text = result.stdout.decode('gbk', errors='replace').strip()

        if text.startswith('Error:'):
            fail += 1
            error_msg = text.replace('Error: ', '')
            print(f"  ✗ 失败: {error_msg} ({elapsed:.1f}s)")
            results.append(f"{username}:{password} -> FAIL: {error_msg}")
        else:
            # 成功 - 输出格式: uid + wrappedCookie
            success += 1
            print(f"  ✓ 成功! ({elapsed:.1f}s)")
            print(f"  输出: {text[:100]}...")
            results.append(f"{username}:{password} -> OK: {text}")
    except subprocess.TimeoutExpired:
        fail += 1
        print(f"  ✗ 超时 (60s)")
        results.append(f"{username}:{password} -> TIMEOUT")
    except Exception as e:
        fail += 1
        print(f"  ✗ 异常: {e}")
        results.append(f"{username}:{password} -> ERROR: {e}")

# 保存结果
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write('\n'.join(results))

print(f"\n{'='*60}")
print(f"批量登录完成!")
print(f"  总计: {len(accounts)}")
print(f"  成功: {success}")
print(f"  失败: {fail}")
print(f"  结果保存至: {OUTPUT_FILE}")
print(f"{'='*60}")
