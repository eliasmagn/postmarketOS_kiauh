<p align="center">
    <img src="docs/assets/logo-large.png" alt="KIAUH Logo" height="181">
    <h1 align="center">Klipper Installation And Update Helper</h1>
</p>

<p align="center">
  A handy installation script that makes installing Klipper (and more) a breeze!
</p>

<p align="center">
  <a><img src="https://img.shields.io/github/license/postmarketOS-community/postmarketos-kiauh"></a>
  <a><img src="https://img.shields.io/github/stars/postmarketOS-community/postmarketos-kiauh"></a>
  <a><img src="https://img.shields.io/github/forks/postmarketOS-community/postmarketos-kiauh"></a>
  <a><img src="https://img.shields.io/github/languages/top/postmarketOS-community/postmarketos-kiauh?logo=gnubash&logoColor=white"></a>
  <a><img src="https://img.shields.io/github/v/tag/postmarketOS-community/postmarketos-kiauh"></a>
  <br />
  <a><img src="https://img.shields.io/github/last-commit/postmarketOS-community/postmarketos-kiauh"></a>
  <a><img src="https://img.shields.io/github/contributors/postmarketOS-community/postmarketos-kiauh"></a>
</p>

<hr>

<h2 align="center">
  📄️ Instructions 📄
</h2>

### 📋 Prerequisites

