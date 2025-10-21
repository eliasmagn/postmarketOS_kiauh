# Roadmap

## Near Term
- Validate apk-based installations on multiple postmarketOS devices and document any device-specific steps.
- ✅ Normalize cross-compilation toolchain package names for Alpine/postmarketOS so apk installs succeed on stock mirrors.
- ✅ Expand the package translation table as additional dependencies are encountered during component installs; track follow-up actions for packages without Alpine ports (`packagekit`, `libcamera-apps-lite`).
- ✅ Detect the active init system and wire service management to both systemd and OpenRC so installers and maintenance flows stay in sync.
- ✅ Ship Wayland launcher presets for Phosh/Plasma along with auto-generated KlipperScreen display defaults so mobile shells behave out of the box.
- ✅ Mirror Sxmo's wlroots session exports so Qualcomm msm8953 reference images boot KlipperScreen without manual environment tweaks.
- ✅ Auto-configure KlipperScreen autostart across Phosh/Plasma desktops and OpenRC consoles while keeping Moonraker's update-manager systemd hints optional.
- ✅ Publish postmarketOS-specific prerequisites covering SSH access, UI packages, and seat management so the new presets work on phones and tablets.
- ✅ Replace KlipperScreen's upstream installer with an apk-aware wrapper so X11 and Wayland dependencies resolve correctly on postmarketOS.
- ✅ Ship a native OpenRC KlipperScreen service so standalone installs boot directly into the UI without systemd dependencies.
- ✅ Apply Xwrapper console permissions during apk installs so OpenRC-managed KlipperScreen services can start Xorg successfully.
- ✅ Inject a default `KS_XCLIENT` fallback into `KlipperScreen-start.sh` so post-install services and manual runs always launch the UI.
- ✅ Stage the Wayland preset helper after the backend selection so X11-first installs progress without unrelated prompts.
- ✅ Trim the KlipperScreen dependency footprint by default and prompt before installing optional extras.
- ✅ Remove forced reboots from KlipperScreen's NetworkManager install step and replace them with manual reminders for safer unattended runs.
- ✅ Detect the active NGINX include directory (conf.d vs http.d) so Fluidd installs succeed on Alpine/postmarketOS hosts without manual intervention.
- ✅ Fix web UI detection when generating example `printer.cfg` files so Mainsail/Fluidd include stanzas are added automatically after installation.
- ✅ Harden NGINX port detection so missing site configs fall back to the stored defaults instead of aborting the installer menus.
- ✅ Reuse Moonraker's Debian dependency manifest on apk-based systems while translating package names so installations no longer abort when the JSON lacks an Alpine entry.
- ✅ Handle Moonraker's policykit helper on BusyBox-based postmarketOS installs by auto-installing GNU `grep` when `grep -P` is unavailable and retrying the rule setup.
- ✅ Ship an apt-compatible Moonraker update-manager drop-in on apk-based systems so the Update Manager works without PackageKit while keeping the policykit helper intact and warning-free.
- ✅ Offer guided nftables allow-rule prompts for Moonraker and web UIs with selectable network scopes on nftables-enabled hosts.
- ✅ Provide an apk-aware crowsnest deployment that renders config templates and installs an OpenRC service so Fluidd/Mainsail webcams stream on postmarketOS.
- ✅ Offer optional WireGuard provisioning so remote access can ride an encrypted tunnel alongside the nftables automation.
- ✅ Pause spinner-driven loading messages whenever sudo interactions are required so update prompts stay visible to the user.
- ✅ Point the self-update routine at the postmarketOS community fork by default while keeping an escape hatch for personal forks via `KIAUH_REPO_URL`.
- Automate KlipperScreen smoke tests on representative postmarketOS handsets/tablets to validate display heuristics after each release.
- Collect tester feedback and grow the public compatibility matrix with device-specific init/display notes.

## Mid Term
- Introduce automated detection for other lightweight distributions (e.g., OpenWrt derivatives) while keeping Debian compatibility intact.
- Provide localized documentation updates mirroring the primary README changes.
- Coordinate with KlipperScreen maintainers and Alpine/postmarketOS package maintainers to upstream the Wayland wrapper and dependency fixes.

## Long Term
- Explore a plugin-based dependency resolver so that package translations can be shipped without touching the core logic.
- Build a continuous integration smoke test that exercises the installer on both Debian and Alpine containers.
- Investigate automated flashing and regression testing hooks for actual postmarketOS hardware in CI once device farms are available.
