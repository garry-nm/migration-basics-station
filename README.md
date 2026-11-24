# migration-basics-station
Basics Stations migration for Browan Gempiconext and Multitech AP300 gateways.

### Instructions:
1. Populate eui-list.txt with the list of gateway EUIs to be migrated. Do not mix both models.
2. For Browan Gempiconext, run ./bs-piconext.sh.
3. For Multitech AP300, run ./bs-ap300.sh.

### Browan Gempiconext specifics:
1. bs-piconext.sh script will loop through each gateway EUI listed in eui-list.txt.
2. For each gateway, it will download installer-cups_v1.0.sh using the gwl (gateway-login).
3. After the download, it will execute the installer-cups_v1.0.sh via gwl to start the migration.
4. Internally, installer-cups_v1.0.sh uses uci utility to configure the basics station, download the CA trust certificate, and create the trust uri file.

### Multitech AP300 specifics:
1. bs-ap300.sh script will loop through each gateway EUI listed in eui-list.txt.
2. For each gateway, it will download ap300-basic-station.py and basicStation-template using the gwl (gateway-login).
3. After the download, it will execute the ap300-basic-station.py via gwl to start the migration.
4. Internally ap300-basic-station.py gets the current gateway configuration, replaces the basics station section, and then update the new configuration to the gateway.
5. In addition, the script also stops the custom app "netmore".

### Possible issues during Multitech AP300 migration:

#### Failure to delete or remove the custom application via the CLI.
```
admin@mtcap3:~$ app-manager --command list-installed
{
        "Apps" : 
        [
                {
                        "AppDescription" : "Gateway configuration for Netmore LoRaWAN",
                        "AppId" : "e2",
                        "AppName" : "netmore",
                        "AppType" : "CUSTOM",
                        "AppVersion" : "1.1",
                        "AppVersionNotes" : "",
                        "Enabled" : true,
                        "PersistentStorage" : true,
                        "status" : "STARTED"
                }
        ]
}

admin@mtcap3:~$ app-manager --command remove --appid e2
Failed to get lock file, errno = 9 , exiting
```

To resolve this, the custom application needs to be removed via the GUI. After the removal:
```
admin@mtcap3:~$ app-manager --command list-installed             
{
        "Apps" : []
}
```

