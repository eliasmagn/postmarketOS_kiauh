# Project Concept

KIAUH (Klipper Installation And Update Helper) streamlines the setup and maintenance of Klipper-based 3D printing stacks. This fork extends the original concept by ensuring that the helper also works on Alpine Linux derivatives such as postmarketOS. Detecting the available system package manager and translating dependency names keeps the installation flow consistent across distributions while preserving the familiar menu-driven user experience.

The project focuses on:

- Capturing handset and tablet ergonomics—navigation, scaling, and orientation heuristics—so the mobile UX feels native on postmarketOS touch shells.
- Automating environment preparation for Klipper, Moonraker, and companion tools.
- Providing a resilient installation experience across multiple Linux families.
- Replacing disruptive post-install reboots with clear guidance so scripted deployments can finish gracefully.
- Maintaining documentation that highlights platform-specific nuances for end users.
- Accepting case-insensitive yes/no responses—including numeric toggles like `1`/`0`—so touch keyboards and remote terminals
  can breeze through prompts without tripping validation.
- Tracking Debian package requirements in each installer and pairing them with Alpine `apk` equivalents—cross-compilation toolchains included—so postmarketOS users can reproduce the same setup flow without manual package hunting.
- Documenting kernel configuration expectations so custom postmarketOS builds ship with the drivers Klipper, Moonraker, KlipperScreen, and crowsnest rely on.
- Reading `/etc/os-release` to prefer the native package manager on each device so postmarketOS hosts stop tripping over compatibility shims that accidentally expose `apt-get`.
- Steering the self-update routine toward the postmarketOS community fork by default while still allowing personal forks to override the `origin` remote through `KIAUH_REPO_URL`.
- Normalizing Moonraker's Debian-centric dependency manifests so apk-based systems transparently reuse and translate the same requirements without aborting the install flow.
- Detecting BusyBox-specific tool limitations (for example, the absence of `grep -P`) and automatically installing the missing GNU utilities so Moonraker's policykit configuration succeeds on postmarketOS.
- Shipping an apt-compatible Moonraker update-manager drop-in for apk-based installs so the Update Manager keeps working without PackageKit while the policykit helper remains intact.
- Replacing upstream-only installers with apk-aware shims when necessary so features like KlipperScreen's X11 session remain first-class citizens alongside the newer Wayland presets.
- Ensuring CLI feedback remains accessible by pausing spinner-driven status messages whenever privileged prompts appear, keeping sudo password requests visible during update flows.
- Offering optional sudo credential caching that only prompts the first time a privileged action runs, keeping tasks moving after a single consent while clearing the timestamp again on exit.
- Detecting minimal sudo shims that lack timestamp management flags and gracefully skipping the caching flow so unsupported option errors never interrupt menu rendering.
- Guarding loading indicator teardown so menus can dismiss spinners even when the animation never started, preventing stray exceptions from interrupting long-running update flows.
- Detecting the active init system and routing all service lifecycle operations through a shared abstraction so that both systemd and OpenRC hosts behave identically.
- Surfacing mobile-shell aware launch presets and display heuristics so touch-friendly environments (Phosh, Plasma Mobile, Sxmo, etc.) get a usable KlipperScreen session without manual environment plumbing.
- Offering a panorama-orientation prompt that rewrites KlipperScreen defaults and seeds an X11 helper so wide touch panels report horizontal resolutions without extra manual tweaks.
- Mirroring postmarketOS' `monitor-sensor` auto-rotation guidance with a KlipperScreen helper that spawns alongside the launcher, honours backend hints, waits for the target display server to come up, and rotates the selected output through `wlr-randr`/`xrandr` whenever the accelerometer fires.
- Keeping KlipperScreen's width/height overrides anchored inside the `[main]` section so panorama mode and autodetected defaults stay effective even when printers add their own config blocks.
- Accounting for distribution-specific filesystem layouts—like alternative NGINX configuration directories or the absence of Debian-style site folders—so web interfaces install without manual path fixes.
- Pre-provisioning `/etc/nginx/sites-available` and `/etc/nginx/sites-enabled` when they are missing and streaming generated site definitions directly into place with `sudo tee` so doas-backed systems never lose the template to tmpdir cleanup before it lands in `/etc/nginx`.
- Accounting for distribution-specific filesystem layouts—like alternative NGINX configuration directories—and proactively creating missing `conf.d` targets—then seeding them before writing the `kiauh-sites.conf` drop-in—so stock nginx configurations immediately load the generated sites without manual path fixes.
- Inspecting `/etc/nginx/nginx.conf` to discover which include directory (`conf.d` or `http.d`) the active configuration loads when both exist so generated drop-ins land where nginx actually reads them.
- Streaming generated NGINX site definitions directly into privileged paths with `sudo tee` so doas-backed systems never lose the template to tmpdir cleanup before it lands in `/etc/nginx`.
- Ensuring generated printer configuration templates automatically link the installed web UIs (Mainsail, Fluidd, etc.) so fresh Klipper instances keep their dashboards reachable without manual edits.
- Falling back to sane defaults when expected NGINX site stanzas are absent, keeping menu flows responsive instead of crashing on missing configs.
- Detecting nftables-based firewalls and layering guided prompts that open Moonraker and Fluidd ports only for the networks you approve, keeping phones and tablets reachable without exposing them broadly by default.
- Supplying actionable fallback guidance when the default nftables input chain is missing so users know to consult the postmarketOS firewall documentation before proceeding.
- Replacing crowsnest's Debian-centric installer with an apk-aware deployment path that renders the upstream configuration and provisions an OpenRC service so Fluidd and Mainsail webcam panels stay functional on postmarketOS.
- Standardizing warning and attention messaging through the shared logger helpers so user prompts stay consistent across installers and extensions.
- Offering optional WireGuard provisioning so remote access can ride an encrypted tunnel without hand-authoring VPN configs on postmarketOS devices.
- Surfacing mobile-shell aware launch presets and display heuristics so touch-friendly environments (Phosh, Plasma Mobile, etc.) get a usable KlipperScreen session without manual environment plumbing.
- Sequencing installer prompts so Wayland-specific choices only surface after the user opts into the Wayland backend, keeping the X11-first flow streamlined while preserving the option to revisit presets later.
- Adapting KlipperScreen autostart to the surrounding shell—desktop environments receive `.desktop` launchers while console-only OpenRC systems get login hooks that wait for Moonraker before spawning the UI.
- Auto-enabling the generated Wayland autostart services by talking to `systemd --user` when available or wiring OpenRC runlevel symlinks so fresh presets boot without manual follow-up.
- Provisioning a first-party OpenRC service for KlipperScreen's standalone flow so console boots spawn the UI without relying on systemd units.
- Writing console-safe Xwrapper policies on apk-based hosts so the OpenRC KlipperScreen service can bring up Xorg without elogind.
- Hardening upstream launchers with default `KS_XCLIENT` fallbacks so ad-hoc invocations still boot the touch UI even when init systems skip the expected environment exports.
- Defaulting installers to the minimum viable dependency footprint and offering optional extras as explicit opt-ins so mobile deployments stay lightweight.

As the scope expands beyond SBCs, we treat touch-first UX goals—gesture-ready launchers, portrait rotation defaults, and low-power service policies—as first-class citizens so postmarketOS phones and tablets can host Klipper without desktop-era compromises.
