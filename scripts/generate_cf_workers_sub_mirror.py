#!/usr/bin/env python3

from __future__ import annotations

import base64
import hashlib
import json
import sys
import urllib.parse
from pathlib import Path


def parse_vless(line: str) -> dict:
    parts = urllib.parse.urlsplit(line)
    if parts.scheme != "vless":
        raise ValueError(f"Unsupported scheme: {parts.scheme}")

    if "@" not in parts.netloc:
        raise ValueError("Missing UUID or server in VLESS URI")
    uuid, server_part = parts.netloc.split("@", 1)
    if ":" not in server_part:
        raise ValueError("Missing port in VLESS URI")
    server, port = server_part.rsplit(":", 1)

    query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
    name = urllib.parse.unquote(parts.fragment or f"{server}:{port}")

    proxy = {
        "name": name,
        "type": "vless",
        "server": server,
        "port": int(port),
        "uuid": uuid,
        "udp": True,
        "network": query.get("type", ["ws"])[0],
        "tls": query.get("security", ["none"])[0] == "tls",
        "servername": query.get("sni", [""])[0] or None,
        "client-fingerprint": query.get("fp", ["chrome"])[0] or None,
        "skip-cert-verify": query.get("allowInsecure", ["0"])[0] in {"1", "true", "True"},
    }

    host = query.get("host", [""])[0]
    path = query.get("path", ["/"])[0] or "/"
    proxy["ws-opts"] = {
        "path": path,
        "headers": {"Host": host} if host else {},
    }
    return proxy


def yaml_scalar(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return '""'
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def emit_mapping(lines: list[str], mapping: dict, indent: int = 0) -> None:
    prefix = " " * indent
    for key, value in mapping.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            emit_mapping(lines, value, indent + 2)
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    emit_mapping(lines, item, indent + 4)
                else:
                    lines.append(f"{prefix}  - {yaml_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {yaml_scalar(value)}")


def build_clash_yaml(proxies: list[dict]) -> str:
    lines = [
        "mixed-port: 7890",
        "allow-lan: false",
        "mode: rule",
        "log-level: info",
        "",
        "proxies:",
    ]
    for proxy in proxies:
        lines.append("  -")
        emit_mapping(lines, proxy, 4)

    names = [proxy["name"] for proxy in proxies]
    lines.extend(
        [
            "",
            "proxy-groups:",
            '  - name: "节点选择"',
            "    type: select",
            "    proxies:",
            '      - "自动选择"',
        ]
    )
    lines.extend(f'      - "{name}"' for name in names)
    lines.extend(
        [
            '  - name: "自动选择"',
            "    type: url-test",
            '    url: "https://www.gstatic.com/generate_204"',
            "    interval: 300",
            "    tolerance: 50",
            "    proxies:",
        ]
    )
    lines.extend(f'      - "{name}"' for name in names)
    lines.extend(
        [
            "",
            "rules:",
            '  - "MATCH,节点选择"',
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "usage: generate_cf_workers_sub_mirror.py INPUT_LINK OUTPUT_B64 OUTPUT_CLASH OUTPUT_META",
            file=sys.stderr,
        )
        return 1

    input_path = Path(argv[1])
    output_b64 = Path(argv[2])
    output_clash = Path(argv[3])
    output_meta = Path(argv[4])

    lines = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise SystemExit("input LINK.txt is empty")

    output_b64.write_text(base64.b64encode("\n".join(lines).encode("utf-8")).decode("utf-8") + "\n", encoding="utf-8")
    proxies = [parse_vless(line) for line in lines]
    clash_text = build_clash_yaml(proxies)
    output_clash.write_text(clash_text, encoding="utf-8")

    metadata = {
        "source_link_url": "https://raw.githubusercontent.com/XavierXIEXIN/CF-Workers-SUB/main/LINK.txt",
        "decoded_node_count": len(lines),
        "link_sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
        "b64_sha256": hashlib.sha256(output_b64.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest(),
        "clash_sha256": hashlib.sha256(clash_text.encode("utf-8")).hexdigest(),
    }
    output_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
