# -*- coding: utf-8 -*-
from collections import Counter, deque
from random import choice, sample, uniform
from string import ascii_letters, ascii_lowercase, digits
from threading import Lock, Thread
from time import sleep, time
import msvcrt
from ddddocr import DdddOcr
import requests
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY, ROUNDED
from dotenv import load_dotenv
import os
from fingerprint import generate_android_fingerprint

load_dotenv()

# 全局统计计数器
counts = Counter()
failure_details = Counter()
proxy_stats = Counter()

# 共享数据存储
shared_data = {
    'success_times': deque(maxlen=10000),  # 限制队列长度防止内存溢出
    'is_paused': False,
    'pause_start_time': 0,
    'total_paused_time': 0
}

# 线程锁
shared_data_lock = Lock()
proxy_lock = Lock()

# 全局变量
proxy_index = 0
start_time = time()
console = Console()

# 设备指纹轮换 (每 N 个号换一次设备)
DEVICE_ROTATION_INTERVAL = 10
current_device_fp = generate_android_fingerprint()
device_account_count = 0
device_lock = Lock()

# 字符集定义
strings = ascii_letters + digits
captcha_strings = ascii_lowercase + digits

# 从环境变量读取配置
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
PROXY = os.getenv('PROXY', '')
PROXY_FILE = os.getenv('PROXY_FILE', 'proxies.txt')
PROXY_API = os.getenv('PROXY_API', '')
PROXY_REFRESH_INTERVAL = int(os.getenv('PROXY_REFRESH_INTERVAL', '300'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '15'))
REQUEST_RETRY = int(os.getenv('REQUEST_RETRY', '2'))
CAPTCHA_TIMEOUT = int(os.getenv('CAPTCHA_TIMEOUT', '8'))
REGISTER_TIMEOUT = int(os.getenv('REGISTER_TIMEOUT', '15'))
SFZ_FILE = os.getenv('SFZ_FILE', 'sfz.txt')
OCR_FOLDER = os.getenv('OCR_FOLDER', '4399ocr')
SYMBOL = os.getenv('SYMBOL', '')
THREADS = int(os.getenv('THREADS', '30'))
CAPTCHA_RETRY = int(os.getenv('CAPTCHA_RETRY', '4'))

# 新增配置项
ACCOUNT_FORMAT = int(os.getenv('ACCOUNT_FORMAT', '3'))  # 1:全数字, 2:全英文, 3:数字加英文
PASSWORD_MODE = os.getenv('PASSWORD_MODE', 'random')   # fixed:固定密码, random:随机密码
FIXED_PASSWORD = os.getenv('FIXED_PASSWORD', '123456') # 固定密码

# 请求头 (动态生成 Android 指纹)
def build_headers():
    """每次调用生成新的 Android 设备指纹请求头"""
    fp = generate_android_fingerprint()
    return fp['headers']

# 默认请求头（首次加载用）
headers = build_headers()

# 代理池相关变量
proxy_list = []
proxy_fail_count = {}       # 记录代理失败次数
proxy_last_used_time = {}   # 记录代理上次使用时间
proxy_cooldown_until = {}   # 429/503等错误的冷却截止时间
last_proxy_refresh_time = 0

def load_proxies_from_file():
    """从文件加载代理"""
    proxies = []
    if os.path.exists(PROXY_FILE):
        try:
            with open(PROXY_FILE, 'r', encoding='utf-8') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except Exception as e:
            console.print(f"[yellow]警告: 无法读取代理文件 {PROXY_FILE}: {e}[/yellow]")
    return proxies

def test_proxy(proxy):
    """测试代理是否可用(测试4399验证码接口)"""
    try:
        test_url = 'https://ptlogin.4399.com/ptlogin/captcha.do?captchaId=testReq12345'
        proxy_dict = {'http': proxy, 'https': proxy}
        response = requests.get(test_url, proxies=proxy_dict, timeout=8, verify=False)
        return response.status_code == 200 and len(response.content) > 1000
    except Exception as e:
        if 'socks' in proxy.lower():
            console.print(f"[dim red]SOCKS5测试失败 {proxy}: {type(e).__name__}[/dim red]")
        return False

