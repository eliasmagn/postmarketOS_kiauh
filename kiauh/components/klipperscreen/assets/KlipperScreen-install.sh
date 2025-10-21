#!/bin/bash

SCRIPTPATH=$(dirname -- "$(readlink -f -- "$0")")
KSPATH=$(dirname "$SCRIPTPATH")
KSENV="${KLIPPERSCREEN_VENV:-${HOME}/.KlipperScreen-env}"

XSERVER="xinit xinput x11-xserver-utils xserver-xorg-input-evdev xserver-xorg-input-libinput xserver-xorg-legacy xserver-xorg-video-fbdev"
CAGE="cage seatd xwayland"
PYGOBJECT="libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0"
MISC="librsvg2-common libopenjp2-7 libdbus-glib-1-dev autoconf python3-venv"
OPTIONAL_EXTRAS="fonts-nanum fonts-ipafont libmpv-dev"

Red='\033[0;31m'
Green='\033[0;32m'
Cyan='\033[0;36m'
Normal='\033[0m'

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo_text ()
{
    printf "${Normal}%s${Cyan}\n" "$1"
}

echo_error ()
{
    printf "${Red}%s${Normal}\n" "$1"
}

echo_ok ()
{
    printf "${Green}%s${Normal}\n" "$1"
}

PRIV_CMD="sudo"
if ! command_exists sudo && command_exists doas; then
    PRIV_CMD="doas"
fi

PKG_MANAGER="apt"
if command_exists apt-get && command_exists dpkg-query; then
    PKG_MANAGER="apt"
elif command_exists apk; then
    PKG_MANAGER="apk"
else
    PKG_MANAGER="unknown"
fi

INIT_SYSTEM="unknown"
if command_exists systemctl && [ -d /run/systemd/system ]; then
    INIT_SYSTEM="systemd"
elif command_exists rc-service; then
    INIT_SYSTEM="openrc"
fi

if [ "$PKG_MANAGER" = "apk" ]; then
    XSERVER="xorg-server xf86-input-evdev xf86-input-libinput xf86-video-fbdev xinit xinput xset"
    CAGE="cage seatd xwayland"
    PYGOBJECT="gobject-introspection-dev gcc cairo-dev pkgconf python3-dev gtk+3.0-dev"
    MISC="librsvg openjpeg dbus-glib-dev autoconf py3-virtualenv"
    OPTIONAL_EXTRAS="mpv-dev"
fi

translate_apk_package() {
    case "$1" in
        x11-xserver-utils)
            echo "xset"
            ;;
        xserver-xorg-legacy)
            echo "xorg-server"
            ;;
        xserver-xorg-input-evdev)
            echo "xf86-input-evdev"
            ;;
        xserver-xorg-input-libinput)
            echo "xf86-input-libinput"
            ;;
        xserver-xorg-video-fbdev)
            echo "xf86-video-fbdev"
            ;;
        libgirepository1.0-dev)
            echo "gobject-introspection-dev"
            ;;
        libcairo2-dev)
            echo "cairo-dev"
            ;;
        pkg-config)
            echo "pkgconf"
            ;;
        gir1.2-gtk-3.0)
            echo "gtk+3.0-dev"
            ;;
        librsvg2-common)
            echo "librsvg"
            ;;
        libopenjp2-7)
            echo "openjpeg"
            ;;
        libdbus-glib-1-dev)
            echo "dbus-glib-dev"
            ;;
        python3-venv)
            echo "py3-virtualenv"
            ;;
        fonts-nanum|fonts-ipafont)
            echo ""
            ;;
        libmpv-dev)
            echo "mpv-dev"
            ;;
        build-essential)
            echo "build-base"
            ;;
        libsystemd-dev)
            echo "elogind-dev"
            ;;
        network-manager)
            echo "networkmanager"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

pkg_update() {
    if [ "$PKG_MANAGER" = "apt" ]; then
        $PRIV_CMD apt update
    elif [ "$PKG_MANAGER" = "apk" ]; then
        $PRIV_CMD apk update
    else
        echo_error "Unsupported package manager for updates"
        return 1
    fi
}

