# Kernel configuration reference for postmarketOS KIAUH deployments

This guide highlights the Linux kernel options that keep KIAUH-managed components fully functional on Alpine and postmarketOS devices. Use it when building a custom kernel or verifying that a downstream vendor tree exposes the right drivers. Each section lists the relevant `CONFIG_` symbols (with their module names when they normally ship as loadable drivers) and explains why the feature matters.

## Core system prerequisites

| Capability | Key symbols / modules | Notes |
| --- | --- | --- |
| Modern init & packaging helpers | `CONFIG_FHANDLE`, `CONFIG_DNOTIFY`, `CONFIG_INOTIFY_USER` | Required for OpenRC/systemd service helpers and Moonraker's file watchers.
| Virtual memory pressure and OOM handling | `CONFIG_MEMCG`, `CONFIG_CGROUPS`, `CONFIG_CGROUP_FREEZER`, `CONFIG_CGROUP_DEVICE` | Keeps Moonraker and Klipper processes manageable on memory-constrained devices; aligns with upstream Debian defaults.
| Filesystems | `CONFIG_EXT4_FS`, `CONFIG_AUTOFS4_FS`, `CONFIG_TMPFS_POSIX_ACL`, `CONFIG_OVERLAY_FS` | Ext4/overlayfs support matches postmarketOS rootfs expectations and ensures backup/snapshot helpers work.
| Networking basics | `CONFIG_IPV6`, `CONFIG_NETFILTER`, `CONFIG_NETFILTER_XT_MATCH_CONNTRACK`, `CONFIG_NETFILTER_XT_TARGET_MASQUERADE` | Moonraker, web UIs, and WireGuard rely on IPv4/IPv6 networking with nftables firewalls.
| USB host stack | `CONFIG_USB`, `CONFIG_USB_XHCI_HCD`, `CONFIG_USB_DWC2` (mobile SoCs), `CONFIG_USB_EHCI_HCD`, `CONFIG_USB_OHCI_HCD` | Required for USB-connected printer boards, webcams, and touch displays.

## Klipper host

| Feature | Key symbols / modules | Notes |
| --- | --- | --- |
| USB serial printers | `CONFIG_USB_ACM`, `CONFIG_USB_SERIAL`, `CONFIG_USB_SERIAL_CH341`, `CONFIG_USB_SERIAL_CP210X`, `CONFIG_USB_SERIAL_FTDI_SIO` | Covers common MCU bootloaders (STM32 CDC, AVR, RP2040) and 3D-printer-specific adapters.
| GPIO bridge boards | `CONFIG_GPIO_SYSFS`, `CONFIG_GPIO_CDEV`, `CONFIG_SPI`, `CONFIG_I2C`, `CONFIG_I2C_CHARDEV`, `CONFIG_PWM` | Keeps expansion hats, accelerometer probes, and filament sensors reachable from Klipper.
| CAN bus toolboards | `CONFIG_CAN`, `CONFIG_CAN_RAW`, `CONFIG_CAN_DEV`, `CONFIG_CAN_MCP251X`, `CONFIG_CAN_MCP251XFD` | Enables SocketCAN, letting Klipper talk to CAN-enabled toolboards such as BTT EBB and Fysetc spider modules.
| Real-time responsiveness | `CONFIG_PREEMPT`, `CONFIG_PREEMPT_DYNAMIC` | Improves scheduling latency for time-sensitive MCU flashing and USB streaming.
| MCU flashing utilities | `CONFIG_USB_DFU`, `CONFIG_USB_G_SERIAL`, `CONFIG_TTY`, `CONFIG_SERIAL_8250` | Keeps DFU, CDC, and UART flash workflows available.

## Moonraker API server

| Feature | Key symbols / modules | Notes |
| --- | --- | --- |
| WebSockets & HTTP | `CONFIG_INET_DIAG`, `CONFIG_TCP_CONG_BBR` (optional), `CONFIG_TLS` | Standard TCP/IP stack; TLS hooks allow nginx-terminated HTTPS reverse proxies.
| inotify file monitoring | `CONFIG_INOTIFY_USER` | Moonraker watches configuration and log files for changes.
| nftables integration | `CONFIG_NF_TABLES`, `CONFIG_NF_TABLES_IPV4`, `CONFIG_NF_TABLES_IPV6`, `CONFIG_NETFILTER_XT_SET` | Lets the nftables helper manage firewall rules programmatically.

## Web UIs (Mainsail, Fluidd, others)

| Feature | Key symbols / modules | Notes |
| --- | --- | --- |
| Reverse proxy | `CONFIG_NETFILTER_XT_MATCH_STATE`, `CONFIG_NETFILTER_XT_MATCH_SOCKET` | Ensures nftables-based reverse proxy rules work when nginx listens on alternate ports.
| HTTP/2 and TLS acceleration | `CONFIG_TLS`, `CONFIG_CRYPTO_USER_API_HASH`, `CONFIG_CRYPTO_USER_API_SKCIPHER` | Required when nginx is compiled with `openssl`/`libressl` back-ends.

