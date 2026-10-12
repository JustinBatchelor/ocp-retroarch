# Validation record

Initial deployment completed on **2026-10-10** at
https://retroarch.apps.sno.batchelor.live, Helm release `retroarch`, revision 2.
The owner confirmed that the real Xbox controller works for menu navigation
through the Route. The session was left running for their use.
The private-IPv4 access update was deployed on **2026-10-11**, revision 3;
affected-device VPN acceptance remains pending as detailed below.

## Deployed configuration

- OpenShift 4.22.16; one session on `worker-0`, Ryzen 9 5900X.
- AMD Radeon RX 5700 XT, existing host `amdgpu`, allocated through
  `gaming.batchelor.live/amd-gpu`. Host SELinux remains enforcing.
- Native RetroArch 1.20.0 with Selkies WebSocket streaming, 1080p60, H.264,
  approximately 15 Mbps. Application and plugin digests are recorded in
  [deployment.lock.json](../deployment.lock.json); upstream pins are in
  [images.lock.json](../images.lock.json).
- Core bundle `linux-x86_64-cc958ce52a203870`; archive and extracted-file checksums
  are recorded in [cores.lock.json](../cores.lock.json).
- Bound `truenas-nfs` PVCs: 250 GiB library and 20 GiB state. Both survive Helm
  uninstall; the requested capacities do not enforce NFS quotas.
- Secret-backed personal authentication, trusted edge TLS, private-IPv4 source allowlist,
  router-only application ingress. Application runs non-root under its dedicated
  SCC, without host mounts, API token, added capabilities, or privilege escalation.
  The device plugin has a separate privileged service account.

## Checks performed

| Area | Result and evidence |
| --- | --- |
| Manifests and local tests | Helm lint and server-side dry run passed; eight unit tests passed. Core archive and extracted-file integrity checks passed. |
| HTTPS and authentication | Chrome accepted the Route certificate; anonymous HTTP request returned 401, authenticated request returned 200. |
| Browser streaming | Chrome received a 1920×1080 stream over WebSockets in a secure context with Gamepad API available. First automated run received 2,245 WebSocket frames and about 10.8 MB, without JavaScript errors. |
| OpenGL | Renderer reported RX 5700 XT, OpenGL 4.6, Mesa 25.0.7. Bundled ROM-free 2048 completed 180 frames using `glcore`. |
| Vulkan | RADV NAVI10 was available; the 2048 Vulkan smoke selected the AMD GPU and completed 180 frames. Software Vulkan was also enumerated but was not selected by that test. |
| Hardware encoding | VA-API H.264 encode capabilities reported; an actual three-second 1080p60 FFmpeg hardware encode passed. Active Selkies logs confirmed VAAPI H264 on amdgpu with DRI3 GPU buffers encoded in place. |
| Controller forwarding | Initial synthetic browser input reached server SDL for buttons, D-pad, sticks, triggers, and neutral release. Server detected the owner's Xbox Wireless Controller; the owner confirmed real controller menu navigation works. |
| Controller profile | Persistent SDL2 profile matches `X360 Controller` and uses SDL GameController button positions. RetroArch logged `Selkies Xbox Controller configured`. Start+Select is the menu combination. |
| Core availability | 241 of 243 catalog cores passed native library load checks. This checks dependencies/loadability, not game compatibility. |
| Persistence | Configuration and controller profile survived pod replacement and application upgrade. The 2048 smoke wrote a save-RAM file and runtime playlist log to persistent state. |
| Backup restoration | `backup-state.py` archived state, restored into scratch storage, and verified all restored file hashes. Successful archive: `recovery/20261010T173005Z/state.tar.gz`; metadata records the image and archive checksum. This archive predates the later 2048 save. |

The later automated browser run lost its primary connection when the owner
connected to play. Its SDL GameController input assertions therefore did not
complete; this run is not counted as a pass. The script now recognizes that
takeover explicitly. No further takeover or restart tests were run during the
owner's session. Local diagnostic logs and screenshots are in ignored `recovery/`.

The two unavailable cores in this bundle are `fsuae_libretro.so` (unresolved
`esp_scsi_init`) and `melonds_libretro.so` (executable-stack request rejected by
the runtime). PUAE and melonDS DS are included alternatives, with gameplay still
to be tested. See the [full native load report](core-compatibility.json).

