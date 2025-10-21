#!/usr/bin/env bash

#=======================================================================#
# Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>       #
#                                                                       #
# This file is part of KIAUH - Klipper Installation And Update Helper   #
# https://github.com/dw-0/kiauh                                         #
#                                                                       #
# This file may be distributed under the terms of the GNU GPLv3 license #
#=======================================================================#

set -e
clear -x

# make sure we have the correct permissions while running the script
umask 022

#===================================================#
#=================== GLOBAL VARS ===================#
#===================================================#

readonly KIAUH_SRCDIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
readonly DEFAULT_KIAUH_REPO="https://github.com/postmarketOS-community/postmarketos-kiauh.git"
declare -ar LEGACY_KIAUH_REPOS=(
  "https://github.com/dw-0/kiauh.git"
  "git@github.com:dw-0/kiauh.git"
  "https://github.com/dw-0/kiauh"
  "git@github.com:dw-0/kiauh"
)

: "${KIAUH_REPO_URL:=${DEFAULT_KIAUH_REPO}}"

#===================================================#
#==================== UTILITIES ====================#
#===================================================#

function _kiauh_get_current_branch() {
  local current_branch

  current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

  if [[ -z "${current_branch}" || "${current_branch}" == "HEAD" ]]; then
    current_branch=$(git remote show origin 2>/dev/null | sed -n '/HEAD branch/s/.*: //p')
  fi

  echo "${current_branch}"
}

function _kiauh_should_update_remote() {
  local current_url legacy

  current_url=$(git config --get remote.origin.url 2>/dev/null)

  if [[ -z "${current_url}" ]]; then
    return 0
  fi

  for legacy in "${LEGACY_KIAUH_REPOS[@]}"; do
    if [[ "${current_url}" == "${legacy}" ]]; then
      return 0
    fi
  done

  return 1
}

function _kiauh_ensure_origin_remote() {
  local current_url

  current_url=$(git config --get remote.origin.url 2>/dev/null)

  if _kiauh_should_update_remote; then
    if [[ -z "${current_url}" ]]; then
      status_msg "Setting KIAUH origin remote to ${KIAUH_REPO_URL}"
      git remote add origin "${KIAUH_REPO_URL}"
    else
      status_msg "Switching KIAUH origin remote to ${KIAUH_REPO_URL}"
      git remote set-url origin "${KIAUH_REPO_URL}"
    fi
  fi
}

#===================================================#
#=================== UPDATE KIAUH ==================#
#===================================================#

function update_kiauh() {
  status_msg "Updating KIAUH ..."

  cd "${KIAUH_SRCDIR}"

  _kiauh_ensure_origin_remote

  local branch
  branch=$(_kiauh_get_current_branch)

  if [[ -z "${branch}" ]]; then
    echo "Unable to determine the active branch for KIAUH updates."
    exit 1
  fi

  if ! git fetch origin "${branch}"; then
    echo "Fetching updates for branch '${branch}' failed."
    exit 1
  fi

  git reset --hard "origin/${branch}"

  ok_msg "Update complete! Please restart KIAUH."
  exit 0
}

#===================================================#
#=================== KIAUH STATUS ==================#
#===================================================#

function kiauh_update_avail() {
  [[ ! -d "${KIAUH_SRCDIR}/.git" ]] && return
  local origin head branch

  cd "${KIAUH_SRCDIR}"

  _kiauh_ensure_origin_remote

  branch=$(_kiauh_get_current_branch)

  [[ -z "${branch}" ]] && return

  if ! git ls-remote --exit-code --heads origin "${branch}" &>/dev/null; then
    return
  fi

  ### compare commit hash
  git fetch -q origin "${branch}"
  origin=$(git rev-parse --short=8 "origin/${branch}")
  head=$(git rev-parse --short=8 HEAD)

  if [[ ${origin} != "${head}" ]]; then
    echo "true"
  fi
}

function kiauh_update_dialog() {
  [[ ! $(kiauh_update_avail) == "true" ]] && return
  echo -e "/-------------------------------------------------------\\"
  echo -e "|${green}              New KIAUH update available!              ${white}|"
  echo -e "|-------------------------------------------------------|"
  echo -e "|${green}  View Changelog: https://git.io/JnmlX                 ${white}|"
  echo -e "|                                                       |"
  echo -e "|${yellow}  It is recommended to keep KIAUH up to date. Updates  ${white}|"
  echo -e "|${yellow}  usually contain bugfixes, important changes or new   ${white}|"
  echo -e "|${yellow}  features. Please consider updating!                  ${white}|"
  echo -e "\-------------------------------------------------------/"

  local yn
  read -p "${cyan}###### Do you want to update now? (Y/n):${white} " yn
  while true; do
    case "${yn}" in
     Y|y|Yes|yes|"")
       do_action "update_kiauh"
       break;;
     N|n|No|no)
       break;;
     *)
       deny_action "kiauh_update_dialog";;
    esac
  done
}

function check_euid() {
  if [[ ${EUID} -eq 0 ]]; then
    echo -e "${red}"
    echo -e "/-------------------------------------------------------\\"
    echo -e "|       !!! THIS SCRIPT MUST NOT RUN AS ROOT !!!        |"
    echo -e "|                                                       |"
    echo -e "|        It will ask for credentials as needed.         |"
    echo -e "\-------------------------------------------------------/"
    echo -e "${white}"
    exit 1
  fi
}

function check_if_ratos() {
  if [[ -n $(which ratos) ]]; then
    echo -e "${red}"
    echo -e "/-------------------------------------------------------\\"
    echo -e "|        !!! RatOS 2.1 or greater detected !!!          |"
    echo -e "|                                                       |"
    echo -e "|        KIAUH does currently not support RatOS.        |"
    echo -e "| If you have any questions, please ask for help on the |"
    echo -e "| RatRig Community Discord: https://discord.gg/ratrig   |"
    echo -e "\-------------------------------------------------------/"
    echo -e "${white}"
    exit 1
  fi
}

function main() {
   local entrypoint

   if ! command -v python3 &>/dev/null || [[ $(python3 -V | cut -d " " -f2 | cut -d "." -f2) -lt 8 ]]; then
     echo "Python 3.8 or higher is not installed!"
     echo "Please install Python 3.8 or higher and try again."
     exit 1
   fi

   entrypoint="${KIAUH_SRCDIR}"

   export PYTHONPATH="${entrypoint}"

   clear -x
   python3 "${entrypoint}/kiauh/main.py"
}

check_if_ratos
check_euid
kiauh_update_dialog
main
