#!/bin/sh
set -e

apn=iot.1nce.net
version="0.5"

# Platform
#platform='thingparkenterprise.au.actility.com'
#platform='thingparkenterprise.eu.actility.com'
platform='thingparkenterprise.eu2.actility.com'

# Update network
update_network=0

# RAT installation
install_rat=0

while [ $# -gt 0 ]; do
    case "$1" in
        --apn)
            apn="$2"
            shift
            ;;
        -v | --version)
            echo "$version"
            exit 0
            ;;
        -h | --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --apn <apn>           Set the APN to use (default: iot.1nce.net)"
            echo "  -v, --version         Display latest config version"
            echo "  -h, --help            Display this help"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
    esac
    shift
done

# ---------------------------------------------------------------

log_action() {
    printf '%-31s' "$1..."
}

log_result() {
    printf '%s\n' "$1"
}

# ---------------------------------------------------------------
echo ".-------------------------------."
echo "| Netmore Browan installer v$version |"
echo "'-------------------------------'"

# --- System ----------------------------------------------------
log_action "Checking hardware"
if ! uname -a | grep -qi "Linux browan" || [ ! -f /usr/bin/uci ]; then
    log_result "This device is not a valid Browan gateway, install cancelled"
    exit 2
fi
log_result "OK (Browan Gateway)"

# --- User ------------------------------------------------------
log_action "Checking user"
if [ "$USER" != "root" ]; then
    log_result "You must run this installer as root, install cancelled"
    exit 3
fi
log_result "OK ($USER)"

# --- Firmware --------------------------------------------------
log_action "Checking firmware"
fw_version=$(cat /etc/version)
fw_version_major=$(echo "$fw_version" | cut -d'.' -f1)
fw_version_minor=$(echo "$fw_version" | cut -d'.' -f2)
fw_version_patch=$(echo "$fw_version" | cut -d'.' -f3)
if [ -z "$fw_version_major" ] || [ -z "$fw_version_minor" ] || [ -z "$fw_version_patch" ]; then
    log_result "cannot read firmware version, install cancelled"
    exit 4
# Temporarily remove the minimal version requirement. What is the reason for requiring >= 1.2.55?
#elif [ "$fw_version_major" -eq 1 ] && [ "$fw_version_minor" -eq 2 ] && [ "$fw_version_patch" -ge 55 ]; then
elif [ "$fw_version_major" -eq 1 ] && [ "$fw_version_minor" -eq 1 ] && [ "$fw_version_patch" -ge 53 ]; then
    log_result "OK ($fw_version)"
else
    log_result "unsupported firmware version ($fw_version), install cancelled"
    exit 5
fi

# --- LoRaWAN ---------------------------------------------------
log_action "Configuring Basics Station"
uci set lora.config.mode=basicstation
uci commit lora
uci import basicstation < /dev/null
uci set basicstation.config=settings
uci set basicstation.config.mode='cups'
uci set basicstation.config.type='boot'
uci set basicstation.config.protocol='https'
uci set basicstation.config.srvAddress="$platform"
uci set basicstation.config.srvPort='443'
uci set basicstation.config.srvUri="https://$platform:443"
uci set basicstation.config.gwAuthMode='disabled'
uci commit basicstation
echo "https://$platform:443" > /app/basicstation/cups-boot.uri
curl --fail --silent --insecure --output /app/basicstation/cups-boot.trust https://www.amazontrust.com/repository/AmazonRootCA1.pem
log_result "OK"

if [ "$update_network" -eq 1 ]; then
    # --- Network ---------------------------------------------------
    log_action "Configuring network"
    uci set network.wan.wantype=3g_eth
    uci set network.wan.proto=dhcp
    uci set network.wan.apn=$apn
    uci set network.wan.pincode='NA'
    uci set network.wan.username='NA'
    uci set network.wan.password='NA'
    uci set network.wan.dial_num='NA'
    uci set network.wan.authMode='NONE'
    uci commit network
    uci set dualwan.dwan.priority=eth0
    uci set dualwan.dwan.enable=1
    uci commit dualwan
    log_result "OK (Dual WAN)"
    log_action "Configuring APN"
    uci set module_34g.dev_info.apn=$apn
    uci commit module_34g
    cp /etc/network/interfaces_dhcp /etc/network/interfaces
    log_result "OK ($apn)"
fi

# Get the gateway EUI
eui=$(uci get pktfwder.gateway.gateway_id)

if [ "$install_rat" -eq 1 ]; then
    # --- RAT -------------------------------------------------------
    log_action "Configuring remote access"
    nratFile=/tmp/nrat.sh
    curl --fail --silent --insecure https://docs.netmoregroup.com/downloads/rat/netmore-rat-installer.sh -o $nratFile
    # Specify the EUI explicitly to nrat
    #if sh $nratFile > /dev/null; then
    if sh $nratFile --eui $eui > /dev/null; then
        rm $nratFile
        log_result "OK"
    else
        ec="$?"
        if [ "$ec" -eq 3 ] || [ "$ec" -eq 4 ]; then
            log_result "OK (already setup)"
            rm $nratFile
        else
            log_result "failed ($ec)"
            exit 6
        fi
    fi
fi

# --- Restart ---------------------------------------------------
log_action "Restarting services"
$(ls /etc/init.d/S*lora) restart > /dev/null 2>&1
log_result "OK"

# --- Summary ---------------------------------------------------
serial=$(cat /sys/class/net/eth0/address |sed 's/\://g')
model=$(cat /etc/os-release | grep "NAME" | sed 's/NAME=//' | head -n 1)
echo ""
#echo "EUI:      $eui (https://portal.blink.services/net/gateways?gwEui=$eui)"
echo "EUI:      $eui"
echo "Serial:   $serial"
echo "Model:    $model"
#echo "PF:       Basics Station"
echo "PF:       Basics Station @ $platform"
echo ""
echo "Setup done."