pkg_install() {
    if [ "$#" -eq 0 ]; then
        return 0
    fi
    if [ "$PKG_MANAGER" = "apt" ]; then
        $PRIV_CMD apt install -y "$@"
    elif [ "$PKG_MANAGER" = "apk" ]; then
        local translated=()
        local pkg
        for pkg in "$@"; do
            local mapped
            mapped=$(translate_apk_package "$pkg")
            if [ -z "$mapped" ]; then
                continue
            fi
            for part in $mapped; do
                local already=0
                local existing
                for existing in "${translated[@]}"; do
                    if [ "$existing" = "$part" ]; then
                        already=1
                        break
                    fi
                done
                if [ $already -eq 0 ]; then
                    translated+=("$part")
                fi
            done
        done
        if [ ${#translated[@]} -eq 0 ]; then
            return 0
        fi
        $PRIV_CMD apk add --no-cache "${translated[@]}"
    else
        echo_error "Unsupported package manager for installation"
        return 1
    fi
}

pkg_install_list() {
    local raw="$1"
    if [ -z "$raw" ]; then
        return 0
    fi
    read -r -a packages <<< "$raw"
    pkg_install "${packages[@]}"
}

install_optional_extras() {
    if [ -z "$OPTIONAL_EXTRAS" ]; then
        return 0
    fi

    local decision="${KIAUH_KS_INSTALL_EXTRAS:-}"
    local install_choice
    local normalized

    if [ -n "$decision" ]; then
        install_choice="$decision"
    else
        echo_text "Optional extras provide fonts and media backends that are not required for a touch-ready KlipperScreen."
        echo "Press enter for default (No)"
        read -r -e -p "Install optional extras? [y/N]" install_choice
    fi

    normalized=$(printf '%s' "$install_choice" | tr '[:upper:]' '[:lower:]')

    if [[ "$normalized" =~ ^(y|yes|1)$ ]]; then
        echo_text "Installing optional KlipperScreen extras"
        if pkg_install_list "$OPTIONAL_EXTRAS"; then
            echo_ok "Installed optional extras"
        else
            echo_error "Installation of optional extras failed ($OPTIONAL_EXTRAS)"
            exit 1
        fi
    else
        echo_text "Skipping optional extras to keep the installation minimal"
    fi
}

ensure_group() {
    local group="$1"
    if command_exists groupadd; then
        $PRIV_CMD groupadd -f "$group"
    elif command_exists addgroup; then
        if ! getent group "$group" >/dev/null 2>&1; then
            $PRIV_CMD addgroup -S "$group"
        fi
    fi
}

add_user_to_group() {
    local user="$1"
    local group="$2"
    if command_exists usermod; then
        $PRIV_CMD usermod -a -G "$group" "$user"
    elif command_exists gpasswd; then
        $PRIV_CMD gpasswd -a "$user" "$group"
    elif command_exists addgroup; then
        $PRIV_CMD addgroup "$user" "$group"
    else
        echo_error "Unable to add $user to group $group"
    fi
}

install_graphical_backend()
{
  while true; do
    if [ -z "$BACKEND" ]; then
      echo_text ""
      echo_text "Choose graphical backend"
      echo_ok "Default is X11 (via Xorg)"
      echo_text "Wayland (cage) is experimental, requires KMS/DRM drivers, and currently disables DPMS on some devices"
      echo_text ""
      echo "Press enter for default (Xserver)"
      read -r -e -p "Backend Xserver or Wayland (cage)? [X/w]" BACKEND
    fi
    if [[ "$BACKEND" =~ ^[wW]$ ]]; then
        echo_text "Installing Wayland Cage kiosk components"
        if pkg_install_list "$CAGE"; then
            echo_ok "Installed Cage"
            BACKEND="W"
            break
        else
            echo_error "Installation of Cage dependencies failed ($CAGE)"
            exit 1
        fi
      else
        echo_text "Installing X server session packages"
        if pkg_install_list "$XSERVER"; then
            echo_ok "Installed X"
            if [ "$PKG_MANAGER" = "apt" ]; then
                update_x11
            fi
            BACKEND="X"
            break
        else
            echo_error "Installation of X-server dependencies failed ($XSERVER)"
            exit 1
        fi
    fi
  done

  if [ -n "$KIAUH_BACKEND_TRACK_FILE" ]; then
    printf '%s\n' "$BACKEND" > "$KIAUH_BACKEND_TRACK_FILE"
  fi
}

install_packages()
{
    echo_text "Update package data"
    if ! pkg_update; then
        exit 1
    fi

    if [ "$PKG_MANAGER" = "apt" ]; then
        echo_text "Checking for broken packages..."
        if dpkg-query -W -f='${db:Status-Abbrev} ${binary:Package}\n' | grep -E "^.[^nci]"; then
            echo_text "Detected broken packages. Attempting to fix"
            if ! $PRIV_CMD apt -f install; then
                echo_error "Unable to fix broken packages. These must be fixed before KlipperScreen can be installed"
                exit 1
            fi
            if dpkg-query -W -f='${db:Status-Abbrev} ${binary:Package}\n' | grep -E "^.[^nci]"; then
                echo_error "Unable to fix broken packages. These must be fixed before KlipperScreen can be installed"
                exit 1
            fi
        else
            echo_ok "No broken packages"
        fi
    else
        echo_text "Skipping broken package check on $PKG_MANAGER"
    fi

    echo_text "Installing KlipperScreen dependencies"

    if pkg_install_list "$PYGOBJECT"; then
        echo_ok "Installed PyGobject dependencies"
    else
        echo_error "Installation of PyGobject dependencies failed ($PYGOBJECT)"
        exit 1
    fi
    if pkg_install_list "$MISC"; then
        echo_ok "Installed Misc packages"
    else
        echo_error "Installation of Misc packages failed ($MISC)"
        exit 1
    fi

    install_optional_extras
}

check_requirements()
{
    VERSION="3,8"
    echo_text "Checking Python version > "$VERSION
    python3 --version
    if ! python3 -c 'import sys; exit(1) if sys.version_info <= ('$VERSION') else exit(0)'; then
        echo_error 'Not supported'
        exit 1
    fi
}

create_virtualenv()
{
    if [ "${KSENV}" = "/" ]; then
        echo_error "Failed to resolve venv location. Aborting."
        exit 1
    fi

    if [ -d "$KSENV" ]; then
        echo_text "Removing old virtual environment"
        rm -rf "${KSENV}"
    fi

    echo_text "Creating virtual environment"
    python3 -m venv "${KSENV}"

    if ! . "${KSENV}/bin/activate"; then
        echo_error "Could not activate the environment, try deleting ${KSENV} and retry"
        exit 1
    fi

    if [[ "$(uname -m)" =~ armv[67]l ]]; then
        echo_text "Using armv[67]l! Adding piwheels.org as extra index..."
        pip --disable-pip-version-check install --extra-index-url https://www.piwheels.org/simple -r ${KSPATH}/scripts/KlipperScreen-requirements.txt
    else
        pip --disable-pip-version-check install -r ${KSPATH}/scripts/KlipperScreen-requirements.txt
    fi
    if [ $? -gt 0 ]; then
        echo_error "Error: pip install exited with status code $?"
        echo_text "Trying again with build tools..."
        if ! pkg_install build-essential cmake libsystemd-dev; then
            echo_error "Unable to install additional build dependencies"
            deactivate
            exit 1
        fi
        if [[ "$(uname -m)" =~ armv[67]l ]]; then
            echo_text "Adding piwheels.org as extra index..."
            pip install --extra-index-url https://www.piwheels.org/simple --upgrade pip setuptools
            pip install --extra-index-url https://www.piwheels.org/simple -r ${KSPATH}/scripts/KlipperScreen-requirements.txt --prefer-binary
        else
            pip install --upgrade pip setuptools
            pip install -r ${KSPATH}/scripts/KlipperScreen-requirements.txt --prefer-binary
        fi
        if [ $? -gt 0 ]; then
            echo_error "Unable to install dependencies, aborting install."
            deactivate
            exit 1
        fi
    fi
    deactivate
    echo_ok "Virtual environment created"
}

install_systemd_service()
{
    if [ "$INIT_SYSTEM" != "systemd" ]; then
        echo_text "Non-systemd init detected. Skipping systemd service installation."
        return
    fi

    echo_text "Installing KlipperScreen unit file"

    SERVICE=$(cat "$SCRIPTPATH"/KlipperScreen.service)
    SERVICE=${SERVICE//KS_USER/$USER}
    SERVICE=${SERVICE//KS_ENV/$KSENV}
    SERVICE=${SERVICE//KS_DIR/$KSPATH}
    SERVICE=${SERVICE//KS_BACKEND/$BACKEND}

    echo "$SERVICE" | $PRIV_CMD tee /etc/systemd/system/KlipperScreen.service > /dev/null
    $PRIV_CMD systemctl unmask KlipperScreen.service
    $PRIV_CMD systemctl daemon-reload
    $PRIV_CMD systemctl enable KlipperScreen
    $PRIV_CMD systemctl set-default multi-user.target
    add_user_to_group "$USER" tty
}

create_policy()
{
    POLKIT_DIR="/etc/polkit-1/rules.d"
    POLKIT_USR_DIR="/usr/share/polkit-1/rules.d"

    echo_text "Installing KlipperScreen PolicyKit Rules"
    ensure_group klipperscreen
    ensure_group network
    add_user_to_group "$USER" netdev
    add_user_to_group "$USER" network
    if [ ! -x "$(command -v pkaction)" ]; then
        echo "PolicyKit not installed"
        return
    fi

    POLKIT_VERSION="$(pkaction --version | sed -n 's/[^0-9]*\([0-9.]*\).*/\1/p')"
    echo_text "PolicyKit Version ${POLKIT_VERSION} Detected"
    if [ "$POLKIT_VERSION" = "0.105" ]; then
        # install legacy pkla
        create_policy_legacy
        return
    fi

    RULE_FILE=""
    if [ -d $POLKIT_USR_DIR ]; then
        RULE_FILE="${POLKIT_USR_DIR}/KlipperScreen.rules"
    elif [ -d $POLKIT_DIR ]; then
        RULE_FILE="${POLKIT_DIR}/KlipperScreen.rules"
    else
        echo "PolicyKit rules folder not detected"
        exit 1
    fi
    echo_text "Installing PolicyKit Rules to ${RULE_FILE}..."
    $PRIV_CMD rm -f ${RULE_FILE}

    KS_GID=$( getent group klipperscreen | awk -F: '{printf "%d", $3}' )
    $PRIV_CMD tee ${RULE_FILE} > /dev/null << EOF_RULE
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 && subject.isInGroup("network")) {
        return polkit.Result.YES;
    }
});
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.login1.power-off" ||
         action.id == "org.freedesktop.login1.power-off-multiple-sessions" ||
         action.id == "org.freedesktop.login1.reboot" ||
         action.id == "org.freedesktop.login1.reboot-multiple-sessions" ||
         action.id == "org.freedesktop.login1.halt" ||
         action.id == "org.freedesktop.login1.halt-multiple-sessions" ||
         action.id.startsWith("org.freedesktop.NetworkManager.")) &&
        subject.user == "$USER") {
        return polkit.Result.YES;
        }
});
EOF_RULE
}

