import difflib
import json
import os
import subprocess
import sys
from datetime import datetime

import requests
import urllib3


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

GET_URL = "https://localhost/api?fields=loraNetwork"
PUT_URL = "http://localhost/api/loraNetwork"
SAVE_APPLY_URL = "http://localhost/api/command/save_apply?allowRestart=false"

STORE_FILE = "tmp-store.json"
BASIC_STATION_TEMPLATE = "basicStation-template"
OUTPUT_FILE = "loraNetwork-updated.json"

EUI_PLACEHOLDER = "EUI-TO-BE-REPLACED"
APP_NAME = "netmore"

# Equivalent to curl -k
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GET_HEADERS = {
    "Accept": "application/json",
}

PUT_HEADERS = {
    
"Accept": "application/json",
    "Content-Type": "application/json",
}

# ---------------------------------------------------------
# Local command execution
# ---------------------------------------------------------

def run_command(command):
    """
    Run a local command and return its standard output.

    Raises RuntimeError if the command exits with a non-zero
    return code.
    """

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        error_message = result.stderr.strip()

        if not error_message:
            error_message = result.stdout.strip()

        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(command)}\n"
            f"{error_message}"
        )

    return result.stdout


# ---------------------------------------------------------
# Application handling
# ---------------------------------------------------------

def get_installed_apps():
    """
    Run:

        app-manager --command list-installed

    Parse the JSON response and return its Apps list.
    """

    output = run_command(
        [
            "app-manager",
            "--command",
            "list-installed",
        ]
    )

    try:
        data = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "app-manager list-installed returned invalid JSON:\n"
            f"{output}"
        ) from error

    apps = data.get("Apps")

    if not isinstance(apps, list):
        raise RuntimeError(
            "app-manager output does not contain a valid "
            "'Apps' list"
        )

    return apps


def find_app(app_name):
    """
    Find an installed application by AppName.
    """

    for app in get_installed_apps():
        if app.get("AppName") == app_name:
            return app

    raise RuntimeError(
        f"Application '{app_name}' was not found"
    )


def stop_app(app_name):
    """
    Find the application's current AppId, stop it if needed,
    and verify that its status becomes STOPPED.
    """

    app = find_app(app_name)

    app_id = app.get("AppId")
    app_status = app.get("status", "UNKNOWN")

    if not app_id:
        raise RuntimeError(
            f"Application '{app_name}' does not have an AppId"
        )

    print(
        f"Found application: "
        f"AppName={app_name}, "
        f"AppId={app_id}, "
        f"status={app_status}"
    )

    if app_status == "STOPPED":
        print(
            f"Application '{app_name}' is already stopped."
        )
        return app_id

    print(
        f"Stopping application '{app_name}' "
        f"with AppId '{app_id}'..."
    )

    stop_output = run_command(
        [
            "app-manager",
            "--command",
            "stop",
            "--appid",
            app_id,
        ]
    )

    if stop_output.strip():
        print(stop_output.strip())

    # Query app-manager again to verify the resulting status.
    updated_app = find_app(app_name)
    updated_status = updated_app.get("status", "UNKNOWN")

    if updated_status != "STOPPED":
        raise RuntimeError(
            f"Application '{app_name}' did not stop. "
            f"Current status: {updated_status}"
        )

    print(
        f"Application '{app_name}' successfully stopped."
    )

    return app_id


