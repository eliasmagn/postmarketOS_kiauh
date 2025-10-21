# Project Concept

KIAUH (Klipper Installation And Update Helper) streamlines the setup and maintenance of Klipper-based 3D printing stacks. This fork extends the original concept by ensuring that the helper also works on Alpine Linux derivatives such as postmarketOS. Detecting the available system package manager and translating dependency names keeps the installation flow consistent across distributions while preserving the familiar menu-driven user experience.

The project focuses on:

- Automating environment preparation for Klipper, Moonraker, and companion tools.
- Providing a resilient installation experience across multiple Linux families.
- Maintaining documentation that highlights platform-specific nuances for end users.
- Tracking Debian package requirements in each installer and pairing them with Alpine `apk` equivalents so postmarketOS users can reproduce the same setup flow.
- Detecting the active init system and routing all service lifecycle operations through a shared abstraction so that both systemd and OpenRC hosts behave identically.
- Surfacing mobile-shell aware launch presets and display heuristics so touch-friendly environments (Phosh, Plasma Mobile, etc.) get a usable KlipperScreen session without manual environment plumbing.
- Adapting KlipperScreen autostart to the surrounding shell—desktop environments receive `.desktop` launchers while console-only OpenRC systems get login hooks that wait for Moonraker before spawning the UI.