create_policy_legacy()
{
    RULE_FILE="/etc/polkit-1/localauthority/50-local.d/20-klipperscreen.pkla"
    $PRIV_CMD tee ${RULE_FILE} > /dev/null << EOF_LEGACY
[KlipperScreen]
Identity=unix-user:$USER
Action=org.freedesktop.login1.power-off;
       org.freedesktop.login1.power-off-multiple-sessions;
       org.freedesktop.login1.reboot;
       org.freedesktop.login1.reboot-multiple-sessions;
       org.freedesktop.login1.halt;
       org.freedesktop.login1.halt-multiple-sessions;
       org.freedesktop.NetworkManager.*
ResultAny=yes
EOF_LEGACY
}

update_x11()
{
    $PRIV_CMD tee /etc/X11/Xwrapper.config > /dev/null << EOF_X11
allowed_users=anybody
needs_root_rights=yes
EOF_X11
}

fix_fbturbo()
{
    if [ "$PKG_MANAGER" != "apt" ]; then
        return
    fi

    if [ "$(dpkg-query -W -f='${Status}' xserver-xorg-video-fbturbo 2>/dev/null | grep -c "ok installed")" -eq 0 ]; then
        FBCONFIG="/usr/share/X11/xorg.conf.d/99-fbturbo.conf"
        if [ -e $FBCONFIG ]; then
            echo_text "FBturbo not installed, but the configuration file exists"
            echo_text "This will fail if the config is not removed or the package installed"
            echo_text "moving the config to the home folder"
            $PRIV_CMD mv $FBCONFIG ~/99-fbturbo-backup.conf
        fi
    fi
}

