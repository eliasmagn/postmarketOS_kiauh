# Project Concept

KIAUH (Klipper Installation And Update Helper) streamlines the setup and maintenance of Klipper-based 3D printing stacks. This fork extends the original concept by ensuring that the helper also works on Alpine Linux derivatives such as postmarketOS. Detecting the available system package manager and translating dependency names keeps the installation flow consistent across distributions while preserving the familiar menu-driven user experience.

The project focuses on:

- Capturing handset and tablet ergonomics—navigation, scaling, and orientation heuristics—so the mobile UX feels native on postmarketOS touch shells.
- Automating environment preparation for Klipper, Moonraker, and companion tools.
- Providing a resilient installation experience across multiple Linux families.
- Replacing disruptive post-install reboots with clear guidance so scripted deployments can finish gracefully.
- Maintaining documentation that highlights platform-specific nuances for end users.
- Tracking Debian package requirements in each installer and pairing them with Alpine `apk` equivalents—cross-compilation toolchains included—so postmarketOS users can reproduce the same setup flow without manual package hunting.
- Normalizing Moonraker's Debian-centric dependency manifests so apk-based systems transparently reuse and translate the same requirements without aborting the install flow.
- Detecting BusyBox-specific tool limitations (for example, the absence of `grep -P`) and automatically installing the missing GNU utilities so Moonraker's policykit configuration succeeds on postmarketOS.
- Replacing upstream-only installers with apk-aware shims when necessary so features like KlipperScreen's X11 session remain first-class citizens alongside the newer Wayland presets.
- Detecting the active init system and routing all service lifecycle operations through a shared abstraction so that both systemd and OpenRC hosts behave identically.
- Surfacing mobile-shell aware launch presets and display heuristics so touch-friendly environments (Phosh, Plasma Mobile, Sxmo, etc.) get a usable KlipperScreen session without manual environment plumbing.
- Accounting for distribution-specific filesystem layouts—like alternative NGINX configuration directories—so web interfaces install without manual path fixes.
- Ensuring generated printer configuration templates automatically link the installed web UIs (Mainsail, Fluidd, etc.) so fresh Klipper instances keep their dashboards reachable without manual edits.
- Falling back to sane defaults when expected NGINX site stanzas are absent, keeping menu flows responsive instead of crashing on missing configs.
- Detecting nftables-based firewalls and layering guided prompts that open Moonraker and Fluidd ports only for the networks you approve, keeping phones and tablets reachable without exposing them broadly by default.
- Replacing crowsnest's Debian-centric installer with an apk-aware deployment path that renders the upstream configuration and provisions an OpenRC service so Fluidd and Mainsail webcam panels stay functional on postmarketOS.
- Offering optional WireGuard provisioning so remote access can ride an encrypted tunnel without hand-authoring VPN configs on postmarketOS devices.
- Surfacing mobile-shell aware launch presets and display heuristics so touch-friendly environments (Phosh, Plasma Mobile, etc.) get a usable KlipperScreen session without manual environment plumbing.
- Sequencing installer prompts so Wayland-specific choices only surface after the user opts into the Wayland backend, keeping the X11-first flow streamlined while preserving the option to revisit presets later.
- Adapting KlipperScreen autostart to the surrounding shell—desktop environments receive `.desktop` launchers while console-only OpenRC systems get login hooks that wait for Moonraker before spawning the UI.
- Provisioning a first-party OpenRC service for KlipperScreen's standalone flow so console boots spawn the UI without relying on systemd units.
- Writing console-safe Xwrapper policies on apk-based hosts so the OpenRC KlipperScreen service can bring up Xorg without elogind.
- Hardening upstream launchers with default `KS_XCLIENT` fallbacks so ad-hoc invocations still boot the touch UI even when init systems skip the expected environment exports.
- Defaulting installers to the minimum viable dependency footprint and offering optional extras as explicit opt-ins so mobile deployments stay lightweight.

As the scope expands beyond SBCs, we treat touch-first UX goals—gesture-ready launchers, portrait rotation defaults, and low-power service policies—as first-class citizens so postmarketOS phones and tablets can host Klipper without desktop-era compromises.