def main():

    # ---------------------------------------------------------
    # 1. Get EUI from command line
    # ---------------------------------------------------------

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <EUI>")
        print()
        print(f"Example:")
        print(f"  {sys.argv[0]} 00800000D00002C3")
        sys.exit(1)

    eui = sys.argv[1]

    print(f"EUI: {eui}")

    try:
        # -----------------------------------------------------
        # 2. Get latest configuration from gateway
        # -----------------------------------------------------

        response = requests.get(
            GET_URL,
            headers=GET_HEADERS,
            verify=False,
            timeout=30
        )

        response.raise_for_status()
        latest_data = response.json()

        print(f"HTTP status: {response.status_code}")

        # -----------------------------------------------------
        # 3. Normalize latest response for comparison
        # -----------------------------------------------------

        latest_json = json.dumps(
            latest_data,
            indent=4,
            sort_keys=True
        ) + "\n"

        # -----------------------------------------------------
        # 4. Compare against previous response
        # -----------------------------------------------------

        if os.path.exists(STORE_FILE):

            with open(STORE_FILE, "r") as f:
                previous_data = json.load(f)

            previous_json = json.dumps(
                previous_data,
                indent=4,
                sort_keys=True
            ) + "\n"

            diff = difflib.unified_diff(
                previous_json.splitlines(keepends=True),
                latest_json.splitlines(keepends=True),
                fromfile=f"{STORE_FILE} (previous)",
                tofile="latest gateway response"
            )

            diff_text = "".join(diff)

            if diff_text:

                print("\nConfiguration changes detected:\n")
                print(diff_text, end="")

                timestamp = datetime.now().strftime(
                    "%Y%m%d-%H%M%S"
                )

                diff_file = f"diff-{timestamp}.txt"

                with open(diff_file, "w") as f:
                    f.write(diff_text)

                print(f"\nDiff saved to: {diff_file}")

            else:
                print("\nNo changes detected.")

        else:
            print(f"\n{STORE_FILE} does not exist.")
            print(
                "This is the first run, "
                "so there is nothing to compare."
            )

        # -----------------------------------------------------
        # 5. Save actual latest gateway configuration
        # -----------------------------------------------------

        with open(STORE_FILE, "w") as f:
            f.write(latest_json)

        print(f"Latest gateway response saved to: {STORE_FILE}")

        # -----------------------------------------------------
        # 6. Read basicStation-template
        # -----------------------------------------------------

        if not os.path.exists(BASIC_STATION_TEMPLATE):
            raise FileNotFoundError(
                f"{BASIC_STATION_TEMPLATE} does not exist"
            )

        with open(BASIC_STATION_TEMPLATE, "r") as f:
            basic_station_template = json.load(f)

        print(
            f"Loaded basicStation configuration from: "
            f"{BASIC_STATION_TEMPLATE}"
        )

        # -----------------------------------------------------
        # 7. Check that conf exists and is a string
        # -----------------------------------------------------

        if "conf" not in basic_station_template:
            raise KeyError(
                "conf not found in basicStation-template"
            )

        if not isinstance(basic_station_template["conf"], str):
            raise TypeError(
                "basicStation-template 'conf' must be a string"
            )

        # -----------------------------------------------------
        # 8. Replace EUI placeholder inside basicStation-template
        # -----------------------------------------------------

        conf = basic_station_template["conf"]

        replacement_count = conf.count(EUI_PLACEHOLDER)

        if replacement_count == 0:
            print(
                f"WARNING: '{EUI_PLACEHOLDER}' "
                "not found in basicStation-template"
            )
        else:
            basic_station_template["conf"] = conf.replace(
                EUI_PLACEHOLDER,
                eui
            )

            print(
                f"Replaced {replacement_count} occurrence(s) of "
                f"'{EUI_PLACEHOLDER}' with '{eui}' "
                "in basicStation-template"
            )

        # -----------------------------------------------------
        # 9. Verify latest response contains loraNetwork
        # -----------------------------------------------------

        if "loraNetwork" not in latest_data["result"]:
            raise KeyError(
                "loraNetwork not found in latest API response"
            )

        if not isinstance(latest_data["result"]["loraNetwork"], dict):
            raise TypeError(
                "loraNetwork in API response is not a JSON object"
            )

        # -----------------------------------------------------
        # 10. Replace loraNetwork.basicStation
        # -----------------------------------------------------

        latest_data = latest_data["result"]["loraNetwork"]
        latest_data["basicStation"] = (
            basic_station_template
        )

        print(
            "Replaced latest loraNetwork.basicStation "
            "with basicStation-template"
        )

        # -----------------------------------------------------
        # 11. Update loraNetwork.lora
        # -----------------------------------------------------

        latest_data["lora"]["enabled"] = True
        latest_data["lora"]["basicStationMode"] = True
        latest_data["lora"]["packetForwarderMode"] = False

        # -----------------------------------------------------
        # 12. Save updated complete configuration
        # -----------------------------------------------------

        with open(OUTPUT_FILE, "w") as f:
            json.dump(
                latest_data,
                f,
                indent=4
            )
            f.write("\n")

        print(f"Updated configuration saved to: {OUTPUT_FILE}")

        # -----------------------------------------------------
        # 13. PUT updated configuration back to gateway
        # -----------------------------------------------------
        #
        # Python equivalent of:
        #
        # curl -X PUT http://localhost/api/loraNetwork \
        #   -H 'Accept: application/json' \
        #   -H 'Content-Type: application/json' \
        #   --data-raw '<JSON>'
        #
        # requests json= automatically JSON-encodes the dict
        # and sends Content-Type: application/json.
        # -----------------------------------------------------

        print("\nUpdating gateway configuration...")

        put_response = requests.put(
            PUT_URL,
            headers=PUT_HEADERS,
            json=latest_data,
            timeout=30
        )

        # Display response before raising an exception.
        # This is useful if the gateway returns an API error
        # explaining why a configuration was rejected.
        print(f"PUT HTTP status: {put_response.status_code}")

        if put_response.text.strip():
            print("PUT response:")
            print(put_response.text)

        put_response.raise_for_status()

        print("\nGateway configuration updated successfully.")

        # -----------------------------------------------------
        # 14. Save and apply configuration
        # -----------------------------------------------------
        #
        # Equivalent to:
        #
        # curl -X POST -d '{}' \
        #   'http://localhost/api/command/save_apply?allowRestart=false' \
        #   -H 'Accept: application/json' \
        #   -H 'Content-Type: application/json'
        #
        # -----------------------------------------------------

        print("\nSaving and applying gateway configuration...")

        save_apply_response = requests.post(
            SAVE_APPLY_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={},
            timeout=30
        )

        print(
            f"Save/apply HTTP status: "
            f"{save_apply_response.status_code}"
        )

        if save_apply_response.text.strip():
            print("Save/apply response:")
            print(save_apply_response.text)

        save_apply_response.raise_for_status()

        print("\nGateway configuration saved and applied successfully.")

        # -----------------------------------------------------
        # 15. Find and stop the Netmore application
        # -----------------------------------------------------

        print(
            f"\nChecking application '{APP_NAME}'..."
        )

        app_id = stop_app(APP_NAME)

        print(
            f"\nApplication '{APP_NAME}' "
            f"(AppId={app_id}) is STOPPED."
        )

    # ---------------------------------------------------------
    # Error handling
    # ---------------------------------------------------------

    except requests.RequestException as e:
        print(f"HTTP request failed: {e}")
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)

    except KeyError as e:
        print(f"Missing JSON field: {e}")
        sys.exit(1)

    except TypeError as e:
        print(f"Invalid JSON structure: {e}")
        sys.exit(1)

    except ValueError as error:
        print(f"\nInvalid value: {error}")
        sys.exit(1)

    except RuntimeError as error:
        print(f"\nCommand failed: {error}")
        sys.exit(1)

    except OSError as e:
        print(f"File operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
