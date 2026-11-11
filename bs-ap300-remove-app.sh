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
    # Step 1: Remove netmore application
    #

    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do

        echo "[$eui] Remove netmore application attempt $attempt/$MAX_ATTEMPTS"

        gwl "$eui" \
            "app-manager --command remove --appid e2"

        rc=$?

        if [ "$rc" -eq 0 ]; then
            echo "[$eui] Remove netmore application SUCCESS"
            break
        fi

        echo "[$eui] Remove netmore application FAILED (exit code: $rc)"

        if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
            wait_time=$((attempt * 5))
            echo "[$eui] Waiting ${wait_time}s before retry..."
            sleep "$wait_time"
        fi

    done

done
