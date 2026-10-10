#!/usr/bin/env python3
"""Snapshot upstream Linux cores; verify locked archives; probe runtime loading."""
import argparse
import concurrent.futures
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import zipfile

BASE = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/"
INFO = "https://buildbot.libretro.com/assets/frontend/info.zip"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def download(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                return response.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def unpack(data, destination, suffix):
    destination.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            path = Path(member.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe archive member: " + member.filename)
            if path.suffix != suffix or member.is_dir():
                continue
            target = destination / path.name
            content = archive.read(member)
            target.write_bytes(content)
            extracted.append({"name": path.name, "sha256": sha(content)})
    if not extracted:
        raise ValueError("Archive contains no " + suffix + " files")
    return extracted


def paths(root):
    return root / ("vendor/core-bundle" if (root / "scripts").exists() else "core-bundle")


def fetch(root):
    bundle = paths(root)
    (bundle / "archives").mkdir(parents=True, exist_ok=True)
    lock_path = root / "cores.lock.json"
    if lock_path.exists():
        lock = json.loads(lock_path.read_text())
        entries = lock["archives"]
        print("Restoring locked bundle " + lock["bundle_id"], flush=True)
    else:
        index = download(BASE + ".index").decode()
        names = sorted(set(re.findall(r"[A-Za-z0-9_+.-]+_libretro\.so\.zip", index)))
        if not names:
            raise RuntimeError("No cores found in upstream index")
        entries = [{"name": n, "url": BASE + n, "kind": "core"} for n in names]
        entries.append({"name": "info.zip", "url": INFO, "kind": "info"})
        lock = {"schema": 1, "platform": "linux-x86_64", "archives": entries}
        print("Snapshotting %d cores" % len(names), flush=True)

    def retrieve(entry):
        archive = bundle / "archives" / entry["name"]
        data = archive.read_bytes() if archive.exists() else download(entry["url"])
        digest = sha(data)
        if "sha256" in entry and digest != entry["sha256"]:
            raise ValueError("Checksum mismatch: " + entry["name"])
        archive.write_bytes(data)
        destination, suffix = ("cores", ".so") if entry["kind"] == "core" else ("info", ".info")
        files = unpack(data, bundle / destination, suffix)
        print(entry["name"], flush=True)
        return dict(entry, sha256=digest, files=files)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        lock["archives"] = sorted(pool.map(retrieve, entries), key=lambda e: e["name"])
    identity = sha(json.dumps(lock["archives"], sort_keys=True).encode())[:16]
    lock["bundle_id"] = "linux-x86_64-" + identity
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    verify(root)


def verify(root):
    lock = json.loads((root / "cores.lock.json").read_text())
    bundle = paths(root)
    for entry in lock["archives"]:
        archive = bundle / "archives" / entry["name"]
        if sha(archive.read_bytes()) != entry["sha256"]:
            raise ValueError("Archive checksum mismatch: " + entry["name"])
        directory = "cores" if entry["kind"] == "core" else "info"
        for file in entry["files"]:
            if sha((bundle / directory / file["name"]).read_bytes()) != file["sha256"]:
                raise ValueError("Core/info checksum mismatch: " + file["name"])
    print("Verified " + lock["bundle_id"], flush=True)


def probe(root):
    results = []
    for core in sorted((paths(root) / "cores").glob("*.so")):
        try:
            process = subprocess.run(
                [sys.executable, "-c", "import ctypes,sys; "
                 "[ctypes.CDLL(n,mode=ctypes.RTLD_GLOBAL) for n in ('libstdc++.so.6','libudev.so.1','libGL.so.1')]; "
                 "c=ctypes.CDLL(sys.argv[1]); assert c.retro_api_version()==1", str(core)],
                capture_output=True, text=True, timeout=15)
            results.append({"core": core.name, "loadable": process.returncode == 0,
                            "detail": process.stderr.strip(), "exit_code": process.returncode})
        except subprocess.TimeoutExpired:
            results.append({"core": core.name, "loadable": False, "detail": "load timeout"})
    print(json.dumps({"note": "Library loading with RetroArch's common global dependencies; no ROM or gameplay test", "cores": results}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "verify", "probe"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    globals()[args.command](args.root)
