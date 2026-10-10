#!/usr/bin/env python3
"""Restart with application egress denied; check persistent saves and browser input."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def oc(*args, **kwargs):
    return subprocess.run(["oc", "-n", "retroarch", *args], check=True, **kwargs)


def state_hashes():
    return oc("exec", "deployment/retroarch", "--", "sha256sum",
        "/home/ubuntu/.config/retroarch/autoconfig/sdl2/Selkies.cfg",
        "/home/ubuntu/.config/retroarch/saves/2048/2048.srm",
        "/home/ubuntu/.config/retroarch/playlists/logs/2048/2048.lrtl",
        capture_output=True, text=True).stdout


def main():
    baseline = state_hashes()
    policy = {"apiVersion":"networking.k8s.io/v1", "kind":"NetworkPolicy",
        "metadata":{"name":"retroarch-offline-test"},
        "spec":{"podSelector":{"matchLabels":{"app":"retroarch"}},
                "policyTypes":["Egress"],"egress":[]}}
    created = False
    try:
        oc("create", "-f", "-", input=json.dumps(policy), text=True)
        created = True
        oc("rollout", "restart", "deployment/retroarch")
        oc("rollout", "status", "deployment/retroarch", "--timeout=5m")
        # Prove that the selected policy actually blocks external connections.
        denied = subprocess.run(["oc", "-n", "retroarch", "exec", "deployment/retroarch", "--",
            "python3", "-c", "import socket; socket.create_connection(('1.1.1.1',443),timeout=3)"], capture_output=True)
        if denied.returncode == 0:
            raise RuntimeError("Egress denial was not effective; check other additive policies")
        if state_hashes() != baseline:
            raise RuntimeError("Persistent controller profile, save, or playlist runtime changed")
        subprocess.run([sys.executable, str(ROOT / "scripts/browser-smoke.py")], check=True)
        print("Offline restart, persistent state hashes, authenticated video, and synthetic controller input passed.")
    finally:
        if created:
            oc("delete", "networkpolicy", "retroarch-offline-test", "--ignore-not-found")


if __name__ == "__main__":
    main()
