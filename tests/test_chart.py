from pathlib import Path
import subprocess
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PINS = ["--set", "image.digest=sha256:" + "a" * 64,
        "--set", "gpu.plugin.digest=sha256:" + "b" * 64]


class DeploymentContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rendered = subprocess.check_output(["helm", "template", "retroarch", str(ROOT / "charts/retroarch"), "-n", "retroarch"] + PINS, text=True)
        cls.resources = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all(rendered) if d}

    def test_unpinned_images_refused(self):
        result = subprocess.run(["helm", "template", "retroarch", str(ROOT / "charts/retroarch")], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_application_cannot_access_host_or_api(self):
        pod = self.resources["Deployment", "retroarch"]["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertTrue(pod["securityContext"]["runAsNonRoot"])
        self.assertFalse(any("hostPath" in v for v in pod["volumes"]))
        self.assertEqual(pod["containers"][0]["resources"]["limits"]["gaming.batchelor.live/amd-gpu"], 1)
        scc = self.resources["SecurityContextConstraints", "retroarch-session"]
        self.assertFalse(scc["allowPrivilegedContainer"])
        self.assertFalse(scc["allowPrivilegeEscalation"])

    def test_persistent_storage_is_retained(self):
        for name in ("retroarch-library", "retroarch-state"):
            pvc = self.resources["PersistentVolumeClaim", name]
            self.assertEqual(pvc["metadata"]["annotations"]["helm.sh/resource-policy"], "keep")

    def test_route_and_auth_boundary(self):
        route = self.resources["Route", "retroarch"]
        self.assertEqual(route["spec"]["tls"]["insecureEdgeTerminationPolicy"], "Redirect")
        self.assertEqual(route["metadata"]["annotations"]["haproxy.router.openshift.io/ip_allowlist"], "10.45.45.0/24")
        pod = self.resources["Deployment", "retroarch"]["spec"]["template"]["spec"]
        password = next(e for e in pod["containers"][0]["env"] if e["name"] == "SELKIES_BASIC_AUTH_PASSWORD")
        self.assertEqual(password["valueFrom"]["secretKeyRef"]["name"], "retroarch-login")
