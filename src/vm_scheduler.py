#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 VM Scheduler - 虚拟机调度主控程序
 =============================================================================
 功能：GitHub虚拟机 + 4399注册任务的并发调度管理器
 运行：python vm_scheduler.py
 说明：纯控制台CLI程序，无GUI，多进程并发，带异常自愈机制
 ==============================================================================
"""

import os
import sys
import json
import time
import random
import signal
import multiprocessing
from multiprocessing import Process, Queue, Event
from pathlib import Path


# ===========================================================================
# 模块一：配置管理 — 负责config.json的读写与持久化
# ===========================================================================
class ConfigManager:
    """配置管理器：加载、保存、读取、修改配置项"""

    # 默认配置（首次运行时自动生成）
    DEFAULT_CONFIG = {
        "target_count": 50,            # 4399目标注册总数量
        "max_concurrency": 5,          # 最大并发虚拟机数量
        "run_duration_minutes": 60,    # 默认运行时长（分钟）
        "identities_dir": "./identities"  # 身份文件存放目录
    }

    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置管理器
        :param config_path: 配置文件路径，默认程序同目录下config.json
        """
        self.config_path = config_path
        self.config = {}
        self.load()

    def load(self):
        """加载配置文件，不存在则创建默认配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                # 补全缺失的默认字段
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in self.config:
                        self.config[key] = value
                return
            except (json.JSONDecodeError, IOError):
                print(f"[警告] 配置文件损坏，使用默认配置")
        # 不存在或损坏时使用默认配置
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()

    def save(self):
        """保存当前配置到文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """设置配置项并自动保存"""
        self.config[key] = value
        self.save()