def fetch_proxies_from_api():
    """从API获取代理列表"""
    if not PROXY_API:
        console.print("[red]PROXY_API 未配置[/red]")
        return []
    
    try:
        console.print(f"[cyan]正在从API获取代理: {PROXY_API}[/cyan]")
        response = requests.get(PROXY_API, timeout=10)
        console.print(f"[cyan]API响应状态: {response.status_code}[/cyan]")
        
        if response.status_code == 200:
            proxies = []
            seen = set()
            
            raw_text = response.text.strip()
            console.print(f"[cyan]API原始返回(前200字符):\n{raw_text[:200]}[/cyan]")
            
            for line in raw_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 自动添加协议前缀
                    if not line.startswith('http://') and not line.startswith('https://') and not line.startswith('socks'):
                        line = 'http://' + line
                    
                    if line not in seen:
                        proxies.append(line)
                        seen.add(line)
            
            if proxies:
                console.print(f"[green]跳过测试,直接加载 {len(proxies)} 个代理[/green]")
                return proxies
            else:
                console.print("[red]解析后代理列表为空[/red]")
            
            return proxies
    except Exception as e:
        console.print(f"[red]代理API获取失败: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
    
    return []

def refresh_proxy_list():
    """刷新代理列表"""
    global proxy_list, last_proxy_refresh_time
    
    new_proxies = []
    
    # 优先从API获取
    if PROXY_API:
        new_proxies = fetch_proxies_from_api()
        if new_proxies:
            console.print(f"[green]从API获取到 {len(new_proxies)} 个代理IP[/green]")
            proxy_stats['refresh_count'] += 1
    
    # 如果API没有返回，尝试从文件加载
    if not new_proxies:
        new_proxies = load_proxies_from_file()
        if new_proxies:
            console.print(f"[green]从文件加载 {len(new_proxies)} 个代理IP[/green]")
    
    # 如果都没有，使用单个代理
    if not new_proxies and PROXY:
        new_proxies = [PROXY]
        console.print(f"[green]使用单个代理[/green]")
    
    with proxy_lock:
        proxy_list = new_proxies
        last_proxy_refresh_time = time()
    
    return len(new_proxies)

def check_and_refresh_proxies():
    """检查并刷新代理（如果需要）"""
    global last_proxy_refresh_time
    
    # 可用代理不足时主动刷新
    available_count = sum(1 for p in proxy_list 
                         if proxy_fail_count.get(p, 0) < 8 
                         and proxy_cooldown_until.get(p, 0) <= time())
    
    # IP有效期较短,需更频繁更新
    if PROXY_API and ((time() - last_proxy_refresh_time) >= PROXY_REFRESH_INTERVAL or available_count < 5):
        refresh_proxy_list()

# 初始加载代理
refresh_proxy_list()

proxies = {
    "http": PROXY,
    "https": PROXY
} if PROXY else None

# 加载OCR和身份证数据
try:
    ocr = DdddOcr(use_gpu=True, show_ad=False, 
                  import_onnx_path=f"{OCR_FOLDER}/4399ocr.onnx",
                  charsets_path=f"{OCR_FOLDER}/4399ocr.json")
    with open(SFZ_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except FileNotFoundError as e:
    console.print(f"[bold red]错误: 缺少必要文件: {e.filename}，请确保它在程序目录下。[/bold red]")
    exit()

def randstr(chars, length):
    """生成指定长度的随机字符串"""
    return ''.join(sample(chars, length))

def get_account_charset():
    """根据配置获取账号字符集"""
    if ACCOUNT_FORMAT == 1:
        return digits, "全数字"
    elif ACCOUNT_FORMAT == 2:
        return ascii_lowercase, "全英文"
    elif ACCOUNT_FORMAT == 3:
        return ascii_lowercase + digits, "数字加英文"
    else:
        return ascii_lowercase + digits, "数字加英文(默认)"

def get_next_proxy():
    """轮询获取下一个代理(智能跳过失败代理,带冷却与限频)"""
    global proxy_index
    if not proxy_list:
        return None

    now = time()
    cool_down = 1  # 同一代理最短使用间隔(秒)

    with proxy_lock:
        # 尝试最多找len(proxy_list)个代理,跳过失败次数过多或在冷却期内/刚用过的
        for _ in range(len(proxy_list)):
            proxy = proxy_list[proxy_index % len(proxy_list)]
            proxy_index += 1

            # 失败次数过多,跳过
            if proxy_fail_count.get(proxy, 0) >= 8:
                continue

            # 处于冷却期(例如429/503后),跳过
            if proxy_cooldown_until.get(proxy, 0) > now:
                continue

            # 距离上次使用时间太短,跳过(限频)
            last_used = proxy_last_used_time.get(proxy, 0)
            if now - last_used < cool_down:
                continue

            proxy_last_used_time[proxy] = now
            proxy_stats['total_switches'] += 1
            proxy_stats['current_proxy'] = proxy
            return {
                "http": proxy,
                "https": proxy
            }

        # 如果一圈下来都没找到合适的代理,尝试再选一个未在冷却期且失败分较低的
        candidates = [
            p for p in proxy_list
            if proxy_fail_count.get(p, 0) < 8 and proxy_cooldown_until.get(p, 0) <= now
        ]
        if not candidates:
            # 所有代理都在冷却或失败过多,暂时不使用代理,由调用方决定等待
            return None

        # 简单选择失败次数最少的一个
        proxy = min(candidates, key=lambda p: proxy_fail_count.get(p, 0))

        proxy_last_used_time[proxy] = now
        proxy_stats['total_switches'] += 1
        proxy_stats['current_proxy'] = proxy

    return {
        "http": proxy,
        "https": proxy
    }

def handle_input():
    """处理键盘输入"""
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b' ':
                toggle_pause()
        sleep(0.1)

def toggle_pause():
    """切换暂停状态"""
    with shared_data_lock:
        shared_data['is_paused'] = not shared_data['is_paused']
        if shared_data['is_paused']:
            shared_data['pause_start_time'] = time()
        else:
            paused_duration = time() - shared_data['pause_start_time']
            shared_data['total_paused_time'] += paused_duration

def get_elapsed_time():
    """获取运行时间"""
    with shared_data_lock:
        total_paused_time = shared_data['total_paused_time']
        is_paused = shared_data['is_paused']
        pause_start_time = shared_data['pause_start_time']

    current_paused_duration = 0
    if is_paused:
        current_paused_duration = time() - pause_start_time

    elapsed = time() - start_time - total_paused_time - current_paused_duration
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

def register_4399(usr, pwd, count=1, retry_count=0):
    """注册4399账号(带重试机制)"""
    current_proxy = None
    try:
        # 优先使用代理池,否则使用单个代理
        current_proxy = get_next_proxy() if proxy_list else proxies

        # 代理池存在但当前无可用代理时,直接返回,避免无效请求
        if proxy_list and current_proxy is None:
            sleep(1)
            return "网络异常_无可用代理"

        # 每 DEVICE_ROTATION_INTERVAL 个号更换一次设备指纹
        global current_device_fp, device_account_count
        with device_lock:
            if device_account_count >= DEVICE_ROTATION_INTERVAL:
                current_device_fp = generate_android_fingerprint()
                device_account_count = 0
            device_account_count += 1
            req_headers = current_device_fp['headers']

        sfz = choice(lines).strip()
        sfz_split = sfz.split('----')

        sessionId = 'captchaReq' + randstr(captcha_strings, 19)

        # 随机打散请求节奏,降低同IP瞬时并发
        sleep(uniform(0.1, 0.3))

        # 获取验证码(优化:单次请求,失败直接换代理)
        captcha_response = requests.get(
            f'https://ptlogin.4399.com/ptlogin/captcha.do?captchaId={sessionId}',
            headers=req_headers,
            proxies=current_proxy,
            verify=False,
            timeout=CAPTCHA_TIMEOUT
        ).content

        captcha = ocr.classification(captcha_response)

        # 提交注册前再加入轻微抖动
        sleep(uniform(0.1, 0.4))

        data = {
            'postLoginHandler': 'default', 'displayMode': 'popup', 'appId': 'www_home', 'gameId': '', 'cid': '',
            'externalLogin': 'qq', 'aid': '', 'ref': '', 'css': '', 'redirectUrl': '', 'regMode': 'reg_normal',
            'sessionId': sessionId, 'regIdcard': 'true', 'noEmail': '', 'crossDomainIFrame': '', 'crossDomainUrl': '',
            'mainDivId': 'popup_reg_div', 'showRegInfo': 'true', 'includeFcmInfo': 'false', 'expandFcmInput': 'true',
            'fcmFakeValidate': 'false', 'realnameValidate': 'true', 'username': usr, 'password': pwd,
            'passwordveri': pwd, 'email': '', 'inputCaptcha': captcha, 'reg_eula_agree': 'on',
            'realname': sfz_split[0], 'idcard': sfz_split[1]
        }

        response = requests.post(
            'https://ptlogin.4399.com/ptlogin/register.do',
            data=data,
            proxies=current_proxy,
            headers=req_headers,
            verify=False,
            timeout=REGISTER_TIMEOUT
        )
        response_text = response.text
        status_code = response.status_code

        if '注册成功' in response_text:
            result = '生产成功'
            # 成功则重置该代理失败计数
            if current_proxy and proxy_list:
                proxy_key = current_proxy.get('http', '')
                proxy_fail_count[proxy_key] = 0
            with open('accounts.log', 'a') as f:
                f.write(f'{usr}:{pwd}\n')
        elif '验证码错误' in response_text:
            if count >= CAPTCHA_RETRY:
                result = "菠萝码超时"
            else:
                return register_4399(usr, pwd, count + 1, retry_count)
        elif '身份证实名账号数量超过限制' in response_text: 
            result = '菠萝证种植数量超过限制'
        elif '身份证实名过于频繁' in response_text: 
            result = '菠萝证种植过于频繁'
        elif '该姓名身份证提交验证过于频繁' in response_text: 
            result = '该菠萝人的菠萝证种植过于频繁'
        elif '您的身份证异常或错误' in response_text: 
            result = '您的菠萝证异常或错误'
        elif '姓名身份证不匹配' in response_text: 
            result = '菠萝名与菠萝号不匹配'
        elif '用户名包含敏感字符' in response_text: 
            result = '菠萝名包含敏感字符'
        elif '身份证实名账号数量超过时段限制' in response_text: 
            result = '菠萝证种植数量超过时段限制'
        elif '用户名已被注册' in response_text: 
            result = '该菠萝已被生产'
        else:
            if status_code == 200:
                with open("error200.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                result = "未知错误_200"
            else:
                # 针对不同状态码做更精细的处理
                if current_proxy and proxy_list:
                    proxy_key = current_proxy.get('http', '')

                    # 429 视为限流,增加失败分并设置冷却时间
                    if status_code == 429:
                        fail = proxy_fail_count.get(proxy_key, 0) + 1
                        proxy_fail_count[proxy_key] = fail
                        # 冷却时间: 15, 30, 60...秒, 上限300s
                        cooldown = min(300, 15 * (2 ** (fail - 1)))
                        proxy_cooldown_until[proxy_key] = time() + cooldown
                        result = "网络错误_429"

                    # 503 多为服务端过载,轻度打分+固定冷却
                    elif status_code == 503:
                        proxy_fail_count[proxy_key] = proxy_fail_count.get(proxy_key, 0) + 1
                        proxy_cooldown_until[proxy_key] = time() + 30
                        result = "网络错误_503"

                    # 其他 4xx/5xx 维持原逻辑,只做失败计数
                    else:
                        proxy_fail_count[proxy_key] = proxy_fail_count.get(proxy_key, 0) + 1
                        result = f"网络错误_{response.status_code}"
                else:
                    result = f"网络错误_{response.status_code}"
        
        return result

    except requests.exceptions.ProxyError:
        # 代理错误,标记并换代理重试
        if current_proxy and proxy_list:
            proxy_key = current_proxy.get('http', '')
            proxy_fail_count[proxy_key] = proxy_fail_count.get(proxy_key, 0) + 2
            # 代理错误,给一个短暂冷却,避免瞬间重复踩雷
            proxy_cooldown_until[proxy_key] = time() + 20
        if retry_count < REQUEST_RETRY and proxy_list:
            return register_4399(usr, pwd, count, retry_count + 1)
        return "网络异常_ProxyError"
    except requests.exceptions.Timeout:
        # 超时,标记代理并重试
        if current_proxy and proxy_list:
            proxy_key = current_proxy.get('http', '')
            proxy_fail_count[proxy_key] = proxy_fail_count.get(proxy_key, 0) + 1
            proxy_cooldown_until[proxy_key] = time() + 10
        if retry_count < 1:
            return register_4399(usr, pwd, count, retry_count + 1)
        return "网络异常_Timeout"
    except requests.exceptions.ConnectionError:
        # 连接错误,标记代理并重试
        if current_proxy and proxy_list:
            proxy_key = current_proxy.get('http', '')
            proxy_fail_count[proxy_key] = proxy_fail_count.get(proxy_key, 0) + 2
            proxy_cooldown_until[proxy_key] = time() + 20
        if retry_count < REQUEST_RETRY and proxy_list:
            return register_4399(usr, pwd, count, retry_count + 1)
        return "网络异常_ConnectionError"
    except Exception as e:
        # 其他异常,换代理重试一次
        if retry_count < 1 and proxy_list:
            return register_4399(usr, pwd, count, retry_count + 1)
        error_type = type(e).__name__
        return f"网络异常_{error_type}"

def worker():
    """工作线程函数"""
    # 获取账号字符集
    account_charset, _ = get_account_charset()
    
    while True:
        # 定时检查并刷新代理
        check_and_refresh_proxies()
        
        with shared_data_lock:
            is_paused = shared_data['is_paused']
        
        if is_paused:
            sleep(0.5)
            continue

        # 根据账号格式生成相应类型的账号
        if ACCOUNT_FORMAT == 1:  # 全数字
            account_body = randstr(digits, 9)
        elif ACCOUNT_FORMAT == 2:  # 全英文(小写)
            account_body = randstr(ascii_lowercase, 9)
        else:  # 数字加英文(小写)
            account_body = randstr(ascii_lowercase + digits, 9)
            
        # 如果设置了前缀，则添加前缀
        if SYMBOL:
            usr = SYMBOL + account_body
        else:
            usr = account_body
        
        # 生成密码
        if PASSWORD_MODE == 'fixed':
            pwd = FIXED_PASSWORD
        else:
            pwd = randstr(ascii_letters + digits, 12)
        
        result = register_4399(usr, pwd)
        
        with shared_data_lock:
            if shared_data['is_paused']:
                continue
            
            counts['total'] += 1
            if result == '生产成功':
                counts['success'] += 1
                current_active_time = time() - start_time - shared_data['total_paused_time']
                shared_data['success_times'].append(current_active_time)
            else:
                counts['failure'] += 1
                failure_details[result] += 1

def make_header() -> Panel:
    """创建头部面板"""
    with shared_data_lock:
        is_paused = shared_data['is_paused']

    # 获取账号格式和密码模式信息
    _, account_format_desc = get_account_charset()
    password_mode_desc = "固定密码" if PASSWORD_MODE == 'fixed' else "随机密码"

    # 显示当前设备指纹
    title = Text("Pineapple Register", justify="center", style="bold cyan")

    if is_paused:
        pause_text = Text(" [ PAUSED ]", style="bold yellow")
        title.append(pause_text)

    # 显示设备指纹与剩余号数
    remaining = DEVICE_ROTATION_INTERVAL - device_account_count
    device_text = Text(
        f" | 📱 {current_device_fp['brand']} {current_device_fp['name']} "
        f"(Android {current_device_fp['android_version']}) | 剩余 {remaining} 号换设备",
        style="bold magenta"
    )
    title.append(device_text)

    # 显示代理信息
    current_proxy = proxy_stats.get('current_proxy', '直连')
    proxy_text = Text(f" | 代理: {current_proxy}", style="bold green")
    title.append(proxy_text)

    # 显示账号格式和密码模式
    config_text = Text(f" | 账号: {account_format_desc} | 密码: {password_mode_desc}", style="bold blue")
    title.append(config_text)

    return Panel(title, box=HEAVY, border_style="bright_blue")

def make_stats_panel() -> Panel:
    """创建统计面板"""
    total = counts['total']
    success = counts['success']
    failure = counts['failure']
    
    with shared_data_lock:
        success_times_copy = shared_data['success_times'].copy()
        is_paused = shared_data['is_paused']
        pause_start_time = shared_data['pause_start_time']
        total_paused_time = shared_data['total_paused_time']

    success_rate = (success / total * 100) if total > 0 else 0

    current_paused_duration = 0
    if is_paused:
        current_paused_duration = time() - pause_start_time
    
    current_active_time = time() - start_time - total_paused_time - current_paused_duration

    while success_times_copy and success_times_copy[0] < current_active_time - 60:
        success_times_copy.popleft()
    spm = len(success_times_copy)
    
    # 获取代理统计
    proxy_switches = proxy_stats.get('total_switches', 0)
    proxy_refreshes = proxy_stats.get('refresh_count', 0)
    proxy_count = len(proxy_list) if proxy_list else 0

    stats_table = Table.grid(expand=True, padding=(0, 1))
    stats_table.add_column(style="bright_cyan", justify="right")
    stats_table.add_column(style="bold bright_magenta", justify="left")
    stats_table.add_row("总尝试", f"{total}")
    stats_table.add_row("[green]生产成功[/green]", f"[green]{success}[/green]")
    stats_table.add_row("[red]生产失败[/red]", f"[red]{failure}[/red]")
    stats_table.add_row("SPM", f"{spm} / min")
    stats_table.add_row("[blue]代理池[/blue]", f"[blue]{proxy_count} 个[/blue]")
    stats_table.add_row("[blue]切换次数[/blue]", f"[blue]{proxy_switches}[/blue]")
    stats_table.add_row("[blue]刷新次数[/blue]", f"[blue]{proxy_refreshes}[/blue]")

    success_progress = Progress(
        TextColumn("成功率", style="bright_cyan"),
        BarColumn(bar_width=None, complete_style="bright_green"),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        expand=True
    )
    success_progress.add_task("rate", completed=success_rate)

    content_group = Group(
        stats_table,
        Rule(style="dim blue"),
        success_progress
    )

    return Panel(content_group, title="[bold yellow]核心统计[/bold yellow]", border_style="bright_yellow")

def make_failure_panel() -> Panel:
    """创建失败分析面板"""
    failure = counts['failure']
    sorted_failures = failure_details.most_common(10)

    reasons_table = Table(show_edge=True, title_style="bold bright_red", expand=True, box=ROUNDED)
    reasons_table.add_column("原因", style="bright_red", no_wrap=True, ratio=60)
    reasons_table.add_column("数量", style="bright_cyan", ratio=20, justify="center")
    reasons_table.add_column("占比", style="bright_magenta", ratio=20, justify="center")

    if failure > 0:
        for reason, count in sorted_failures:
            percentage = (count / failure * 100)
            reasons_table.add_row(reason, str(count), f"{percentage:.1f}%")

    return Panel(reasons_table, title="[bold red]失败分析[/bold red]", border_style="bright_red")

def make_footer() -> Align:
    """创建底部面板"""
    with shared_data_lock:
        proxy_count = len(proxy_list) if proxy_list else 0

    proxy_info = f" | 可用代理: {proxy_count}" if proxy_count > 0 else ""

    return Align.center(
        Text(f"运行时长: {get_elapsed_time()}{proxy_info} | 按 空格键 暂停/继续 | 按 Ctrl+C 停止", style="bold dim")
    )

def generate_layout() -> Layout:
    """生成布局"""
    layout = Layout(name="root")

    layout.split(
        Layout(make_header(), name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(make_footer(), name="footer", size=1)
    )

    layout["main"].split_row(
        Layout(make_stats_panel(), name="side"),
        Layout(make_failure_panel(), name="body", ratio=2)
    )
    return layout

def main():
    """主函数"""
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    
    # 显示配置信息
    _, account_format_desc = get_account_charset()
    password_mode_desc = "固定密码" if PASSWORD_MODE == 'fixed' else "随机密码"

    console.print(f"[cyan]账号格式: {account_format_desc}[/cyan]")
    console.print(f"[cyan]密码模式: {password_mode_desc}[/cyan]")
    if PASSWORD_MODE == 'fixed':
        console.print(f"[cyan]固定密码: {FIXED_PASSWORD}[/cyan]")
    
    console.print(f"[cyan]线程数: {THREADS}[/cyan]")
    console.print(f"[cyan]验证码重试次数: {CAPTCHA_RETRY}[/cyan]")
    
    if proxy_list:
        console.print(f"[green]初始代理池大小: {len(proxy_list)}[/green]")
    else:
        console.print("[red]警告: 没有可用的代理[/red]")

    input_thread = Thread(target=handle_input, daemon=True)
    input_thread.start()

    for i in range(THREADS):
        thread = Thread(target=worker, daemon=True)
        thread.start()

    try:
        with Live(generate_layout(), screen=True, redirect_stderr=False, refresh_per_second=4) as live:
            was_paused = False
            while True:
                with shared_data_lock:
                    is_paused = shared_data['is_paused']
                
                if not is_paused or (is_paused and not was_paused):
                    live.update(generate_layout())
                
                was_paused = is_paused
                sleep(0.25)
    except KeyboardInterrupt:
        console.print("\n[bold green]程序已停止。[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]发生意外错误: {e}[/bold red]")
        console.print_exception()

if __name__ == "__main__":
    main()