KIAUH is a script that assists you in installing Klipper on a Linux operating
system that has
already been flashed to your Raspberry Pi's (or other SBC's) SD card. As a
result, you must ensure
that you have a functional Linux system on hand.
`Raspberry Pi OS Lite (either 32bit or 64bit)` is a recommended Linux image
if you are using a Raspberry Pi.
The [official Raspberry Pi Imager](https://www.raspberrypi.com/software/)
is the simplest way to flash an image like this to an SD card.

* Once you have downloaded, installed and launched the Raspberry Pi Imager,
  select `Choose OS -> Raspberry Pi OS (other)`: \

<p align="center">
  <img src="docs/assets/rpi_imager1.png" alt="KIAUH logo" height="350">
</p>

* Then select `Raspberry Pi OS Lite (32bit)` (or 64bit if you want to use that
  instead):

<p align="center">
  <img src="docs/assets/rpi_imager2.png" alt="KIAUH logo" height="350">
</p>

* Back in the Raspberry Pi Imager's main menu, select the corresponding SD card
  to which
  you want to flash the image.

* Make sure to go into the Advanced Option (the cog icon in the lower left
  corner of the main menu)
  and enable SSH and configure Wi-Fi.

* If you need more help for using the Raspberry Pi Imager, please visit
  the [official documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html).


#### postmarketOS device prerequisites

If you are deploying KIAUH on a phone or tablet that ships with postmarketOS, make sure the base image is prepped through [pmbootstrap](https://wiki.postmarketos.org/wiki/Pmbootstrap) and that you can reach the device over SSH. The following checklist helps align the mobile environment with KIAUH's init-system and Wayland tooling:

- Flash a recent `postmarketos-base` rootfs and enable SSH or USB networking (`pmbootstrap install --ssh`).
- Install one of the touch UIs (`postmarketos-ui-phosh` or `postmarketos-ui-plasma-mobile`) so the Wayland presets have an available session.
- Sxmo users should keep `sxmo-utils` installed—the helper mirrors its wlroots environment exports when generating the KlipperScreen launcher.
- Ensure the main user belongs to the `video`, `input`, and `plugdev` groups so KlipperScreen inherits display and input permissions.
- Start the seat management service after the first boot (`rc-update add seatd default && rc-service seatd start`) because the KlipperScreen Wayland wrapper relies on it.
- Keep the vendor-specific DRM or DSI panel drivers enabled; the display preset generator reads them to pre-seed orientation hints.

With these prerequisites met, the init-system helper will link services into OpenRC automatically and the launcher presets can bind to the device's Wayland shell without manual tweaks.

> 🛠️ **Kernel configuration checklist** – When you build or select a custom postmarketOS kernel, make sure the drivers required by Klipper, Moonraker, KlipperScreen, crowsnest, and WireGuard are enabled. See [docs/kernel_requirements.md](docs/kernel_requirements.md) for a per-component breakdown of the key `CONFIG_` options and module names to verify before flashing.

These steps **only** apply if you are actually using a Raspberry Pi. In case you
want
to use a different SBC (like an Orange Pi or any other Pi derivates), please
look up on how to get an appropriate Linux image flashed
to the SD card before proceeding further (usually done with Balena Etcher in
those cases). Also make sure that KIAUH will be able to run
and operate on the Linux Distribution you are going to flash. You likely will
have the most success with
distributions based on Debian 11 Bullseye. Read the notes further down below in
this document.

### 💾 Download and use KIAUH

**📢 Disclaimer: Usage of this script happens at your own risk!**

* **Step 1:** \
  To download this script, it is necessary to have git installed. If you don't
  have git already installed, or if you are unsure, run the command that matches
  your distribution:

```shell
# Debian, Ubuntu, Raspberry Pi OS, ...
sudo apt-get update && sudo apt-get install git -y

# Alpine Linux / postmarketOS
sudo apk update && sudo apk add git
```

> ℹ️ **Alpine/postmarketOS cross-toolchains** – KIAUH now resolves the cross-compilation packages by their native `apk` names:
> `binutils-arm-none-eabi`, `gcc-arm-none-eabi`, `binutils-avr`, and `gcc-avr`. This avoids the "package not found" errors
> reported during early postmarketOS installs that still referenced the Debian naming scheme.

* **Step 2:** \
  Once git is installed, use the following command to download KIAUH into your
  home-directory:

```shell
cd ~ && git clone https://github.com/postmarketOS-community/postmarketos-kiauh.git
```

> ℹ️ **Self-update origin rewriting** – `kiauh.sh` now ensures that the script's
> `origin` remote points to the postmarketOS community fork before running a
> self-update. If you maintain a personal fork, set
> `KIAUH_REPO_URL=<your-remote-url>` in the environment before launching KIAUH
> so the helper keeps your remote intact.

* **Step 3:** \
  Finally, start KIAUH by running the next command:

```shell
./kiauh/kiauh.sh
```

* **Step 4:** \
  You should now find yourself in the main menu of KIAUH. You will see several
  actions to choose from depending
  on what you want to do. To choose an action, simply type the corresponding
  number into the "Perform action"
  prompt and confirm by hitting ENTER.

> ✅ **Case-insensitive prompts** – Every yes/no dialog now accepts upper- or
> lower-case responses alongside numeric toggles like `1`/`0` and `on`/`off`, so
> you can answer from touch keyboards and remote shells without triggering the
> invalid choice handler.

### 🔄 Update menu UX

- Loading spinners now pause automatically whenever `sudo` needs your password or the package manager prints interactive output, so update checks no longer obscure the prompt behind the animation.
- Menu loading indicators now shut down safely even if they were never started, eliminating the `AttributeError` that previously appeared when a menu tried to stop a missing spinner.
- Warning prompts across installers and extensions now route through the shared `Logger.print_warn` helper so the CLI surfaces consistent messaging.

### ♻️ Init system compatibility

KIAUH now ships with a unified init abstraction so phones, tablets, and SBCs share the same workflows regardless of which service manager they boot. During startup the helper automatically detects whether the host is running **systemd** or
**OpenRC**. All service files are created in the appropriate
location (`/etc/systemd/system` for systemd, `/etc/init.d` for OpenRC) and every
component now executes start/stop/enable operations through a shared helper.
On OpenRC-based systems the helper transparently switches to `rc-service` and
`rc-update`, so manual maintenance commands follow the native tools instead of
`systemctl`.

- When NetworkManager is installed during the KlipperScreen flow on systemd, the helper now prints a reboot reminder instead of forcing an immediate restart so unattended runs can finish cleanly before you reboot manually.
- On OpenRC devices the standalone KlipperScreen path now installs a native `/etc/init.d/KlipperScreen` script, links it into the default runlevel, and exports the same environment variables as the upstream systemd unit so boot-to-console deployments land in the touch UI automatically.
- apk-based OpenRC deployments now receive an `/etc/X11/Xwrapper.config` with console-friendly permissions so `KlipperScreen-start.sh` can launch Xorg from services without requiring logind.
- The installer now patches `KlipperScreen-start.sh` with a fallback client so manual launches still invoke `screen.py` even if init systems or shells omit the `KS_XCLIENT` environment export.

### 🌐 NGINX layout detection

- Fluidd and other web front-ends now detect whether the host uses `/etc/nginx/conf.d/` or Alpine's `/etc/nginx/http.d/` include directory before copying support files. This prevents the Fluidd installer from failing on postmarketOS devices where `conf.d` is absent and keeps the generated configuration inside the directory that NGINX already loads.
- When neither include directory exists—common on freshly provisioned postmarketOS images—the installer now creates `/etc/nginx/conf.d` before writing `upstreams.conf` and `common_vars.conf`, so Fluidd deployments no longer abort with a missing-path error.
- When `/etc/nginx/sites-available` or `/etc/nginx/sites-enabled` is missing—as on stock Alpine images—the installer provisions both directories with `sudo install -d` and drops a `kiauh-sites.conf` include into the detected NGINX include directory so multiple dashboards (Mainsail, Fluidd, PrettyGCode, etc.) can coexist without rewriting `nginx.conf`.
- The helper logs the resolved directory so you can confirm which include path was used if you need to hand-inspect the configuration later.
- When an expected site definition is missing entirely, the menu falls back to the saved default port instead of crashing so you can still reinstall or reconfigure the client.
- Fluidd's NGINX site definition now streams straight into place with `sudo tee`, sidestepping the tmpfile rename that `doas`-backed hosts occasionally lost before it reached `/etc/nginx`.

### 🧩 Web UI config hand-off

- When KIAUH seeds a fresh `printer.cfg` for new Klipper instances it now re-checks for installed Mainsail/Fluidd directories and automatically adds the matching `include` statements. The generated example therefore keeps your dashboards reachable immediately after installation, even on systems that install the web UIs before Klipper.

### 📹 Crowsnest webcam integration

- The crowsnest installer now falls back to an apk-aware workflow when `apt` is unavailable, translating the upstream dependency list through KIAUH's package mapper so ustreamer builds cleanly on postmarketOS and other Alpine derivatives.
- During the apk install path the helper renders the upstream `crowsnest.conf`, environment file, and logrotate rule directly from the cloned repository, then provisions a native OpenRC service that mirrors the original systemd unit so `/webcam`, `/webcam2`, etc. work immediately inside Fluidd and Mainsail.
- Installations on OpenRC hosts add the invoking user to the `video` group automatically and restart the new service, which keeps the camera stream reachable through the existing NGINX reverse proxy without manual tweaks.

### 🔒 nftables firewall integration

- When the helper detects the `nft` binary it now inspects the default `inet filter input` chain and offers to add allow rules for Moonraker and NGINX-hosted web UIs (Fluidd, Mainsail, etc.). Fresh installs only prompt when the target port is missing so existing firewall policies remain untouched.
- The dialog lets you keep the listener open to the world, restrict it to the automatically detected local subnets, or enter a custom comma-separated list of CIDR ranges/hosts. IPv4 and IPv6 prefixes are supported.
- Reconfiguring a web UI port through the installation menu re-runs the firewall helper so the nftables rule stays in sync without manual edits. You can always skip the automation and adjust rules manually if you prefer.
- When the default `inet filter input` chain is missing, the helper now surfaces a follow-up warning that links to the [postmarketOS firewall guide](https://wiki.postmarketos.org/wiki/Firewall) so you know where to add rules manually before continuing.

### 🔐 WireGuard provisioning

- The Installation menu now exposes a `WireGuard` entry that installs `wireguard-tools`, walks you through generating or importing keys, and writes `/etc/wireguard/<interface>.conf` with the peer settings you provide.
- Existing configurations are backed up with a timestamped `.bak` before the new file is written, permissions are tightened to `600`, and KIAUH enables the matching `wg-quick` service for systemd and OpenRC hosts when possible.
- The helper prints the freshly generated public key so you can register the device on your VPN gateway, making it easier to pair WireGuard with the nftables automation when remote access is required.

### 📱 Wayland mobile-shell presets

During KlipperScreen installation you can now pick a Wayland launcher preset
that mirrors the upstream Phosh, Plasma Mobile, and Sxmo recommendations while also
deferring the choice until after you explicitly select the Wayland backend in
the upstream installer. X11-first setups therefore skip the extra question but
can rerun the preset helper later if they move to Wayland. When Wayland is
selected, the prompt surfaces device-aware display defaults gathered from postmarketOS hardware
probing. KIAUH writes the following artefacts after cloning the KlipperScreen
repository:

- A shell wrapper in `~/.local/bin/` that exports the compositor-friendly
  environment variables (Qt, GTK, SDL, etc.) before delegating to
  `KlipperScreen-start.sh`.
- A `.desktop` entry in `~/.local/share/applications/` so Phosh/Plasma launchers
  can spawn KlipperScreen with the expected Wayland flags.
- When a Phosh or Plasma Mobile session is detected at install time, a matching
  autostart entry is written to `~/.config/autostart/` so the wrapper launches
  automatically on login.
- On OpenRC consoles without a graphical shell, a login snippet in
  `~/.config/profile.d/` waits for Moonraker to respond before spawning
  KlipperScreen.
- Either a `systemd --user` service or an OpenRC user service stub, depending on
  the host init system, pointing to the wrapper.
- Sxmo environments receive the same wlroots variables the upstream `sxmo-utils`
  package exports, ensuring Qualcomm msm8953 reference images can launch
  KlipperScreen without additional wrappers.

Systemd users can enable the service immediately:

```sh
systemctl --user enable --now klipperscreen-phosh.service
```

OpenRC users need to symlink the generated service script into their preferred
runlevel (for example `~/.config/openrc/runlevels/default/`).

The launcher presets are additive—the existing system instance managed by KIAUH
remains untouched—so you can try the Wayland session without disrupting the
original install.

### 🧹 Minimal KlipperScreen footprint

- The KlipperScreen installer now defaults to the packages strictly required to
  run the UI with touch input. Optional fonts and media backends are skipped
  unless you explicitly opt in when KIAUH asks before launching the upstream
  installer.
- Headless or scripted runs can preseed the decision by exporting
  `KIAUH_KS_INSTALL_EXTRAS=1` (install extras) or `KIAUH_KS_INSTALL_EXTRAS=0`
  (keep the minimal set) before invoking `KlipperScreen-install.sh`.
- When the extras are skipped, the downstream log highlights that the install
  kept the dependency footprint minimal, so you can verify that the additional
  packages were not pulled in.

### 🪟 X11 remains a first-class option on postmarketOS

- When the helper detects an Alpine/postmarketOS environment it now swaps the upstream KlipperScreen installer with an apk-aware wrapper before execution. The wrapper mirrors the original prompts but resolves dependency installation through `apk` (or `doas` when `sudo` is absent) so X11 packages install cleanly.
- The translated dependency set covers the classic Xorg stack (`xorg-server`, `xf86-input-libinput`, `xf86-video-fbdev`, `xset`, etc.) as well as the Wayland kiosk trio. Users can therefore continue accepting the default X11 backend even on phones where Wayland is not yet stable.
- Systems booted with OpenRC automatically skip systemd unit creation while still provisioning the graphical backend packages, letting the downstream OpenRC autostart integration take over.

When KlipperScreen runs as a user-managed service (systemd `--user`, OpenRC
user units, or the login hook above) Moonraker's update-manager entry skips the
`managed_services` stanza so non-systemd autostart strategies remain unaffected
by future updates.

### 🖥️ Auto-generated KlipperScreen.conf defaults

If `wlr-randr` or `weston-info` is present, KIAUH now detects the built-in
display during installation. The detected width, height, and rotation hint are
written to `~/printer_data/config/KlipperScreen.conf` (or appended if the file
already exists). Adjust the values if your compositor applies additional
scaling, or if you rotate the panel within Phosh/Plasma settings.

Touch rotation is still handled by the compositor—follow the upstream
troubleshooting guide if pointer coordinates do not align after rotating.

### 🏞️ Panorama orientation helper

- During installation KIAUH now asks whether KlipperScreen should run in a
  panorama (horizontal) layout. Opting in rewrites the width/height defaults in
  `KlipperScreen.conf`, ensuring wide touch panels advertise the correct
  horizontal resolution to the UI.
- The same prompt seeds an executable helper under
  `~/.config/klipperscreen/panorama-xrandr.sh`. When the X11 backend is active
  the patched launcher executes this helper before starting KlipperScreen so the
  selected output is configured with the requested mode and rotation.
- You can rerun the KlipperScreen installer at any time to tweak the panorama
  resolution or disable the helper by removing the script.

<h2 align="center">📦 Debian ➜ Alpine package map</h2>

To keep the postmarketOS port predictable, every Debian package requested by the
component installers under `kiauh/components/**` is mapped to the appropriate
Alpine `apk` name (where possible). The tables below list the exact inventory.
Entries marked as "Not available" are skipped at runtime and emit a warning so
that you can plan any manual workarounds.

#### Global prerequisites

| Debian package        | Alpine package(s) |
|-----------------------|-------------------|
| git                   | git               |
| wget                  | wget              |
| curl                  | curl              |
| unzip                 | unzip             |
| dfu-util              | dfu-util          |
| python3-virtualenv    | py3-virtualenv    |

#### Klipper host installer (`scripts/install-ubuntu-22.04.sh`)

| Debian package             | Alpine package(s)         |
|----------------------------|---------------------------|
| virtualenv                 | py3-virtualenv            |
| python3-dev                | python3-dev               |
| libffi-dev                 | libffi-dev                |
| build-essential            | build-base                |
| libncurses-dev             | ncurses-dev               |
| libusb-dev                 | libusb-dev                |
| avrdude                    | avrdude                   |
| gcc-avr                    | avr-gcc                   |
| binutils-avr               | avr-binutils              |
| avr-libc                   | avr-libc                  |
| stm32flash                 | stm32flash                |
| libnewlib-arm-none-eabi    | newlib-arm-none-eabi      |
| gcc-arm-none-eabi          | arm-none-eabi-gcc         |
| binutils-arm-none-eabi     | arm-none-eabi-binutils    |
| libusb-1.0                 | libusb                    |

#### Klipper input shaper extras

| Debian package        | Alpine package(s) |
|-----------------------|-------------------|
| python3-numpy         | py3-numpy         |
| python3-matplotlib    | py3-matplotlib    |
| libatlas-base-dev     | atlas-dev         |
| libopenblas-dev       | openblas-dev      |

#### Moonraker system dependencies (`scripts/system-dependencies.json`)

| Debian package        | Alpine package(s)        |
|-----------------------|--------------------------|
| python3-virtualenv    | py3-virtualenv           |
| python3-dev           | python3-dev              |
| libopenjp2-7          | openjpeg                 |
| libsodium-dev         | libsodium-dev            |
| zlib1g-dev            | zlib-dev                 |
| libjpeg-dev           | libjpeg-turbo-dev        |
| packagekit            | Not available on Alpine* |
| wireless-tools        | wireless-tools           |
| iw                    | iw                       |
| python3-libcamera     | py3-libcamera            |
| curl                  | curl                     |
| build-essential       | build-base               |

> ℹ️ **Debian fallback on apk systems** – Moonraker's dependency manifest currently ships a single Debian block. When KIAUH detects an Alpine/postmarketOS environment it now reuses that list, feeds the entries through the translation table above, and surfaces warnings for packages without a native apk port (e.g., `packagekit`).

> ✅ **BusyBox-friendly policykit install** – postmarketOS ships BusyBox utilities whose `grep` lacks the `-P` flag used by Moonraker's policykit script. When that happens KIAUH now installs GNU `grep` automatically on apk-based systems and retries the helper so the policykit rules land correctly.

> 🧩 **PackageKit-free system updates** – Alpine/postmarketOS mirrors do not ship PackageKit, so KIAUH now installs an apt-compatible drop-in backed by `apk`, leaves Moonraker's policykit helper in place, and keeps the Update Manager's system provider working without warning banners.

#### Crowsnest core installer (`tools/libs/pkglist-generic.sh`)

| Debian package     | Alpine package(s)           |
|--------------------|-----------------------------|
| git                | git                         |
| crudini            | crudini                     |
| bsdutils           | util-linux                  |
| findutils          | findutils                   |
| v4l-utils          | v4l-utils                   |
| curl               | curl                        |
| build-essential    | build-base                  |
| make               | make                        |
| libevent-dev       | libevent, libevent-dev      |
| libjpeg-dev        | libjpeg-turbo-dev           |
| libbsd-dev         | libbsd-dev                  |
| pkg-config         | pkgconf                     |

#### Crowsnest camera-streamer extras (`tools/libs/pkglist-rpi.sh`)

| Debian package        | Alpine package(s)           |
|-----------------------|-----------------------------|
| cmake                 | cmake                       |
| libavformat-dev       | ffmpeg-dev                  |
| libavutil-dev         | ffmpeg-dev                  |
| libavcodec-dev        | ffmpeg-dev                  |
| libcamera-dev         | libcamera, libcamera-dev    |
| libcamera-apps-lite   | Not available on Alpine*    |
| liblivemedia-dev      | live555, live555-dev        |
| pkg-config            | pkgconf                     |
| xxd                   | xxd                         |
| build-essential       | build-base                  |
| libssl-dev            | openssl-dev                 |

#### Firmware build helpers

| Debian package  | Alpine package(s) |
|-----------------|-------------------|
| build-essential | build-base        |
| dpkg-dev        | dpkg              |
| make            | make              |

#### Web UI clients

| Debian package | Alpine package(s) |
|----------------|-------------------|
| nginx          | nginx             |

*`packagekit` powers Moonraker's PackageKit integration on Debian systems but is
not shipped for Alpine/postmarketOS. `libcamera-apps-lite` provides optional
camera utilities that are also unavailable on Alpine. The helper warns when
these packages are skipped so you can review downstream tooling requirements.

<hr>

<h2 align="center">❗ Notes ❗</h2>

### **📋 Please see the [Changelog](docs/changelog.md) for possible important

changes!**

- Mainly tested on Raspberry Pi OS Lite (Debian 10 Buster / Debian 11 Bullseye)
    - Other Debian based distributions (like Ubuntu 20 to 22) likely work too
    - Reported to work on Armbian as well but not tested in detail
- Automatic package manager detection now supports both `apt` and `apk`
    - This allows running KIAUH on Alpine Linux derivatives such as postmarketOS
    - The helper now inspects `/etc/os-release` so Alpine/postmarketOS hosts always prefer `apk`, even when compatibility wrappers expose `apt-get`
- During the use of this script you will be asked for your sudo password. There
  are several functions involved which need sudo privileges.

<hr>

<h2 align="center">🌐 Sources & Further Information</h2>

<table align="center">
<tr>
    <th><h3><a href="https://github.com/Klipper3d/klipper">Klipper</a></h3></th>
    <th><h3><a href="https://github.com/Arksine/moonraker">Moonraker</a></h3></th>
    <th><h3><a href="https://github.com/mainsail-crew/mainsail">Mainsail</a></h3></th>
</tr>
<tr>
    <th><img src="https://raw.githubusercontent.com/Klipper3d/klipper/master/docs/img/klipper-logo.png" alt="Klipper Logo" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/9563098?v=4" alt="Arksine avatar" height="64"></th>
    <th><img src="https://raw.githubusercontent.com/mainsail-crew/docs/master/assets/img/logo.png" alt="Mainsail Logo" height="64"></th>
</tr>
<tr>
    <th>by <a href="https://github.com/KevinOConnor">KevinOConnor</a></th>
    <th>by <a href="https://github.com/Arksine">Arksine</a></th>
    <th>by <a href="https://github.com/mainsail-crew">mainsail-crew</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/fluidd-core/fluidd">Fluidd</a></h3></th>
    <th><h3><a href="https://github.com/jordanruthe/KlipperScreen">KlipperScreen</a></h3></th>
    <th><h3><a href="https://github.com/OctoPrint/OctoPrint">OctoPrint</a></h3></th>
</tr>
<tr>
    <th><img src="https://raw.githubusercontent.com/fluidd-core/fluidd/master/docs/assets/images/logo.svg" alt="Fluidd Logo" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/31575189?v=4" alt="jordanruthe avatar" height="64"></th>
    <th><img src="https://raw.githubusercontent.com/OctoPrint/OctoPrint/master/docs/images/octoprint-logo.png" alt="OctoPrint Logo" height="64"></th>
</tr>
<tr>
    <th>by <a href="https://github.com/fluidd-core">fluidd-core</a></th>
    <th>by <a href="https://github.com/jordanruthe">jordanruthe</a></th>
    <th>by <a href="https://github.com/OctoPrint">OctoPrint</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/nlef/moonraker-telegram-bot">Moonraker-Telegram-Bot</a></h3></th>
    <th><h3><a href="https://github.com/Kragrathea/pgcode">PrettyGCode for Klipper</a></h3></th>
    <th><h3><a href="https://github.com/TheSpaghettiDetective/moonraker-obico">Obico for Klipper</a></h3></th>
</tr>
<tr>
    <th><img src="https://avatars.githubusercontent.com/u/52351624?v=4" alt="nlef avatar" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/5917231?v=4" alt="Kragrathea avatar" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/46323662?s=200&v=4" alt="Obico logo" height="64"></th>
</tr>
<tr>
    <th>by <a href="https://github.com/nlef">nlef</a></th>
    <th>by <a href="https://github.com/Kragrathea">Kragrathea</a></th>
    <th>by <a href="https://github.com/TheSpaghettiDetective">Obico</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/Clon1998/mobileraker_companion">Mobileraker's Companion</a></h3></th>
    <th><h3><a href="https://octoeverywhere.com/?source=kiauh_readme">OctoEverywhere For Klipper</a></h3></th>
    <th><h3><a href="https://github.com/crysxd/OctoApp-Plugin">OctoApp For Klipper</a></h3></th>
</tr>
<tr>
    <th><a href="https://github.com/Clon1998/mobileraker_companion"><img src="https://raw.githubusercontent.com/Clon1998/mobileraker/master/assets/icon/mr_appicon.png" alt="Mobileraker Logo" height="64"></a></th>
    <th><a href="https://octoeverywhere.com/?source=kiauh_readme"><img src="https://octoeverywhere.com/img/logo.svg" alt="OctoEverywhere Logo" height="64"></a></th>
    <th><a href="https://octoapp.eu/?source=kiauh_readme"><img src="https://octoapp.eu/octoapp.webp" alt="OctoApp Logo" height="64"></a></th>
</tr>
<tr>
    <th>by <a href="https://github.com/Clon1998">Patrick Schmidt</a></th>
    <th>by <a href="https://github.com/QuinnDamerell">Quinn Damerell</a></th>
    <th>by <a href="https://github.com/crysxd">Christian Würthner</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/staubgeborener/klipper-backup">Klipper-Backup</a></h3></th>
    <th><h3><a href="https://simplyprint.io/">SimplyPrint for Klipper</a></h3></th>
</tr>
<tr>
    <th><a href="https://github.com/staubgeborener/klipper-backup"><img src="https://avatars.githubusercontent.com/u/28908603?v=4" alt="Staubgeroner Avatar" height="64"></a></th>
    <th><a href="https://github.com/SimplyPrint"><img src="https://avatars.githubusercontent.com/u/64896552?s=200&v=4" alt="" height="64"></a></th>
</tr>
<tr>
    <th>by <a href="https://github.com/Staubgeborener">Staubgeborener</a></th>
    <th>by <a href="https://github.com/SimplyPrint">SimplyPrint</a></th>
</tr>
</table>

<hr>

<h2 align="center">🎖️ Contributors 🎖️</h2>

<div align="center">
  <a href="https://github.com/postmarketOS-community/postmarketos-kiauh/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=postmarketOS-community/postmarketos-kiauh" alt=""/>
  </a>
</div>

<hr>

<div align="center">
    <img src="https://repobeats.axiom.co/api/embed/a1afbda9190c04a90cf4bd3061e5573bc836cb05.svg" alt="Repobeats analytics image"/>
</div>

<hr>

<h2 align="center">✨ Credits ✨</h2>

* A big thank you to [lixxbox](https://github.com/lixxbox) for that awesome
  KIAUH-Logo!
* Also, a big thank you to everyone who supported my work with
  a [Ko-fi](https://ko-fi.com/dw__0) !
* Last but not least: Thank you to all contributors and members of the Klipper
  Community who like and share this project!

<hr>

<h4 align="center">A special thank you to JetBrains for sponsoring this project
with their incredible software!</h4>
<p align="center">
  <a href="https://www.jetbrains.com/community/opensource/#support" target="_blank">
    <img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.png" alt="JetBrains Logo (Main) logo." height="128">
  </a>
</p>
