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

## Left-stick movement update — 2026-10-16

Installed player 1 core remaps for Gambatte, mGBA, and melonDS DS in the live
state PVC's `~/.config/retroarch/remaps/<core>/<core>.rmp` files. Each contains
only `input_player1_analog_dpad_mode = "3"` (Left Analog, Forced). This adds
left-stick directional input while retaining the existing D-pad and keyboard
bindings. All games in these three cores receive the default.

| Check | Result and evidence |
| --- | --- |
| Live prerequisites | Automatic remap loading and input remapping were enabled; no existing `.rmp` files were present. Core library names were confirmed as `Gambatte`, `mGBA`, and `melonDS DS`. |
| Local validation | `RETROARCH_PYTHON=.cache/venv/bin/python scripts/check.sh` passed: shell syntax, Helm lint, ten unit tests, and core-bundle integrity. |
| Startup seeding | Executed the entrypoint's seeding block against temporary directories: all three defaults copied correctly, including names with spaces; a missing remap was restored; a customized remap was preserved byte-for-byte; repeated runs were idempotent. |
| Live installation | All three persistent remaps match the repository defaults, SHA-256 `1d0564d4fcc289678cdaff4dfca0cc8a09a0d35d51025446049aaf59fd8f5868`. Global configuration and SDL2 controller profile hashes were unchanged. Existing deadzone `0.0` and axis threshold `0.5` were retained. |
| Session continuity | RetroArch PID remained `97386`; no browser takeover, content reload, or application/pod restart was performed. Save, close, and reopen content to load the new remap. |
| Image integration | Containerfile now bundles the defaults and the entrypoint seeds only missing remaps. The image was not rebuilt or rolled out during this update; the live installation is on persistent storage and survives pod replacement. Future image builds include startup seeding for fresh state. |
| Gameplay acceptance | Pending physical-controller tests in each core: D-pad and left stick independently move the character, switching between them requires no setting change, releasing the active control stops movement, keyboard movement remains usable, and DS touch controls still work. These results are not established by file/hash verification. |

Installation evidence is in ignored `recovery/left-stick-remaps/installation.json`.
To undo the added movement, set **Quick Menu → Controls → Port 1 Controls →
Analog to Digital Type → None**, then **Controls → Manage Remap Files → Save Core
Remap File**, for each core. The saved preference is preserved on startup.

## SoulSilver Lapras encounter cheat — 2026-10-18

Inspected the owner's SoulSilver header: USA game code `IPGE`, revision `0`.
Recent content history selects melonDS DS; its bundled core metadata advertises
cheat support. Uploaded
`cheats/Pokemon - SoulSilver Version (USA) - Lapras.cht` from this repository to
`/home/ubuntu/.config/retroarch/cheats/Nintendo - Nintendo DS/` on the state PVC.
The file contains one disabled, emulator-handled Action Replay cheat.