# ===========================================================================
# 模块二：身份文件加载 — 从指定文件夹读取登录身份文件
# ===========================================================================
class IdentityLoader:
    """身份文件加载器：读取目录下的所有JSON身份文件"""

    # 身份文件必填字段
    REQUIRED_FIELDS = ["username", "token", "owner", "repo", "workflow_id"]

    def __init__(self, identities_dir: str):
        """
        初始化身份加载器
        :param identities_dir: 身份文件存放目录路径
        """
        self.identities_dir = identities_dir

    def load_all(self) -> list:
        """
        加载目录下所有有效的身份文件
        :return: 身份字典列表
        """
        identities = []
        # 检查目录是否存在
        if not os.path.isdir(self.identities_dir):
            print(f"[警告] 身份文件目录不存在: {self.identities_dir}")
            print(f"[提示] 请创建该目录并放入身份JSON文件")
            return identities

        # 遍历目录下所有.json文件
        for filename in os.listdir(self.identities_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.identities_dir, filename)
            identity = self._parse_file(filepath)
            if identity:
                identities.append(identity)

        return identities

    def _parse_file(self, filepath: str) -> dict:
        """
        解析单个身份文件
        :param filepath: 文件路径
        :return: 身份字典，无效则返回None
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[跳过] 文件解析失败 {filepath}: {e}")
            return None

        # 校验必填字段
        for field in self.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                print(f"[跳过] 文件缺少字段 '{field}': {filepath}")
                return None

        # 标准化身份字典（enabled默认为True）
        identity = {
            "username": str(data["username"]),
            "token": str(data["token"]),
            "owner": str(data["owner"]),
            "repo": str(data["repo"]),
            "workflow_id": str(data["workflow_id"]),
            "enabled": bool(data.get("enabled", True)),
            "source_file": filepath  # 记录来源文件（不修改、不删除）
        }
        return identity


# ===========================================================================
# 模块三：GitHub VM连接 — 连接测试与workflow调度（预留接口）
# ===========================================================================
class GitHubVMConnector:
    """
    GitHub虚拟机连接器
    ——————————————————————————————————————
    【预留接口说明】
    当前为模拟实现，后续对接真实GitHub API时，
    只需继承此类并重写 test_connection / dispatch_workflow / check_status 方法
    ——————————————————————————————————————
    """

    def test_connection(self, identity: dict) -> tuple:
        """
        测试与GitHub虚拟服务器的连通性
        :param identity: 身份字典
        :return: (是否成功, 消息)
        """
        # 模拟实现：基于token格式做基本校验
        token = identity.get("token", "")
        if not token:
            return False, "Token为空"
        if not token.startswith("ghp_") and not token.startswith("github_pat_"):
            return False, f"Token格式无效: {token[:8]}..."

        # 模拟网络延迟
        time.sleep(random.uniform(0.3, 1.0))

        # 模拟连接结果（95%成功率）
        if random.random() < 0.95:
            return True, f"连接成功 (用户: {identity['username']})"
        else:
            return False, "网络超时，连接失败"

    def dispatch_workflow(self, identity: dict, inputs: dict = None) -> tuple:
        """
        触发GitHub Actions workflow（启动虚拟机）
        :param identity: 身份字典
        :param inputs: workflow输入参数
        :return: (是否成功, run_id或错误消息)
        """
        # 模拟实现：返回模拟的run_id
        run_id = random.randint(100000, 999999)
        return True, str(run_id)

    def check_status(self, identity: dict, run_id: str) -> str:
        """
        检查workflow运行状态
        :param identity: 身份字典
        :param run_id: 运行ID
        :return: 状态字符串 running/success/failed
        """
        # 模拟实现
        return random.choice(["running", "running", "success"])


# ===========================================================================
# 模块四：4399注册引擎 — 注册任务执行（预留接口）
# ===========================================================================
class RegistrationEngine:
    """
    4399注册引擎
    ——————————————————————————————————————
    【预留接口说明】
    当前为模拟实现（随机成功/失败），演示调度逻辑。
    后续对接真实注册程序时，继承此类并重写 run() 方法，
    可调用 register.py 子进程 或 在VM内执行注册流程。
    ——————————————————————————————————————
    """

    def __init__(self, target_count: int = 0):
        """
        初始化注册引擎
        :param target_count: 目标注册数量（0表示无限）
        """
        self.target_count = target_count
        self.success_count = 0

    def run(self, identity: dict) -> tuple:
        """
        执行一次4399注册
        :param identity: 身份字典
        :return: (是否成功, 详情描述)
        """
        # 模拟注册耗时
        time.sleep(random.uniform(0.5, 2.0))

        # 模拟注册结果（70%成功率）
        if random.random() < 0.7:
            username = "usr" + str(random.randint(100000, 999999))
            password = "Pass" + str(random.randint(10000, 99999))
            self.success_count += 1
            return True, f"注册成功 {username}:{password}"
        else:
            fail_reasons = [
                "验证码识别失败",
                "IP被限制",
                "用户名已存在",
                "网络超时",
                "身份信息无效"
            ]
            return False, random.choice(fail_reasons)


# ===========================================================================
# 模块五：VM进程 — 单台虚拟机的生命周期管理（多进程子类）
# ===========================================================================
class VMProcess(Process):
    """
    虚拟机进程
    ——————————————————————————————————————
    每个实例 = 一台虚拟机 = 一个并发
    独立进程运行，通过Queue向主进程上报状态
    通过Event接收停止信号
    ——————————————————————————————————————
    """

    # 最大重试次数（第二次重启后仍失败则永久关机）
    MAX_RETRIES = 2

    def __init__(self, identity: dict, status_queue: Queue,
                 stop_event: Event, run_duration_minutes: int,
                 connector: GitHubVMConnector, engine: RegistrationEngine):
        """
        初始化VM进程
        :param identity: 身份字典
        :param status_queue: 状态上报队列
        :param stop_event: 停止信号事件
        :param run_duration_minutes: 运行时长（分钟），0表示不限
        :param connector: VM连接器实例
        :param engine: 注册引擎实例
        """
        super().__init__(daemon=True)
        self.identity = identity
        self.status_queue = status_queue
        self.stop_event = stop_event
        self.run_duration_minutes = run_duration_minutes
        self.connector = connector
        self.engine = engine
        self.retry_count = 0  # 当前重启次数

    def run(self):
        """进程入口：VM完整生命周期"""
        username = self.identity["username"]

        # 阶段1：连接测试
        self._report("connecting", f"[{username}] 正在连接GitHub虚拟服务器...")
        connected, msg = self.connector.test_connection(self.identity)

        if not connected:
            self._report("failed", f"[{username}] 连接失败: {msg}")
            return

        # 连接成功
        self._report("connected", f"[{username}] 连接成功")

        # 阶段2：启动workflow（分配VM）
        dispatched, run_id = self.connector.dispatch_workflow(self.identity)
        if dispatched:
            self._report("vm_started", f"[{username}] 虚拟机已启动 (run_id: {run_id})")

        # 阶段3：注册任务循环
        start_time = time.time()
        duration_seconds = self.run_duration_minutes * 60 if self.run_duration_minutes > 0 else 0

        while not self.stop_event.is_set():
            # 检查运行时长是否到期
            if duration_seconds > 0:
                elapsed = time.time() - start_time
                if elapsed >= duration_seconds:
                    self._report("timeout", f"[{username}] 运行时长已到，自动停止")
                    break

            # 执行注册
            success, detail = self.engine.run(self.identity)

            if success:
                # 注册成功：重置重试计数
                self.retry_count = 0
                self._report("register_success", f"[{username}] {detail}")
            else:
                # 注册失败：判断是否需要自愈
                if self.retry_count >= self.MAX_RETRIES:
                    # 超过重试上限 → 永久关机
                    self._report("permanent_failure",
                                 f"[{username}] 第{self.retry_count}次重启后仍失败({detail})，永久关机")
                    break
                else:
                    # 自动重启：等待5~10分钟随机时长
                    wait_minutes = random.uniform(5, 10)
                    wait_seconds = int(wait_minutes * 60)
                    self._report("retrying",
                                 f"[{username}] 注册失败({detail})，{wait_minutes:.1f}分钟后自动重启...")
                    # 分段等待（可中断）
                    for _ in range(wait_seconds):
                        if self.stop_event.is_set():
                            self._report("stopped", f"[{username}] 重启等待中被停止")
                            return
                        time.sleep(1)
                    self.retry_count += 1
                    # 重新连接
                    self._report("reconnecting", f"[{username}] 第{self.retry_count}次重启，重新连接...")
                    connected, msg = self.connector.test_connection(self.identity)
                    if connected:
                        self._report("connected", f"[{username}] 重新连接成功")
                    else:
                        self._report("failed", f"[{username}] 重新连接失败: {msg}")
                        break

            # 注册间隔（避免高频请求）
            time.sleep(random.uniform(1, 3))

        # 进程结束
        self._report("stopped", f"[{username}] 虚拟机已停止")

    def _report(self, event_type: str, message: str):
        """
        向主进程上报状态
        :param event_type: 事件类型（connected/failed/retrying等）
        :param message: 消息内容
        """
        try:
            self.status_queue.put({
                "type": event_type,
                "message": message,
                "username": self.identity["username"],
                "timestamp": time.strftime("%H:%M:%S")
            })
        except Exception:
            pass  # 队列关闭时忽略


# ===========================================================================
# 模块六：调度器核心 — 并发调度、状态监控、自愈协调
# ===========================================================================
class Scheduler:
    """
    调度器核心
    ——————————————————————————————————————
    管理所有VM进程的创建、监控、销毁
    实时统计成功连接的虚拟机数量
    ——————————————————————————————————————
    """

    def __init__(self, config: ConfigManager):
        """
        初始化调度器
        :param config: 配置管理器实例
        """
        self.config = config
        self.connector = GitHubVMConnector()
        self.engine = RegistrationEngine(config.get("target_count", 50))
        self.identity_loader = IdentityLoader(config.get("identities_dir", "./identities"))

        # VM进程管理
        self.vm_processes = []       # [(process, stop_event, identity), ...]
        self.status_queue = Queue()  # 状态上报队列

        # 统计信息
        self.connected_count = 0     # 当前成功连接的VM数量
        self.total_success = 0       # 累计注册成功数
        self.total_failure = 0       # 累计注册失败数

        # 运行状态
        self.running = False
        self.monitor_thread = None

    def start_vms(self, run_duration_minutes: int) -> int:
        """
        启动GitHub虚拟机
        :param run_duration_minutes: 运行时长（分钟）
        :return: 成功启动的VM数量
        """
        # 加载身份文件
        identities = self.identity_loader.load_all()
        if not identities:
            print("[错误] 没有找到有效的身份文件，请先配置身份文件")
            return 0

        # 过滤可用的身份
        identities = [i for i in identities if i.get("enabled", True)]
        max_concurrency = self.config.get("max_concurrency", 5)
        # 受最大并发数限制
        identities = identities[:max_concurrency]

        print(f"\n[调度] 读取到 {len(identities)} 个身份，最大并发 {max_concurrency}")
        print("[调度] 正在启动虚拟机...\n")

        started_count = 0
        for identity in identities:
            # 为每个身份创建独立的停止事件
            stop_event = Event()
            # 创建VM进程
            vm = VMProcess(
                identity=identity,
                status_queue=self.status_queue,
                stop_event=stop_event,
                run_duration_minutes=run_duration_minutes,
                connector=self.connector,
                engine=self.engine
            )
            vm.start()
            self.vm_processes.append((vm, stop_event, identity))
            started_count += 1

        self.running = True
        return started_count

    def start_registration(self) -> bool:
        """
        启动4399注册任务（为已连接的VM分配注册任务）
        :return: 是否成功启动
        """
        if not self.vm_processes:
            print("[错误] 没有运行中的虚拟机，请先启动VM")
            return False

        print(f"\n[调度] 已为 {len(self.vm_processes)} 台虚拟机分配注册任务")
        print("[调度] 注册任务在后台持续运行，异常自愈机制已启用\n")
        return True

    def process_status_messages(self):
        """
        处理状态队列中的所有消息（非阻塞）
        更新统计信息并打印状态变化
        """
        while not self.status_queue.empty():
            try:
                msg = self.status_queue.get_nowait()
                event_type = msg["type"]
                message = msg["message"]
                username = msg["username"]

                # 根据事件类型更新统计
                if event_type == "connected":
                    self.connected_count += 1
                    print(f"  \033[32m[连接成功] {message}\033[0m")  # 绿色
                elif event_type == "failed":
                    print(f"  \033[31m[连接失败] {message}\033[0m")  # 红色
                elif event_type == "permanent_failure":
                    self.connected_count = max(0, self.connected_count - 1)
                    print(f"  \033[31m[永久关机] {message}\033[0m")  # 红色
                elif event_type == "register_success":
                    self.total_success += 1
                    print(f"  \033[32m{message}\033[0m")  # 绿色
                elif event_type == "retrying":
                    print(f"  \033[33m[自愈中] {message}\033[0m")  # 黄色
                elif event_type == "reconnecting":
                    print(f"  \033[33m{message}\033[0m")  # 黄色
                elif event_type == "vm_started":
                    print(f"  \033[36m{message}\033[0m")  # 青色
                elif event_type == "stopped":
                    self.connected_count = max(0, self.connected_count - 1)
                    print(f"  \033[90m{message}\033[0m")  # 灰色
                elif event_type == "timeout":
                    self.connected_count = max(0, self.connected_count - 1)
                    print(f"  \033[35m{message}\033[0m")  # 紫色
                else:
                    print(f"  {message}")

            except Exception:
                break

    def get_connected_count(self) -> int:
        """
        获取当前成功连接的VM数量
        同时清理已结束的进程
        """
        # 清理已结束的进程
        active_processes = []
        for vm, stop_event, identity in self.vm_processes:
            if vm.is_alive():
                active_processes.append((vm, stop_event, identity))
        self.vm_processes = active_processes

        # 处理最新消息以更新计数
        self.process_status_messages()

        return self.connected_count

    def shutdown_all(self):
        """
        一键关机：停止所有运行中的虚拟机
        身份文件保持原样（不修改、不删除、不重置）
        """
        print("\n[调度] 正在发送关机信号到所有虚拟机...")

        # 发送停止信号
        for vm, stop_event, identity in self.vm_processes:
            stop_event.set()

        # 等待进程优雅退出（最多10秒）
        timeout = 10
        for vm, stop_event, identity in self.vm_processes:
            vm.join(timeout=timeout)
            if vm.is_alive():
                vm.terminate()  # 超时则强制终止
                vm.join(timeout=2)

        # 清空进程列表
        self.vm_processes.clear()
        self.connected_count = 0
        self.running = False

        # 清空状态队列
        while not self.status_queue.empty():
            try:
                self.status_queue.get_nowait()
            except Exception:
                break

        print("[调度] 所有虚拟机已关机，身份文件未做任何修改")

    def has_active_vms(self) -> bool:
        """检查是否有运行中的VM"""
        return any(vm.is_alive() for vm, _, _ in self.vm_processes)


# ===========================================================================
# 模块七：CLI界面 — 控制台菜单、输入校验、实时状态展示
# ===========================================================================
class CLI:
    """
    控制台界面
    ——————————————————————————————————————
    固定菜单格式，顶部实时展示成功VM数量
    严格的输入合法性校验
    ——————————————————————————————————————
    """

    # 菜单分隔线
    SEPARATOR = "=" * 40

    def __init__(self):
        """初始化CLI"""
        self.config = ConfigManager()
        self.scheduler = Scheduler(self.config)
        # 注册Ctrl+C信号处理
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Ctrl+C信号处理：优雅关机"""
        print("\n\n[系统] 检测到中断信号，正在安全关机...")
        self.scheduler.shutdown_all()
        sys.exit(0)

    def run(self):
        """主循环：显示菜单并处理用户选择"""
        while True:
            self._clear_screen()
            self._show_menu()
            choice = input("  请选择操作 (1-4): ").strip()

            # 输入校验：必须是1-4的数字
            if not self._validate_menu_choice(choice):
                input("\n  \033[31m[错误] 请输入有效的数字选项 (1-4)\033[0m\n  按回车继续...")
                continue

            choice = int(choice)

            if choice == 1:
                self._handle_start_vms()
            elif choice == 2:
                self._handle_start_registration()
            elif choice == 3:
                self._handle_config()
            elif choice == 4:
                self._handle_shutdown()

    def _clear_screen(self):
        """清屏（跨平台）"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _show_menu(self):
        """
        显示主菜单（固定格式）
        顶部实时展示当前成功虚拟机数量
        """
        # 获取最新的VM连接数量
        connected = self.scheduler.get_connected_count()

        print(self.SEPARATOR)
        print(f"  当前成功虚拟机数量: {connected}")
        print(self.SEPARATOR)
        print("  1. 启动github虚拟机")
        print("  2. 启动4399注册")
        print("  3. 配置注册数量")
        print("  4. 一键关机")
        print(self.SEPARATOR)

    def _validate_menu_choice(self, value: str) -> bool:
        """校验菜单选项输入（必须是1-4的整数）"""
        if not value.isdigit():
            return False
        num = int(value)
        return 1 <= num <= 4

    def _validate_positive_int(self, value: str, min_val: int = 1, max_val: int = 99999) -> tuple:
        """
        校验正整数输入
        :param value: 输入字符串
        :param min_val: 最小值
        :param max_val: 最大值
        :return: (是否有效, 数值或None)
        """
        if not value.isdigit():
            return False, None
        num = int(value)
        if num < min_val or num > max_val:
            return False, None
        return True, num

    def _handle_start_vms(self):
        """处理选项1：启动GitHub虚拟机"""
        self._clear_screen()
        print("\n  === 启动GitHub虚拟机 ===\n")
        print("  请输入运行时长（分钟），范围 0~99999")
        print("  输入 0 直接返回上一级菜单\n")

        while True:
            value = input("  运行时长(分钟): ").strip()

            # 校验输入
            valid, minutes = self._validate_positive_int(value, 0, 99999)
            if not valid:
                print("  \033[31m[错误] 请输入 0~99999 范围内的整数\033[0m")
                continue

            if minutes == 0:
                return  # 返回上一级菜单

            break

        # 启动VM
        started = self.scheduler.start_vms(minutes)
        if started > 0:
            print(f"\n[调度] 已启动 {started} 个VM进程，正在连接中...")
            print("[提示] 连接结果将实时显示在菜单顶部")
            # 等待一段时间让连接结果出来
            time.sleep(2)
            self.scheduler.process_status_messages()
        else:
            print("\n[错误] 没有启动任何虚拟机")

        input("\n  按回车返回主菜单...")

    def _handle_start_registration(self):
        """处理选项2：启动4399注册任务"""
        self._clear_screen()
        print("\n  === 启动4399注册任务 ===\n")

        if not self.scheduler.has_active_vms():
            print("  \033[33m[提示] 当前没有运行中的虚拟机\033[0m")
            print("  请先选择 [1] 启动GitHub虚拟机\n")

            # 询问是否要先启动VM
            value = input("  是否现在启动虚拟机？(y/n): ").strip().lower()
            if value == 'y':
                self._handle_start_vms()
            return

        # 启动注册任务
        self.scheduler.start_registration()

        # 显示实时状态（持续刷新直到用户按回车）
        print("  正在监控注册状态（按回车返回主菜单）...")
        print("  ——————————————————————————————————————\n")

        # 短暂监控展示
        for _ in range(15):  # 最多展示约15秒
            self.scheduler.process_status_messages()
            time.sleep(1)

        print("\n  ——————————————————————————————————————")
        print("  [提示] 注册任务在后台持续运行")
        print(f"  累计成功: {self.scheduler.total_success} | 累计失败: {self.scheduler.total_failure}")
        input("\n  按回车返回主菜单...")

    def _handle_config(self):
        """处理选项3：配置参数"""
        while True:
            self._clear_screen()
            print("\n  === 配置注册参数 ===\n")
            print(f"  当前4399目标注册总数量: {self.config.get('target_count')}")
            print(f"  当前最大并发数量: {self.config.get('max_concurrency')}")
            print(f"  身份文件目录: {self.config.get('identities_dir')}")
            print()
            print("  1. 设置4399目标注册总数量")
            print("  2. 设置最大并发数量")
            print("  3. 设置身份文件目录")
            print("  0. 返回上一级菜单")
            print()

            value = input("  请选择 (0-3): ").strip()

            if value == "0":
                return

            if value == "1":
                self._config_target_count()
            elif value == "2":
                self._config_max_concurrency()
            elif value == "3":
                self._config_identities_dir()
            else:
                print("  \033[31m[错误] 请输入 0-3 的数字\033[0m")
                time.sleep(1)

    def _config_target_count(self):
        """配置目标注册数量"""
        while True:
            value = input("\n  请输入4399目标注册总数量 (1~99999): ").strip()
            valid, num = self._validate_positive_int(value, 1, 99999)
            if valid:
                self.config.set("target_count", num)
                print(f"  \033[32m[成功] 目标注册数量已设置为 {num}\033[0m")
                time.sleep(1)
                return
            print("  \033[31m[错误] 请输入 1~99999 范围内的整数\033[0m")

    def _config_max_concurrency(self):
        """配置最大并发数量"""
        while True:
            value = input("\n  请输入最大并发数量 (1~100): ").strip()
            valid, num = self._validate_positive_int(value, 1, 100)
            if valid:
                self.config.set("max_concurrency", num)
                print(f"  \033[32m[成功] 最大并发数量已设置为 {num}\033[0m")
                time.sleep(1)
                return
            print("  \033[31m[错误] 请输入 1~100 范围内的整数\033[0m")

    def _config_identities_dir(self):
        """配置身份文件目录"""
        value = input("\n  请输入身份文件目录路径: ").strip()
        if value:
            self.config.set("identities_dir", value)
            # 重新初始化调度器的身份加载器
            self.scheduler.identity_loader = IdentityLoader(value)
            print(f"  \033[32m[成功] 身份文件目录已设置为 {value}\033[0m")
            time.sleep(1)
        else:
            print("  \033[31m[错误] 路径不能为空\033[0m")
            time.sleep(1)

    def _handle_shutdown(self):
        """处理选项4：一键关机"""
        self._clear_screen()
        print("\n  === 一键关机 ===\n")

        if not self.scheduler.has_active_vms():
            print("  [提示] 当前没有运行中的虚拟机")
            time.sleep(1)
            return

        # 确认操作
        value = input("  确认关闭所有虚拟机？(y/n): ").strip().lower()
        if value != 'y':
            print("  [提示] 已取消关机操作")
            time.sleep(1)
            return

        # 执行关机
        self.scheduler.shutdown_all()
        print("\n  \033[32m[完成] 所有虚拟机已安全关闭\033[0m")
        print("  [提示] 身份文件保持原样，未做任何修改")
        input("\n  按回车返回主菜单...")


# ===========================================================================
# 程序入口
# ===========================================================================
def main():
    """程序入口函数"""
    # 设置多进程启动方式（Windows兼容）
    if sys.platform == 'win32':
        multiprocessing.set_start_method('spawn', force=True)

    # 修复Windows终端编码
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("\n" + "=" * 40)
    print("  VM Scheduler 虚拟机调度主控程序")
    print("  版本: 1.0.0")
    print("=" * 40)
    print("\n  正在初始化...")

    # 创建并运行CLI
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
