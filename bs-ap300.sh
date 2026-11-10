#!/bin/bash

shopt -s expand_aliases

if [ -f ~/.alias ]; then
    source ~/.alias
fi

if [ -f ~/.bash_aliases ]; then
    source ~/.bash_aliases
fi

EUI_FILE="eui-list.txt"
MAX_ATTEMPTS=5

INSTALLER_URL="https://raw.githubusercontent.com/garry-nm/migration-basics-station/refs/heads/main/ap300-basic-station.py"
INSTALLER_FILE="ap300-basic-station.py"

TEMPLATE_URL="https://raw.githubusercontent.com/garry-nm/migration-basics-station/refs/heads/main/basicStation-template"
TEMPLATE_FILE="basicStation-template"

# Check EUI file
if [ ! -f "$EUI_FILE" ]; then
    echo "ERROR: EUI file '$EUI_FILE' not found." >&2
    exit 1
fi

if [ ! -r "$EUI_FILE" ]; then
    echo "ERROR: EUI file '$EUI_FILE' is not readable." >&2
    exit 1
fi

if [ ! -s "$EUI_FILE" ]; then
    echo "ERROR: EUI file '$EUI_FILE' is empty." >&2
    exit 1
fi


for eui in $(cat "$EUI_FILE"); do

    echo "=================================================="
    echo "Processing EUI: $eui"
    echo "=================================================="

    #
    # Step 1: Download installer
    #
    download_success=0

    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do

        echo "[$eui] Download installer attempt $attempt/$MAX_ATTEMPTS"

        gwl "$eui" \
            "curl -s -kf '$INSTALLER_URL' -o '$INSTALLER_FILE'"

        rc=$?

        if [ "$rc" -eq 0 ]; then
            echo "[$eui] Download installer SUCCESS"
            download_success=1
            break
        fi

        echo "[$eui] Download installer FAILED (exit code: $rc)"

        if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
            wait_time=$((attempt * 5))
            echo "[$eui] Waiting ${wait_time}s before retry..."
            sleep "$wait_time"
        fi

    done


    #
    # Do NOT download template if download installer failed
    #
    if [ "$download_success" -ne 1 ]; then
        echo "[$eui] ERROR: Download installer failed after $MAX_ATTEMPTS attempts"
        echo "[$eui] Template will NOT be downloaded."
        echo
        continue
    fi


    #
    # Step 2: Download template
    #
    download_success=0

    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do

        echo "[$eui] Download template attempt $attempt/$MAX_ATTEMPTS"

        gwl "$eui" \
            "curl -s -kf '$TEMPLATE_URL' -o '$TEMPLATE_FILE'"

        rc=$?

        if [ "$rc" -eq 0 ]; then
            echo "[$eui] Download template SUCCESS"
            download_success=1
            break
        fi

        echo "[$eui] Download template FAILED (exit code: $rc)"

        if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
            wait_time=$((attempt * 5))
            echo "[$eui] Waiting ${wait_time}s before retry..."
            sleep "$wait_time"
        fi

    done


    #
    # Do NOT run installer if download template failed
    #
    if [ "$download_success" -ne 1 ]; then
        echo "[$eui] ERROR: Download template failed after $MAX_ATTEMPTS attempts"
        echo "[$eui] Installer will NOT be executed."
        echo
        continue
    fi


    #
    # Step 2: Run installer
    #
    install_success=0

    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do

        echo "[$eui] Install attempt $attempt/$MAX_ATTEMPTS"

        gwl "$eui" \
            "python3 '$INSTALLER_FILE' '$eui'"

        rc=$?

        if [ "$rc" -eq 0 ]; then
            echo "[$eui] Install SUCCESS"
            install_success=1
            break
        fi

        echo "[$eui] Install FAILED (exit code: $rc)"

        if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
            wait_time=$((attempt * 5))
            echo "[$eui] Waiting ${wait_time}s before retry..."
            sleep "$wait_time"
        fi

    done


    if [ "$install_success" -ne 1 ]; then
        echo "[$eui] ERROR: Installer failed after $MAX_ATTEMPTS attempts"
    fi

    echo

done
