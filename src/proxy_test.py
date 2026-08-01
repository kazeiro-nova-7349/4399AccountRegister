#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
from urllib.parse import urlparse

import requests


TARGET_URL = os.getenv("TARGET_URL", "https://www.baidu.com")
PROXY_API = os.getenv("PROXY_API", "")
PROXY_HOST = os.getenv("PROXY_HOST", "")
PROXY_PORT = os.getenv("PROXY_PORT", "")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")
DEFAULT_PROXY_API = "https://service.ipzan.com/core-extract?num=1&no=20260712920961949707&minute=3&format=json&area=110100&protocol=1&pool=quality&mode=whitelist&library=3&secret=4fu8b38582rvvlo"


def parse_proxy_text(text):
    match = re.search(r"(?:(?:http|https)://)?([^\s:/]+):(\d+)", text)
    if not match:
        raise ValueError(f"未能从返回文本中解析代理: {text[:200]}")
    return match.group(1), match.group(2)


def parse_proxy_json(data):
    if isinstance(data, list) and data:
        return parse_proxy_json(data[0])

    if isinstance(data, dict):
        for key in ("data", "list", "result", "proxy"):
            if key in data:
                return parse_proxy_json(data[key])

        host = data.get("ip") or data.get("host") or data.get("proxyHost")
        port = data.get("port") or data.get("proxyPort")
        if host and port:
            return str(host), str(port)

        proxy = data.get("proxy") or data.get("addr") or data.get("address")
        if proxy:
            return parse_proxy_text(str(proxy))

    if isinstance(data, str):
        return parse_proxy_text(data)

    raise ValueError(f"未识别的代理 API 返回格式: {data}")


def fetch_proxy_from_api():
    proxy_api = PROXY_API or DEFAULT_PROXY_API
    if not proxy_api:
        return None

    response = requests.get(proxy_api, timeout=10)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "json" in content_type.lower():
        return parse_proxy_json(response.json())

    text = response.text.strip()
    try:
        return parse_proxy_json(response.json())
    except ValueError:
        return parse_proxy_text(text)


def build_proxy_url():
    proxy_from_api = fetch_proxy_from_api()
    if proxy_from_api:
        host, port = proxy_from_api
    else:
        host, port = PROXY_HOST, PROXY_PORT

    if not host:
        raise ValueError("请设置 PROXY_API，或设置 PROXY_HOST")
    if not port:
        raise ValueError("请设置 PROXY_API，或设置 PROXY_PORT")

    if PROXY_USER and PROXY_PASSWORD:
        return f"http://{PROXY_USER}:{PROXY_PASSWORD}@{host}:{port}"
    return f"http://{host}:{port}"


def main():
    proxy_url = build_proxy_url()
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }

    print("使用代理:", urlparse(proxy_url).netloc.rsplit("@", 1)[-1])

    start = time.perf_counter()
    try:
        response = requests.get(
            TARGET_URL,
            proxies=proxies,
            timeout=10,
            verify=True,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        print("HTTP 状态码:", response.status_code)
        print("响应前 500 字符:")
        print(response.text[:500])
        print("耗时:", f"{elapsed_ms}ms")
    except requests.exceptions.ProxyError as exc:
        print("代理连接失败:", exc)
    except requests.exceptions.Timeout:
        print("请求超时")
    except requests.exceptions.RequestException as exc:
        print("请求失败:", exc)
    except ValueError as exc:
        print("配置错误:", exc)


if __name__ == "__main__":
    main()
