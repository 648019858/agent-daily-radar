#!/usr/bin/env python3
"""
本地开发服务器 — 启动后在浏览器查看炫酷科技风 Agent 雷达页面
"""

import http.server
import os
import sys
import shutil
import socketserver
import webbrowser
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
DATA_DIR = os.path.join(BASE_DIR, "data")
PORT = 8899


def prepare():
    """确保 web 目录下有 data 符号链接或副本"""
    web_data = os.path.join(WEB_DIR, "data")
    if not os.path.exists(web_data):
        # 创建副本
        target = os.path.join(DATA_DIR, "today.json")
        if os.path.exists(target):
            os.makedirs(web_data, exist_ok=True)
            shutil.copy2(target, os.path.join(web_data, "today.json"))
            print(f"✅ 数据文件已复制到 web/data/today.json")
        else:
            print(f"⚠️  数据文件不存在，请先运行: python scripts/fetch_data.py")
    elif not os.path.exists(os.path.join(web_data, "today.json")):
        target = os.path.join(DATA_DIR, "today.json")
        if os.path.exists(target):
            shutil.copy2(target, os.path.join(web_data, "today.json"))


def main():
    prepare()

    # 切换到 web 目录
    os.chdir(WEB_DIR)

    # 使用 ThreadingHTTPServer 支持并发
    handler = http.server.SimpleHTTPRequestHandler

    # 避免端口占用
    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 60)
        print("🚀 Agent Daily Radar 已启动")
        print(f"   👉 打开浏览器访问: {url}")
        print(f"   📁 服务目录: {WEB_DIR}")
        print(f"   按 Ctrl+C 停止服务")
        print("=" * 60)

        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 服务已停止")


if __name__ == "__main__":
    main()