add_desktop_file()
{
    mkdir -p "$HOME"/.local/share/applications/
    cp "$SCRIPTPATH"/KlipperScreen.desktop "$HOME"/.local/share/applications/KlipperScreen.desktop
    $PRIV_CMD cp "$SCRIPTPATH"/../styles/icon.svg /usr/share/icons/hicolor/scalable/apps/KlipperScreen.svg
}

start_KlipperScreen()
{
    if [ "$INIT_SYSTEM" = "systemd" ]; then
        echo_text "Starting systemd service..."
        $PRIV_CMD systemctl restart KlipperScreen
    elif [ "$INIT_SYSTEM" = "openrc" ]; then
        echo_text "Restarting OpenRC service if available..."
        if command_exists rc-service && rc-service KlipperScreen status >/dev/null 2>&1; then
            $PRIV_CMD rc-service KlipperScreen restart
        else
            echo_text "No OpenRC service for KlipperScreen to restart"
        fi
    else
        echo_text "Unknown init system. Please restart KlipperScreen manually."
    fi
}

install_network_manager()
{
    if [ -z "$NETWORK" ]; then
        echo "Press enter for default (Yes)"
        read -r -e -p "Install NetworkManager for the network panel [Y/n]" NETWORK
    fi

    if [[ $NETWORK =~ ^[nN]$ ]]; then
        echo_error "Not installing NetworkManager for the network panel"
    else
        echo_ok "Installing NetworkManager for the network panel"
        echo_text ""
        echo_text "If you were not using NetworkManager"
        echo_text "You will need to reconnect to the network using KlipperScreen or nmtui or nmcli"
        if ! pkg_install network-manager; then
            echo_error "Failed to install NetworkManager"
            return
        fi
        $PRIV_CMD mkdir -p /etc/NetworkManager/conf.d
        $PRIV_CMD tee /etc/NetworkManager/conf.d/any-user.conf > /dev/null << EOF_NM
[main]
auth-polkit=false
EOF_NM
        if [ "$INIT_SYSTEM" = "systemd" ]; then
            $PRIV_CMD systemctl -q disable dhcpcd 2> /dev/null
            $PRIV_CMD systemctl -q stop dhcpcd 2> /dev/null
            $PRIV_CMD systemctl enable NetworkManager
            $PRIV_CMD systemctl -q --no-block start NetworkManager
            sync
            echo_text "NetworkManager is now enabled and running. Please reboot manually to ensure the new network stack is fully active."
        elif [ "$INIT_SYSTEM" = "openrc" ]; then
            if command_exists rc-update; then
                $PRIV_CMD rc-update del dhcpcd default 2> /dev/null || true
                $PRIV_CMD rc-service dhcpcd stop 2> /dev/null || true
                $PRIV_CMD rc-update add NetworkManager default
                $PRIV_CMD rc-service NetworkManager start
            fi
            sync
            echo_text "Please reboot to ensure NetworkManager starts correctly."
        else
            echo_text "Unknown init system. Configure NetworkManager manually."
        fi
    fi
}

# Script start
if [ "$EUID" == 0 ]
    then echo_error "Please do not run this script as root"
    exit 1
fi
check_requirements

if [ -z "$SERVICE" ]; then
    echo_text "Install standalone?"
    echo_text "It will create a service, enable boot to console and install the graphical dependencies."
    echo_text ""
    echo_text "Say no to install as a regular desktop app that will not start automatically"
    echo_text ""
    echo "Press enter for default (Yes)"
    read -r -e -p "[Y/n]" SERVICE
fi

if [[ $SERVICE =~ ^[nN]$ ]]; then
    echo_text "Not installing the service"
    echo_text "The graphical backend will NOT be installed"
else
    install_graphical_backend
    install_systemd_service
    if [ -z "$START" ]; then
        START=1
    fi
fi

install_packages
create_virtualenv
create_policy
fix_fbturbo
add_desktop_file
install_network_manager
if [ -z "$START" ] || [ "$START" -eq 0 ]; then
    echo_ok "KlipperScreen was installed"
else
    start_KlipperScreen
fi
