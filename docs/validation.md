# Validation record

Deployment completed on **2026-10-10** at
https://retroarch.apps.sno.batchelor.live, Helm release `retroarch`, revision 2.
The owner confirmed that the real Xbox controller works for menu navigation
through the Route. The session was left running for their use.

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
- Secret-backed personal authentication, trusted edge TLS, LAN source allowlist,
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
- VPN source addressing and allowlist access; results must be recorded separately
  from LAN use. Only `10.45.45.0/24` is currently allowed.
- Controlled GPU unavailability, storage outage, and worker restart drills. The
  recovery procedure is documented in the README but outage drills remain pending.

Use owner-supplied games and BIOS files for the remaining gameplay matrix. No
commercial games or BIOS files were supplied with this deployment. Copy the
verified recovery archive and versioned core bundle to off-machine backup.