## KlipperScreen

| Feature | Key symbols / modules | Notes |
| --- | --- | --- |
| DRM / KMS graphics | `CONFIG_DRM`, relevant SoC DRM drivers (e.g., `CONFIG_DRM_MSM`, `CONFIG_DRM_PANFROST`, `CONFIG_DRM_SIMPLEDRM`), `CONFIG_DRM_PANEL_BRIDGE` | Wayland and X11 sessions depend on modern KMS APIs for accelerated rendering and rotation helpers.
| Framebuffer fallback | `CONFIG_FB`, `CONFIG_FB_SIMPLE`, `CONFIG_FB_EFI` | Keeps X11 fallback sessions functional on devices without mature DRM drivers.
| Input/touch | `CONFIG_INPUT_EVDEV`, `CONFIG_INPUT_TOUCHSCREEN`, specific drivers (`CONFIG_TOUCHSCREEN_GOODIX`, `CONFIG_TOUCHSCREEN_FT6236`, etc.) | Touch, stylus, and physical button input for KlipperScreen UI.
| Seat management | `CONFIG_TTY`, `CONFIG_VT`, `CONFIG_UINPUT` | Supports seatd/elogind input handling and virtual keyboard injection.
| GPU acceleration (optional) | `CONFIG_DRM_PANFROST`, `CONFIG_DRM_V3D`, `CONFIG_DRM_ETNAVIV` | Enables smoother Wayland compositing on ARM SoCs.

## Crowsnest (camera streaming)

| Feature | Key symbols / modules | Notes |
| --- | --- | --- |
| Video4Linux capture | `CONFIG_VIDEO_DEV`, `CONFIG_VIDEO_V4L2_SUBDEV_API` | Base V4L2 framework required by both UVC webcams and CSI cameras.
| UVC webcams | `CONFIG_USB_VIDEO_CLASS` (`uvcvideo` module) | Supports the majority of USB webcams used with Mainsail/Fluidd.
| Raspberry Pi CSI stack | `CONFIG_VIDEO_BCM2835`, `CONFIG_VIDEO_BCM2835_UNICAM`, `CONFIG_VIDEO_IMX219`, `CONFIG_VIDEO_OV5647` | Keeps Pi CSI cameras streaming through crowsnest on postmarketOS.
| H.264 hardware encode | `CONFIG_VIDEO_H264`, SoC-specific media drivers (`CONFIG_VIDEO_HI6220_VDEC`, `CONFIG_VIDEO_MEDIATEK_VCODEC`) | Optional but lowers CPU usage for high-resolution streams.

## WireGuard provisioning

| Feature | Key symbols / modules | Notes |
| --- | --- | --- |
| VPN tunnel | `CONFIG_WIREGUARD`, `CONFIG_NET_UDP_TUNNEL`, `CONFIG_CRYPTO_CHACHA20_POLY1305`, `CONFIG_CRYPTO_BLAKE2S` | WireGuard support in the kernel with required crypto primitives.
| Firewall helpers | `CONFIG_NF_TABLES`, `CONFIG_NETFILTER_XT_MATCH_ADDRTYPE` | Allows nftables automation to gate VPN ports alongside Moonraker/web UI rules.

## Optional extras and debugging helpers

| Capability | Key symbols / modules | Notes |
| --- | --- | --- |
| Accelerometer probes | I2C/SPI sensor drivers (`CONFIG_ADXL345_I2C`, `CONFIG_ADXL345_SPI`, `CONFIG_IIO`) | Required for Klipper input-shaper calibration using ADXL345/ADXL355 sensors.
| USB gadget mode (phone tethering) | `CONFIG_USB_GADGET`, `CONFIG_USB_CONFIGFS`, `CONFIG_USB_CONFIGFS_RNDIS` | Enables USB networking so phones/tablets can present Ethernet gadgets while hosting Klipper.
| Storage hotplug | `CONFIG_USB_STORAGE`, `CONFIG_SCSI`, `CONFIG_MSDOS_FS`, `CONFIG_VFAT_FS` | Lets you mount removable storage during firmware flashing or log collection.
| Debugging & diagnostics | `CONFIG_FTRACE`, `CONFIG_KPROBES`, `CONFIG_DEBUG_FS` | Useful when profiling timing jitter or diagnosing driver availability.

When building or selecting a kernel for postmarketOS KIAUH deployments, enable the features above either built-in (`=y`) or as loadable modules (`=m`). Mobile-first vendor kernels often ship many of these options already; this checklist helps verify that no critical driver is missing before you rely on Klipper, Moonraker, or crowsnest on the device.