The code is adapted from the [Libretro SoulSilver USA database's Wild Pokemon
Modifier v1](https://github.com/libretro/libretro-database/blob/master/cht/Nintendo%20-%20Nintendo%20DS/Pokemon%20-%20SoulSilver%20Version%20%28USA%29.cht).
It retains the DS L-button condition, pointer guard, and encounter-table loop,
but replaces the bag-quantity read with the constant species ID `131` (`0x83`).
The bag initialization and level modifier are omitted. The D5 constant-load and
D7 halfword-write operations were checked against melonDS's AR interpreter.

Verified seven correctly formatted instruction pairs, the species ID, disabled
default, emulator handler, and matching local/remote SHA-256
`ab122067b2361579b303f7f59920e45e06d4837bb3c64343f270338564780ef4`.
RetroArch PID `97386` and the global configuration hash were unchanged. No
cheat was enabled, gameplay driven, save edited, or session restarted.
Installation evidence: ignored `recovery/lapras-cheat/installation.json`.
Actual Lapras encounter/capture remains untested.

To use: save in-game, open **Quick Menu → Cheats → Load Cheat File (Replace)**,
choose **Nintendo - Nintendo DS → Pokemon - SoulSilver Version (USA) - Lapras.cht**,
enable the entry, and select **Apply Changes**. Hold DS L (Xbox LB) while walking
in grass until an encounter starts. Release LB during battle. After catching,
disable the cheat and apply changes, save in-game, then close/reopen content and
use the game's Continue option to clear the modified encounter table. This is
not an automatic one-encounter code; disabling alone does not restore RAM writes.

### Surfing correction — 2026-10-18

The owner reported no Lapras while holding LB and surfing. The first version
modified land/radio encounter species only; surfing has separate slots.
Updated the same file with description **Lapras - grass + SURF v2 - hold L
(Xbox LB)**. The five surfing species halfwords are at pointer-relative offsets
`0x32A9A`, `0x32A9E`, `0x32AA2`, `0x32AA6`, and `0x32AAA`; the surfing swarm
species is at `0x32AF2`. These are derived from the original land-species offset
and the [HG/SS encounter data structure](https://github.com/pret/pokeheartgold/blob/master/include/wild_encounter.h).
Writes run before the existing land loop, under the same L-button and non-null
pointer conditions. Levels, encounter rates, and fishing tables are preserved.

A synthetic-memory simulation of the AR instructions verified all 46 species
writes, unchanged surrounding bytes, and zero writes with L released or a null
pointer. This is a code/layout check, not an in-game encounter test. The upload
matches SHA-256 `b302712027e240dace61877e83a515e693e6bc8abe2b670ee1ae60b40eaeb5d7`;
the original file is backed up under `cheats/.backups/lapras-grass-v1.cht.bak` on
the state PVC. Global configuration and RetroArch PID `97386` were unchanged.
Evidence: ignored `recovery/lapras-cheat/surf-v2-installation.json`.

The owner must **Load Cheat File (Replace)** again to load the updated file into
the running session, confirm **grass + SURF v2**, enable it, and **Apply Changes**.
Hold LB while surfing in water that normally has wild encounters, with Repel
expired. The modifier changes encounter species; it does not force an encounter
immediately. The disable/save/reopen instructions above still apply. Surfing
gameplay acceptance remains pending.

## SoulSilver unlimited Master Balls — 2026-10-18

Uploaded `cheats/Pokemon - SoulSilver Version (USA) - Unlimited Master Balls.cht`
to the state PVC under
`/home/ubuntu/.config/retroarch/cheats/Nintendo - Nintendo DS/`.
Rechecked ROM game code `IPGE`, revision `0`. The disabled-by-default,
emulator-handled code retains the pointer guard and first Poké Ball slot write
from the [Libretro SoulSilver USA database's Poke Balls (Default) code](https://github.com/libretro/libretro-database/blob/master/cht/Nintendo%20-%20Nintendo%20DS/Pokemon%20-%20SoulSilver%20Version%20%28USA%29.cht).
It continuously writes item ID `1` and quantity `999` (`0x03E70001`) at
pointer-relative offset `0xDCF4` while enabled, without a button condition.
It replaces the first ball stack; other slots are not written. The description
and file comments explicitly identify this behavior.

Verified the four instruction pairs with a synthetic bag buffer: a null pointer
produces no writes; a valid pointer writes only the first four-byte ball slot,
with the expected item/quantity. Uploaded SHA-256 matches the local file:
`6909fd94719923bfc29ff49faee4235acc2967bf064d1963f5ad24a9a6442cc5`.
Global config, the Lapras cheat, and RetroArch PID `97386` were unchanged.
Evidence: ignored `recovery/master-balls-cheat/installation.json`.
Actual in-game replenishment has not been tested.

Save in-game before activation. Use **Quick Menu → Cheats → Load Cheat File
(Append)** to retain the Lapras entry, select the Master Balls file, enable its
entry, and **Apply Changes**. Resume before reopening the bag. No button press
is required. Avoid rearranging the ball pocket while enabled. Turn it off and
apply changes to stop refilling; balls already added remain and can be saved.

## SoulSilver Game Corner coins — 2026-10-18

Uploaded `cheats/Pokemon - SoulSilver Version (USA) - Max Game Corner Coins.cht`
to the persistent `~/.config/retroarch/cheats/Nintendo - Nintendo DS/` folder.
The single disabled emulator-handled entry uses the unchanged **Max/Infinite
Coins** code from the [Libretro SoulSilver USA database](https://github.com/libretro/libretro-database/blob/master/cht/Nintendo%20-%20Nintendo%20DS/Pokemon%20-%20SoulSilver%20Version%20%28USA%29.cht).
DS L+R (Xbox LB+RB) sets the 16-bit coin count at pointer-relative offset
`0xD074` to `0xC350` (50,000), guarded by a non-null pointer at `0x0211186C`.
It does not add a Coin Case or modify other currencies or bag slots.

Rechecked ROM code `IPGE`, revision `0`; validated the five AR instruction pairs
against the published code. Local and remote SHA-256 match:
`ad9772bf52960feb2ea9be70d9485e7abf0749fbf2ef73957248f92b83dd5d69`.
Existing cheat files, global config, and RetroArch PID `97386` were unchanged.
Evidence: ignored `recovery/game-corner-coins-cheat/installation.json`.
Actual coin refill and prize purchase remain untested.

Save in-game, **Load Cheat File (Append)**, select the new file, enable its entry,
and **Apply Changes**. Resume and press LB+RB together, then reopen the Coin Case
or prize menu. Disable the entry and apply changes after refilling; the coins
remain and can be saved. This does not require a session or pod restart.

## SoulSilver five Oran Berries — 2026-10-19

Uploaded `cheats/Pokemon - SoulSilver Version (USA) - 5 Oran Berries.cht` to
the persistent `~/.config/retroarch/cheats/Nintendo - Nintendo DS/` folder.
Rechecked USA game code `IPGE`, revision `0`. The disabled emulator-handled
entry replaces the first berry stack with five Oran Berries when DS L+R
(Xbox LB+RB) is pressed. It sets the quantity to five, rather than adding five.

Uses the pointer guard and berry-pocket base from the [Libretro SoulSilver USA
Berries code](https://github.com/libretro/libretro-database/blob/master/cht/Nintendo%20-%20Nintendo%20DS/Pokemon%20-%20SoulSilver%20Version%20%28USA%29.cht),
reduced to one 32-bit write at pointer-relative `0xDBF4`. Value `0x0005009B`
encodes quantity five and item ID 155, checked against the
[HG/SS item constants](https://github.com/pret/pokeheartgold/blob/master/include/constants/items.h).
Synthetic-memory checks covered neither/one/both shoulder buttons and null/valid
pointers: only L+R with a valid pointer writes, and only the first berry slot
changes. No live bag or save modification was performed.

Verified matching local/remote SHA-256
`226d8378f373cb7f3248a1c56742459e86f6f893a3465df904b0560943a75bc7`.
Global configuration, existing cheats, and running RetroArch PID `169163` were
unchanged during upload. Evidence: ignored
`recovery/oran-berries-cheat/installation.json`. In-game refill remains untested.

Save in-game; **Load Cheat File (Append)**, select the file, enable the entry,
and **Apply Changes**. Resume, press/release LB+RB, and reopen the bag. Disable
and apply changes before feeding Moomoo or rearranging berries. Moomoo requires
[seven Oran Berries total](https://bulbapedia.bulbagarden.net/wiki/Moomoo_Farm);
repeat the five-berry refill if needed. Existing berries in the first slot are
replaced; all other slots remain untouched by this code.

## White 2 unlimited Master Balls — 2026-10-19

Confirmed the recently loaded White Version 2 ROM is USA/Europe, game code
`IRDO`, revision `0`, using melonDS DS. Uploaded
`cheats/Pokemon - White Version 2 (USA, Europe) - Unlimited Master Balls.cht`
to persistent `~/.config/retroarch/cheats/Nintendo - Nintendo DS/`.

Adapted the [Libretro White Version 2 USA/Europe All Items code](https://github.com/libretro/libretro-database/blob/master/cht/Nintendo%20-%20Nintendo%20DS/Pokemon%20-%20White%20Version%202%20%28USA%2C%20Europe%29.cht)
to a single four-byte inventory write. The non-null pointer guard at `0x0209A378`
is retained; pointer-relative `0x18A38` receives `0x03E70001` (Master Ball ID 1,
quantity 999), without a button condition. This replaces the first Items-pocket
stack and replenishes while enabled. The file clearly labels the replacement
and starts disabled with emulator handling.

Synthetic-memory validation checked the pointer guard, item/count encoding,
single-slot write, and unchanged surrounding bytes. Uploaded SHA-256 matches:
`5e81eee663407a717605a386297fef9c1f57cb7bb1bbb88bb280fbddd804ba23`.
Global config, existing cheats, and RetroArch PID `169163` were unchanged.
Evidence: ignored `recovery/white2-master-balls-cheat/installation.json`.
In-game replenishment remains untested.

Save in-game with White 2 loaded, use **Load Cheat File (Replace)** to select
this White 2 file, enable it, and **Apply Changes**. Resume and reopen the bag;
no button combination is required. Do not load SoulSilver codes in White 2.
Avoid sorting/reordering Items while enabled. Disable and apply changes to stop
refilling; the existing balls remain and can be saved.

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
