#!/usr/bin/env python3
"""Quiesce the session, archive its state, and verify a scratch restoration."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def oc(*args, **kwargs):
    return subprocess.run(["oc", "-n", "retroarch", *args], check=True, **kwargs)


def get(*args):
    return json.loads(oc("get", *args, "-o", "json", capture_output=True, text=True).stdout)


def main():
    deployment = get("deployment", "retroarch")
    previous = deployment["spec"]["replicas"]
    image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = ROOT / "recovery" / stamp
    directory.mkdir(parents=True, mode=0o700)
    pod_name = "retroarch-state-backup"
    existing = oc("get", "pod", pod_name, "--ignore-not-found", "-o", "name", capture_output=True, text=True).stdout.strip()
    if existing:
        raise RuntimeError("A state maintenance pod already exists; finish that operation first")
    created = False
    try:
        oc("scale", "deployment/retroarch", "--replicas=0")
        oc("wait", "--for=delete", "pod", "-l", "app=retroarch", "--timeout=120s")
        pod = {
            "apiVersion": "v1", "kind": "Pod", "metadata": {"name": pod_name},
            "spec": {
                "serviceAccountName": "retroarch", "automountServiceAccountToken": False,
                "restartPolicy": "Never", "activeDeadlineSeconds": 3600,
                "terminationGracePeriodSeconds": 1,
                "nodeSelector": deployment["spec"]["template"]["spec"]["nodeSelector"],
                "securityContext": {"runAsUser": 1000, "runAsGroup": 1000, "runAsNonRoot": True,
                                    "fsGroup": 1000, "seccompProfile": {"type": "RuntimeDefault"}},
                "containers": [{"name": "archive", "image": image,
                    "command": ["sleep", "3600"],
                    "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                    "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"memory": "512Mi"}},
                    "volumeMounts": [{"name": "state", "mountPath": "/state", "readOnly": True},
                                     {"name": "scratch", "mountPath": "/restore"}]}],
                "volumes": [{"name": "state", "persistentVolumeClaim": {"claimName": "retroarch-state"}},
                            {"name": "scratch", "emptyDir": {}}]}}
        oc("create", "-f", "-", input=json.dumps(pod), text=True)
        created = True
        oc("wait", "pod/" + pod_name, "--for=condition=Ready", "--timeout=180s")
        archive = directory / "state.tar.gz"
        with archive.open("wb") as output:
            oc("exec", pod_name, "--", "tar", "-C", "/state", "-czf", "-", ".", stdout=output)
        # The emptyDir mount itself is root-owned. Restore into a directory owned
        # by the session UID so tar can restore directory metadata without root.
        oc("exec", pod_name, "--", "mkdir", "/restore/state")
        with archive.open("rb") as content:
            oc("exec", "-i", pod_name, "--", "tar", "-C", "/restore/state", "--no-same-owner", "-xzf", "-", stdin=content)
        # Compare a complete file hash inventory, not just tar's exit status.
        remote = "import hashlib,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file() and not f.is_symlink()},sort_keys=True))"
        original = oc("exec", pod_name, "--", "python3", "-c", remote, "/state", capture_output=True, text=True).stdout
        restored = oc("exec", pod_name, "--", "python3", "-c", remote, "/restore/state", capture_output=True, text=True).stdout
        if original != restored:
            raise RuntimeError("Scratch restoration differs from original state")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (directory / "metadata.json").write_text(json.dumps({"image": image, "archive_sha256": digest,
            "scratch_restore_verified": True, "files": json.loads(original)}, indent=2) + "\n")
        print("Verified backup and scratch restore: " + str(archive))
    finally:
        try:
            if created:
                oc("delete", "pod", pod_name, "--ignore-not-found", "--wait=true")
        finally:
            oc("scale", "deployment/retroarch", "--replicas=" + str(previous))
            if previous:
                oc("rollout", "status", "deployment/retroarch", "--timeout=5m")


if __name__ == "__main__":
    main()
