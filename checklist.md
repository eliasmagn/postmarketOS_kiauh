# Checklist

- [x] Detect and support both `apt` and `apk` package managers inside the helper utilities.
- [x] Translate Debian-specific dependency names to their Alpine/postmarketOS equivalents during installation.
- [x] Refresh documentation to describe the new package manager support.
- [x] Inventory component installer dependencies and document the Debian ➜ Alpine package mapping, including missing ports.
- [x] Introduce init-system detection and mirror service management for systemd and OpenRC, updating every component to use the shared abstraction.
- [x] Add Phosh/Plasma Wayland presets to the KlipperScreen installer and generate launchers during installation.
- [x] Auto-detect built-in displays and pre-seed `KlipperScreen.conf` with size/orientation hints on first install.
- [x] Autostart KlipperScreen automatically on Phosh/Plasma desktops and OpenRC consoles without relying on systemd units.
- [x] Gate Moonraker update-manager's `managed_services` stanza behind the selected KlipperScreen autostart backend.
- [x] Document postmarketOS-specific prerequisites for the init-service abstraction and Wayland presets in the README.
- [ ] Capture feedback from postmarketOS test runs and extend the compatibility matrix as needed.
- [ ] Automate KlipperScreen smoke tests on postmarketOS handsets/tablets to validate display presets after updates.
- [ ] Upstream missing Alpine packaging workarounds (e.g., `packagekit`, `libcamera-apps-lite`) to reduce custom steps.
- [ ] Coordinate with KlipperScreen maintainers on integrating the Wayland wrapper defaults upstream.