## Private-IPv4 access update — 2026-10-11

The owner reported that the RetroArch page would not load over the home router
VPN while AAP and the cluster console remained reachable. Live inspection found
RetroArch restricted to `10.45.45.0/24`, with no route IP allowlist on AAP or the
console. A VPN source-address mismatch is the leading explanation; the affected
VPN's source address has not been captured.

At the owner's request, Helm revision 3 allows `10.0.0.0/8`, `172.16.0.0/12`, and
`192.168.0.0/16`. This admits any reachable private-IPv4 source to the login
screen. Authentication remains required; IPv6 and other source ranges are not
included.

| Check | Result and evidence |
| --- | --- |
| Local validation | `scripts/check.sh` passed: shell syntax, Helm lint, ten unit tests, and core-bundle integrity. Tests cover default private ranges, custom overrides, and rejection of an empty allowlist. |
| Change comparison | Parsed rendered manifests matched the previous Helm release except for the Route allowlist. Pinned images and pod configuration were unchanged. |
| Cluster validation and deployment | Server-side dry run and deployment preflight passed. `scripts/deploy.sh -f deployment.lock.json` deployed revision 3 successfully. Existing GPU-plugin PodSecurity warnings were unchanged. |
| Live route | Verified all three private ranges, edge TLS with HTTP redirect, forwarded-header replacement, and the one-hour tunnel timeout. |
| DNS and HTTPS from the execution Mac | Host resolved to `10.45.45.6`; certificate verification passed; anonymous request returned 401 and authenticated request returned 200. These requests did not open or take over the streaming session. |
| Running session | Application pod UID, image ID, and zero restart count matched the pre-deployment baseline; the pod remained ready. |
| VPN and gameplay | Pending owner test from the affected VPN device: login, video, audio, controller input, browser reload/reconnect, and ten minutes of use. The execution Mac's successful request does not establish affected-device VPN acceptance or a separate LAN gameplay result. |
| Denied-source connection | Pending: no suitable connection outside the allowed ranges was available. The configured allowlist was verified, but no live negative-source test was performed. |

Local evidence is in ignored `recovery/vpn-private-ipv4/baseline.json` and
`verification.json`. Rollback target is revision 2:
`helm rollback retroarch 2 -n retroarch --wait`; revert the chart's allowlist
to `10.45.45.0/24` as well if rollback is needed.

If the VPN page still fails to load, compare DNS and TCP/TLS connectivity with
AAP and inspect router configuration/available ingress logs for the actual VPN
source. If login succeeds but streaming fails, diagnose WebSocket transport
separately. Do not mark the VPN issue resolved until the affected-device test
passes.

## Manual acceptance still required

- Beyond confirmed menu navigation, verify Xbox Series controller over Bluetooth
  with current macOS/Chrome: face buttons,
  D-pad, shoulders, analog triggers, both sticks/clicks, Start/Select/menu.
- Bluetooth disconnect/reconnect, browser reload, focus loss, stuck-input checks.
- Representative NES, SNES, GBA, PS1, N64, Dreamcast and PSP content supplied by
  the owner, with required BIOS files. Verify analog and OpenGL/Vulkan cases.
- Thirty minutes of gameplay without growing latency or sustained audio breakup.
- High-frame-rate video measurement of button-to-visible response: target median
  below 100 ms on LAN. Record VPN separately; stream RTT is not input latency.
- Optional rumble; Guide/Share are not guaranteed through the browser.
- Enforced offline startup and browser use: `scripts/offline-smoke.py` is ready
  but has not been run. It restarts the session and temporarily denies egress.
- Verify the newly created game save and playlist after a subsequent replacement
  and upgrade. Configuration/profile persistence and scratch backup restoration
  have passed; a production state restore has not been performed.
- VPN source addressing and access under the private-IPv4 allowlist; results
  must be recorded separately from LAN use. See the revision 3 update above.
- Controlled GPU unavailability, storage outage, and worker restart drills. The
  recovery procedure is documented in the README but outage drills remain pending.

Use owner-supplied games and BIOS files for the remaining gameplay matrix. No
commercial games or BIOS files were supplied with this deployment. Copy the
verified recovery archive and versioned core bundle to off-machine backup.
