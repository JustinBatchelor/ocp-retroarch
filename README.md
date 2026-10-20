# RetroArch on OpenShift

Personal native Linux RetroArch session on `worker-0`, streamed by Selkies over
HTTPS/WebSockets at **https://retroarch.apps.sno.batchelor.live**. See
[validation results](docs/validation.md) for actual deployment and test status.

## Use

1. Connect to the LAN or home VPN using private IPv4 addressing (see
   [Security and networking](#security-and-networking)). Run `scripts/show-login.sh` in your own terminal to
   retrieve the generated personal login from OpenShift.
2. Pair an Xbox Series X/S controller with the Mac over Bluetooth. Open the Route
   in current Chrome, sign in, click the session to enable audio, and press a
   controller button. Enable gamepad input in the Selkies sidebar if necessary.
3. Upload your ROMs through Selkies **Files → Upload Files**. Individual uploads
   land in `/library`; see [Adding games later](#adding-games-later) for organized
   imports, playlists, and BIOS placement.
4. Use RetroArch's Load Content, Load Core, and Import Content menus. The virtual
   controller profile maps physical Xbox positions to RetroPad positions:
   Xbox A → RetroPad B; Xbox B → RetroPad A; Xbox X → RetroPad Y;
   Xbox Y → RetroPad X. Start+Select opens the menu; keyboard F1 is a fallback.
5. Save controller and per-core remaps in RetroArch. Rumble, Guide/Share buttons,
   and specialized peripherals are not acceptance requirements.

One session is shared by every authenticated tab. Close other tabs while playing.
Opening a new primary browser disconnects the previous one.
The login grants access to the session and library; do not distribute it as a
multi-user account. Browser reconnect resumes the running session. Pod/node
replacement restarts RetroArch; reload content and use saved progress.

## Adding games later

Use game files you are authorized to use, such as your own cartridge backups.
ROMs and BIOS files are not included in this project. Adding games does not
require an image build, Helm upgrade, or pod restart.

### Upload and play through the browser

1. Open the Route and sign in. Expand the Selkies sidebar, open **Files**, and
   choose **Upload Files**. Select your game files and wait for completion.
   This deployment's upload root is `/library`: individual files go directly
   there, not automatically into `/library/roms` or `/library/incoming`.
   **Download Files** lets you browse the library and confirm the upload.
2. Prefer extracted `.gb`, `.gbc`, `.gba`, or `.nds` files for the systems below.
   Extract ZIP/7z archives on your Mac before uploading to avoid core-dependent
   archive behavior. Keep each game version under a distinct filename so uploads
   and saves do not overwrite another version.
3. In RetroArch, select **Load Core** and choose the appropriate installed core
   from the table below. Then choose **Load Content**, navigate to `/library`
   (use the parent directory if the browser starts in `/library/roms`), and open
   the uploaded game. Loading content directly does not require a playlist scan.
4. Press Start+Select or keyboard F1 for the Quick Menu. Use **Close Content**
   after saving in-game. Saves and save states persist on the state PVC.

### Organize a larger library from the Mac

Create folders named `gb`, `gbc`, `gba`, and `nds` inside a local `ROMs` folder,
and put the appropriate extracted game files inside each. With `oc` logged into
this cluster, copy the folder contents into persistent library storage:

```sh
retroarch_pod=$(oc -n retroarch get pods -l app=retroarch -o jsonpath='{.items[0].metadata.name}')
oc -n retroarch rsync --strategy=tar "$HOME/ROMs/" "$retroarch_pod:/library/roms/"
```

Change `$HOME/ROMs/` to your actual source directory. The trailing slash copies
its contents. The tar strategy works with the tools installed in this image.
This command does not delete remote files absent from the source;
matching destination filenames can be updated, so keep existing game versions
and their saves when replacing a ROM. You can also copy one file explicitly:

```sh
oc -n retroarch exec "$retroarch_pod" -- mkdir -p /library/roms/gba
oc -n retroarch cp "$HOME/ROMs/gba/Your Game.gba" "$retroarch_pod:/library/roms/gba/Your Game.gba"
```

### Add games to playlists

In the installed RetroArch 1.20 interface, open **Import Content → Manual Scan**.
Choose the relevant **Content Directory** (for example `/library/roms/gba`),
**System Name**, and **Default Core**. Set **File Extensions** to `gba` for GBA,
`gb gbc` for a mixed Game Boy folder, or `nds` for DS, without leading dots.
Enable **Scan Recursively** if needed and select **Start Scan**. Repeat for each
system. For later additions, repeat with **Overwrite Existing Playlist** off;
use **Settings → Playlists → Manage Playlists** to refresh or clean an existing
playlist. Avoid moving files after scanning, because playlist paths refer to
their location on the server.

Manual Scan is useful when an automatic database scan does not recognize a game.
See the [official playlist guide](https://docs.libretro.com/guides/roms-playlists-thumbnails/).
Playlists are stored on the state PVC under
`/home/ubuntu/.config/retroarch/playlists`; ROMs remain on the library PVC.

### Pokémon Generations 1–5

This is the intended English-language main-series collection, including remakes
released during those generations. No Pokémon ROMs have been installed.

| Generation | Games | System / file | Installed core |
| --- | --- | --- | --- |
| 1 | Red, Blue, Yellow | Game Boy / `.gb` | Gambatte |
| 2 | Gold, Silver, Crystal | Game Boy Color / `.gbc` | Gambatte |
| 3 | Ruby, Sapphire, Emerald, FireRed, LeafGreen | Game Boy Advance / `.gba` | mGBA |
| 4 | Diamond, Pearl, Platinum, HeartGold, SoulSilver | Nintendo DS / `.nds` | melonDS DS |
| 5 | Black, White, Black 2, White 2 | Nintendo DS / `.nds` | melonDS DS |

Regional editions, including Japanese Green, can be added separately. These
three cores passed the native load check; Pokémon gameplay has not been tested.
Choose **melonDS DS**, since the older **melonDS** binary in this bundle fails
to load. DS games also need a usable bottom-screen/touch layout; configure that
under the loaded core's options and test pointer/controller behavior in-game.

For these three cores, player 1 can use either the **D-pad or left analog stick**
for movement and switch between them during gameplay. The core remaps set
**Analog to Digital Type → Left Analog (Forced)**; D-pad and keyboard bindings,
buttons, right-stick settings, and existing sensitivity remain unchanged.
This applies to all games in these cores, including non-Pokémon games.

To customize this while a game is loaded, open **Quick Menu → Controls →
Port 1 Controls → Analog to Digital Type**, then use **Controls → Manage Remap
Files → Save Core Remap File**. Game or content-directory remaps take precedence
over the core default. Defaults are installed only when the corresponding core
remap is missing, so saved customizations survive container startup. When remaps
are installed during a running session, save in-game, close content, and reopen
it to load the new controls; a pod restart is unnecessary.

Place any required BIOS files in `/library/bios`, preserving the exact filenames
and any core-specific subdirectories. For example, copy a BIOS from your Mac
using `oc cp` with `/library/bios/<filename>` as the destination. Uploading it to
the browser's `/library` root alone does not put it in the configured BIOS folder.
Check **Main Menu → Information → Core Information** after loading a core.

Gambatte and mGBA document optional boot BIOS files. For melonDS DS, DS-mode
BIOS/firmware files are optional; DSi mode requires additional system files.
Start with DS mode for the DS cartridge games above. Consult the exact filenames
and checksums in the official [Gambatte](https://docs.libretro.com/library/gambatte/),
[mGBA](https://docs.libretro.com/library/mgba/), and
[melonDS DS](https://docs.libretro.com/library/melonds_ds/) documentation.
Game saves live under `/home/ubuntu/.config/retroarch/saves`, save states under
`/home/ubuntu/.config/retroarch/states`; back up both state and library storage.

## Build and deploy

Requires `oc` with administrator access, Helm 3, Python 3, and Podman. The Mac
builder must support Linux AMD64 execution. The host GPU already uses `amdgpu`;
do not replace it with ROCm or bind it to VFIO for this deployment.

```sh
scripts/bootstrap.sh
python3 scripts/core-bundle.py fetch
scripts/build.sh
scripts/mirror.sh
scripts/deploy.sh -f deployment.lock.json
scripts/verify.sh
```

`images.lock.json` pins upstream images. `deployment.lock.json` records the
digests actually pushed to the internal registry. `cores.lock.json` identifies
every downloaded core/info archive and extracted file by SHA-256. A locked fetch
refuses changed upstream content; retain `vendor/core-bundle` in an off-machine
backup because the upstream nightly URLs are mutable. Preserve upstream licenses
when distributing images or core binaries; no ROMs or BIOS are included.

The core bundle is copied into a versioned directory on the library PVC once.
The image chooses its corresponding directory on startup. Availability in the
catalog is not a guarantee a core loads or a particular game works. The runtime
probe reports library/dependency failures; gameplay/BIOS requirements are tested
separately. Updates through RetroArch's online updater are disabled to preserve
the tested bundle. Installed content is designed to work without internet access;
the enforced-offline acceptance test remains pending.

The native load check passes for 241 of 243 cores. This snapshot's FS-UAE has an
unresolved `esp_scsi_init` symbol; legacy melonDS requests an executable stack
rejected by the runtime. PUAE and melonDS DS are included as alternative cores
for those systems, though game compatibility remains a separate test. See
[the complete catalog report](docs/core-compatibility.json).

The namespace contains two retained NFS PVCs: 250 GiB library and 20 GiB state.
NFS requested capacity is not a dataset quota. Monitor space and back up the
TrueNAS dataset itself. Keep host OS storage out of the game library.

## Security and networking

The Route uses the cluster certificate, redirects HTTP to HTTPS, replaces
forwarded headers, and permits all private IPv4 ranges: `10.0.0.0/8`,
`172.16.0.0/12`, and `192.168.0.0/16`. Any client in those ranges that can reach
the cluster can reach the login screen; authentication is still required.
This includes the LAN and home VPNs whose source address reaches ingress within
those ranges. IPv6 and other source ranges are not included. Override
`route.allowedCIDRs` through Helm values to use a narrower policy.

The allowlist uses the connection source seen by ingress, including any router
address translation. Do not infer a VPN CIDR from a client-supplied HTTP header.
Requests outside the allowed ranges can be dropped before HTTP authentication,
appearing as an empty response. If the page never loads over VPN, compare DNS
and TCP/TLS connectivity with AAP, then check the VPN source address at ingress.
If login works but streaming fails, inspect the browser's WebSocket connections.

The application runs as UID/GID 1000 with no API token, no capabilities, no host
mounts, and no privilege escalation. A dedicated SCC permits the fixed UID and
GPU groups. The GPU plugin has its own service account and privileged SCC access
for kubelet registration and device discovery; only that plugin mounts `/dev`
and kubelet's device-plugin directory. It runs exclusively on `worker-0`.
The application requests one `gaming.batchelor.live/amd-gpu` allocation. Host
SELinux stays enforcing. Do not grant the session the privileged SCC to bypass
a failed hardware test.

WebSocket media and input share port 8080 behind the Route. Selkies provides
30-second WebSocket heartbeat; the Route tunnel timeout is one hour. NetworkPolicy
allows session ingress only from the cluster ingress policy group, including the
host-network sources used by this cluster router. No UDP, host networking, TURN,
or public desktop port is needed for the initial WebSocket transport.

1080p60/H.264 at 15 Mbps is the default, with 4:2:0 color. For 720p60 use
`--set stream.width=1280 --set stream.height=720` on deployment. Browser preferences
can override unlocked Selkies stream settings; inspect active stream statistics.
WebRTC is deferred until measured WebSocket performance justifies extra media
networking; an HTTPS Route alone does not carry WebRTC UDP.

## Backups, updates, recovery

Before upgrading, close content cleanly and run:

```sh
python3 scripts/backup-state.py
```

This pauses the deployment, archives state into ignored `recovery/`, restores it
into scratch storage, compares file hashes, and restarts the previous replica
count. The library/core bundles are separate and need TrueNAS backup. Move recovery
archives off this Mac; a local copy alone does not protect against its disk loss.

For an upgrade, preserve the existing lock files and bundle, acquire a new bundle
in a separate checkout, build and mirror, then deploy and rerun acceptance tests.
Retain the previous image in the internal registry. `helm rollback retroarch
<revision> -n retroarch --wait` restores the deployment and its bundled cores.
Save-state compatibility is core/version dependent; preserve regular in-game saves.

For state recovery: scale the deployment to zero, mount `retroarch-state` in a
temporary non-root maintenance pod using the image recorded in the backup
metadata, verify the archive checksum, and restore the selected trusted archive
into the empty state directory. Restore the matching library/core-bundle backup
if necessary, delete the maintenance pod, and start the recorded image. Do not
extract an arbitrary uploaded archive into application state.

If the GPU plugin or worker is unavailable, the session remains Pending rather
than silently moving to a CPU-only node. If NFS is unavailable, investigate
TrueNAS/network health; do not delete PVCs or substitute ephemeral storage.
Worker restart loses unsaved RAM state. RetroArch flushes save RAM every ten
seconds and saves a state on clean content exit where the core supports it.
An abrupt power loss can still lose progress. Readiness/liveness monitor the
session; the `verify-gpu` command tests rendering and a real hardware encode.

Uninstall with `helm uninstall retroarch -n retroarch`; the PVCs are deliberately
retained. Leave the namespace in place to retain claims and credentials.

## Development checks

```sh
python3 -m venv .cache/venv
.cache/venv/bin/pip install -r requirements-dev.txt
RETROARCH_PYTHON=.cache/venv/bin/python scripts/check.sh
```

The chart refuses unpinned images and multiple independent replicas. Tests cover
archive extraction safety, integrity checks, retained storage, authentication,
and separation of application versus device-plugin privileges. Hardware and
controller acceptance is recorded separately in `docs/validation.md`.

Additional live checks (close other Route tabs first; these take over or restart
the session):

```sh
oc -n retroarch exec -i deployment/retroarch -- bash -s < scripts/core-smoke.sh
.cache/venv/bin/python scripts/browser-smoke.py
.cache/venv/bin/python scripts/offline-smoke.py
```

The core smoke runs bundled ROM-free 2048 through OpenGL and Vulkan, then returns
to the menu. The browser smoke injects synthetic controller input and checks the
server's SDL interface. The offline check temporarily denies application egress,
restarts, verifies controller/save/playlist hashes, and tests self-hosted browser
assets and input. It removes its temporary policy on exit. These checks do not
substitute for the MacBook Bluetooth-controller and latency acceptance tests.
