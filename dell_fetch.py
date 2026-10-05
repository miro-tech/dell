#!/usr/bin/env python3
"""
Dell VPN — fetch subscription from Google Drive.

Flow:
  Google Drive
    -> base64 decode
    -> extract vless:// / ss:// / vmess:// / trojan:// ...
    -> save decoded subscription
    -> save all URIs
    -> save JSON

Usage:
  python3 dell_fetch.py
  python3 dell_fetch.py --out output
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote


DRIVE_URL = (
    "https://www.googleapis.com/drive/v3/files/"
    "1HAkUZlv0_B4SiMBDcJ2iWgUzXd0qv7M4"
    "?alt=media&key=AIzaSyAIkceIeonANeKGrqeZpiC_HoBzgsQGAdg"
)

UA = "v2rayNG/1.8.29"
CTX = ssl.create_default_context()


def fetch() -> bytes:
    req = urllib.request.Request(
        DRIVE_URL,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )

    try:
        with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:
            return resp.read()

    except urllib.error.HTTPError as e:
        print(
            f"ERROR: Google Drive HTTP {e.code}: {e.reason}",
            file=sys.stderr,
        )
        raise

    except urllib.error.URLError as e:
        print(
            f"ERROR: Google Drive connection failed: {e.reason}",
            file=sys.stderr,
        )
        raise


def decode_subscription(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace").strip()

    # Drive file is normally Base64.
    try:
        decoded = base64.b64decode(
            text,
            validate=True,
        ).decode("utf-8")

        # Make sure decoded content actually looks like a subscription.
        if "://" in decoded:
            return decoded

    except Exception:
        pass

    # Already plain text.
    return text


def extract_uris(body: str) -> list[str]:
    out: list[str] = []

    for line in body.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        if "://" in line:
            out.append(line)

    return out


def parse_uri(u: str) -> dict:
    name = unquote(u.split("#", 1)[1]) if "#" in u else ""

    m = re.match(
        r"(\w+)://([^@]+)@([^:/]+):(\d+)",
        u,
    )

    if not m:
        return {
            "uri": u,
            "name": name,
        }

    return {
        "protocol": m.group(1),
        "uuid": m.group(2),
        "host": m.group(3),
        "port": int(m.group(4)),
        "name": name,
        "uri": u,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Dell VPN Drive subscription fetcher"
    )

    ap.add_argument(
        "--out",
        default=".",
        help="output directory",
    )

    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("[1/2] Google Drive subscription...")

    raw = fetch()

    (out / "dell_sub_raw.txt").write_bytes(raw)

    print(f"      raw {len(raw)} bytes")

    body = decode_subscription(raw)

    (out / "dell_sub_decoded.txt").write_text(
        body,
        encoding="utf-8",
    )

    print("[2/2] Parse URIs...")

    uris = extract_uris(body)

    if not uris:
        print(
            "ERROR: no URIs found",
            file=sys.stderr,
        )
        return 1

    servers = [parse_uri(u) for u in uris]

    (out / "dell_uris_all.txt").write_text(
        "\n".join(uris) + "\n",
        encoding="utf-8",
    )

    (out / "dell_uris.json").write_text(
        json.dumps(
            servers,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    by_proto: dict[str, int] = {}

    for server in servers:
        protocol = server.get("protocol", "?")
        by_proto[protocol] = (
            by_proto.get(protocol, 0) + 1
        )

    print(
        f"      {len(uris)} URIs  {by_proto}"
    )

    print()
    print("Saved:")
    print(f"  {out / 'dell_sub_raw.txt'}")
    print(f"  {out / 'dell_sub_decoded.txt'}")
    print(f"  {out / 'dell_uris_all.txt'}")
    print(f"  {out / 'dell_uris.json'}")

    print()
    print("--- servers ---")

    for server in servers:
        print(
            f"  [{server.get('protocol', '?'):6}] "
            f"{server.get('host', '?'):18}:"
            f"{server.get('port', '?'):<5}  "
            f"{server.get('name', '')}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
