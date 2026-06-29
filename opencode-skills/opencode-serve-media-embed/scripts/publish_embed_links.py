#!/usr/bin/env python3
"""Publish PNG/PDF links for OpenCode app embedding.

This helper can:
- discover recent PNG/PDF files in an exports directory
- optionally start a static server on 0.0.0.0:<port>
- resolve local Tailscale IPv4
- verify URLs and print ready-to-paste Markdown
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def newest_file(directory: Path, suffix: str) -> Path | None:
    matches = [p for p in directory.glob(f"*.{suffix}") if p.is_file()]
    if not matches:
        return None
    return sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.75)
        return sock.connect_ex((host, port)) == 0


def tailscale_ipv4() -> str:
    proc = run(["tailscale", "status", "--json"])
    if proc.returncode != 0:
        raise RuntimeError(
            "Failed to read Tailscale status JSON. stderr: " + proc.stderr.strip()
        )
    data = json.loads(proc.stdout)
    ips = data.get("Self", {}).get("TailscaleIPs", [])
    for ip in ips:
        if "." in ip:
            return ip
    raise RuntimeError("No Tailscale IPv4 found in `tailscale status --json`.")


def start_server(root: Path, port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            "0.0.0.0",
            "--directory",
            str(root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def url_ok(url: str) -> bool:
    proc = run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", url])
    return proc.returncode == 0 and proc.stdout.strip() == "200"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports-dir", default="/home/cloud/projects/skillbridge/tmp_exports")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--start-server", action="store_true")
    args = parser.parse_args()

    exports_dir = Path(args.exports_dir)
    if not exports_dir.exists() or not exports_dir.is_dir():
        raise SystemExit(f"Exports dir not found: {exports_dir}")

    png = newest_file(exports_dir, "png")
    pdf = newest_file(exports_dir, "pdf")
    if not png and not pdf:
        raise SystemExit(f"No PNG/PDF files found in: {exports_dir}")

    if args.start_server and not is_port_open("127.0.0.1", args.port):
        start_server(exports_dir, args.port)

    if not is_port_open("127.0.0.1", args.port):
        raise SystemExit(f"Port {args.port} is not listening. Start the server first.")

    ip = tailscale_ipv4()

    png_url = f"http://{ip}:{args.port}/{png.name}" if png else None
    pdf_url = f"http://{ip}:{args.port}/{pdf.name}" if pdf else None

    if png_url and not url_ok(png_url):
        raise SystemExit(f"PNG URL is not reachable (200 expected): {png_url}")
    if pdf_url and not url_ok(pdf_url):
        raise SystemExit(f"PDF URL is not reachable (200 expected): {pdf_url}")

    print("# Server")
    print(f"Tailscale IP: {ip}")
    print(f"Port: {args.port}")
    print(f"Web root: {exports_dir}")
    print()
    print("# Links")
    if png_url:
        print(f"PNG: {png_url}")
    if pdf_url:
        print(f"PDF: {pdf_url}")
    print()
    print("# Markdown")
    if png_url:
        print(f"[Open PNG]({png_url})")
    if pdf_url:
        print(f"[Open PDF]({pdf_url})")
    print()
    if png_url:
        print(f"![schematic]({png_url})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
