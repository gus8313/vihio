## Cbox

This program bridges your Palazzetti stove box with Home Assistant.

It uses Home Assistant MQTT discovery mechanism: https://www.home-assistant.io/docs/mqtt/discovery/ 

Checkout the project, either edit ```config/default.yml``` or create a ```config/local.yml``` with the properties you need to override. ```api_username``` and ```api_username``` are your Hi-Kumo app credentials. Then run ```Cbox.py```.

Please use, clone and improve. Some things are not supported. It was tested only with my own devices and installation. This is a very early release, based on reverse engineering of the network traffic. I have no relation to Hitachi (other than using their product) and they may not like it. Use at your own perils.

## Installation

### Setup MQTT discovery on HA
You will need an MQTT broker: [MQTT broker](https://www.home-assistant.io/docs/mqtt/broker/)

And to activate MQTT discovery: [MQTT discovery](https://www.home-assistant.io/docs/mqtt/discovery/)

### Clone the Cbox repo
```
git clone https://www.github.com/gus8313/cbox.git
cd cbox
pip3 install -r requirements.txt
```

### Change the configuration
You can either update the ```config/default.yml``` file or create a new file named ```config/local.yml```. The keys that are present in the local config will override the ones in the default config. If a key is absent from local config, Cbox will fallback to the value of the default config. I recommend keeping the default config as is and make all the changes in the local config file so that you don't lose them when the default file gets updated from git.

Property | Usage | Note
--- | --- | ---
**`devices`** | an array of device definitions | **Required**. Each device needs a `name` which is human friendly and a `hostname` which is the ip address or the hostname that the device uses on the network.   
`mqtt_discovery_prefix` | the MQTT topic prefix that HA is monitoring for discovery | You should probably not touch this. HA's default is `homeassistant`. 
`mqtt_state_prefix` | the MQTT topic prefix that Cbox will use to broadcast the devices state to HA | You should probably not touch this.
`mqtt_command_prefix` | the MQTT topic prefix that Cbox will listen to for HA commands | You should probably not touch this.
`mqtt_reset_topic` | the MQTT topic where Cbox receives reset commands | Send any message on this topic to tell Aasivak it must re-register all the devices. You should create an automation to do that every time HA starts.
**`mqtt_host`** | the host name or ip address of the MQTT broker | Use `localhost` or `127.0.0.1` if the MQTT broker runs on the same machine as Cbox.
`mqtt_client_name` | the name that Cbox will us on MQTT | You should probably not touch this.
`mqtt_discovery` | `on` to enable MQTT auto-discovery in HA | Change to `off` if you don't use HA or if you prefer configuring your devices manually 
`mqtt_config_retain` | `on` to retain configuration messages in MQTT | Change to `off` if you cannotor prefer not to retain config messages
`mqtt_state_retain` | `on` to retain state messages in MQTT | Change to `off` if you cannot or prefer not to retain state messages
`mqtt_username` | the MQTT broker username | This is needed only if the MQTT broker requires an authenticated connection.
`mqtt_password` | the MQTT broker password | This is needed only if the MQTT broker requires an authenticated connection.
`temperature_unit` | the temperature measurement unit | `°C` by default.
`pellets_quantity_unit` | the pellets quantity measurement unit | `kg` by default.
`refresh_delays` | list of waiting durations before calling the box API to refresh devices state | If you set `[2, 5, 10, 30]` then Cbox will call the Hi-Kumo API to refresh its state after 2s, then 5s, then 10s, and then every 30s. The delay is reset to 2s when Cbox receives a command from HA. Some randomness is added to these delays: every time Cbox needs to wait, it adds or remove up to `logging_delay_randomness/2` to the delay. 
`refresh_delay_randomness` | maximum number of seconds to add to all the waiting durations | See `refresh_delays`. Use `0` for no randomness.
`offline_timeout` | number of seconds after which the unit will be reported offline if it does not respond API requests | 120 by default.
`logging_level` | Cbox's logging level | INFO


### Start Cbox manually
```
python3 Cbox.py
```

### Start Cbox as a systemd service
Create the following ```/etc/systemd/system/Cbox.service``` file (change the paths as required):

```
[Unit]
Description=Cbox
Documentation=https://github.com/dotvav/Cbox
After=network.target

[Service]
Type=simple
User=homeassistant
WorkingDirectory=/home/homeassistant/Cbox
ExecStart=/usr/bin/python3 /home/homeassistant/Cbox/Cbox.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Run the following to enable and run the service, and see what its status is:
```
sudo systemctl enable Cbox.service
sudo systemctl start Cbox.service
sudo systemctl status Cbox.service
```

### Run in docker
```
docker build -t cbox cbox/
docker run -d --name="cbox" --restart on-failure cbox
```

## Dependencies

- requests
- paho-mqtt
- pyyaml


