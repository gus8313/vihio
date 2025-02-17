import json
import random
import time
import logging

import paho.mqtt.client as mqtt
import requests
import yaml

################

class Device:

    # Based on the Android app mapping: https://pastebin.com/VQjYtzAn
    status_names = {
        0: "Off",
        1: "Timer-regulated switch off",
        10: "Switch off",
        1000: "General error – See Manual",
        1001: "General error – See Manual",
        11: "Burn pot cleaning",
        12: "Cooling in progress",
        1239: "Door open",
        1240: "Temperature too high",
        1241: "Cleaning warning",
        1243: "Fuel error – See Manual",
        1244: "Pellet probe or return water error",
        1245: "T05 error Disconnected or faulty probe",
        1247: "Feed hatch or door open",
        1248: "Safety pressure switch error",
        1249: "Main probe failure",
        1250: "Flue gas probe failure",
        1252: "Too high exhaust gas temperature",
        1253: "Pellets finished or Ignition failed",
        1508: "General error – See Manual",
        2: "Ignition test",
        3: "Pellet feed",
        4: "Ignition",
        5: "Fuel check",
        50: "Final cleaning",
        501: "Off",
        502: "Ignition",
        503: "Fuel check",
        504: "Operating",
        505: "Firewood finished",
        506: "Cooling",
        507: "Burn pot cleaning",
        51: "Ecomode",
        6: "Operating",
        7: "Operating - Modulating",
        8: "-",
        9: "Stand-By"
    }
    fanspd_names = {
        0: "off",
        1: "1",
        2: "2",
        3: "3",
        4: "4",
        5: "5",
        6: "hi",
        7: "auto",
    }
    fanspd_val = {
        "off": "0",
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "hi": "6",
        "auto": "7",
    }

    is_heating_statuses = [2, 3, 4, 5, 502, 503, 504, 51, 6, 7]

    def __init__(self, house, device_id, name, hostname):
        self.house = house
        self.device_id = device_id
        self.name = name
        self.hostname = hostname
        self.climate_discovery_topic = None
        self.climate_mqtt_config = None
        self.status_sensor_discovery_topic = None
        self.status_sensor_mqtt_config = None
        self.exit_temp_sensor_discovery_topic = None
        self.exit_temp_sensor_mqtt_config = None
        self.fumes_temp_sensor_discovery_topic = None
        self.fumes_temp_sensor_mqtt_config = None
        self.pellet_qty_sensor_discovery_topic = None
        self.pellet_qty_sensor_mqtt_config = None
        self.fan_spd_sensor_discovery_topic = None
        self.fan_spd_sensor_mqtt_config = None
        self.power_lvl_sensor_discovery_topic = None
        self.power_lvl_sensor_mqtt_config = None
        self.timer_sensor_discovery_topic = None
        self.timer_sensor_mqtt_config = None
        self.target_temperature = None
        self.temp_step = None
        self.room_temperature = None
        self.exit_temperature = None
        self.fumes_temperature = None
        self.pellet_quantity = None
        self.fan_speed = None
        self.power_level = None
        self.timer_state = None
        self.status = None
        self.mode = None
        self.topic_to_func = None
        self.availability = "offline"
        self.last_update = 0

    def __str__(self):
        return json.dumps({
            'name': self.name,
            'hostname': self.hostname,
            'climate_discovery_topic': self.climate_discovery_topic,
            'climate_mqtt_config': self.climate_mqtt_config,
            'status_sensor_discovery_topic': self.status_sensor_discovery_topic,
            'status_sensor_mqtt_config': self.status_sensor_mqtt_config,
            'exit_temp_sensor_discovery_topic': self.exit_temp_sensor_discovery_topic,
            'exit_temp_sensor_mqtt_config': self.exit_temp_sensor_mqtt_config,
            'fumes_temp_sensor_discovery_topic': self.fumes_temp_sensor_discovery_topic,
            'fumes_temp_sensor_mqtt_config': self.fumes_temp_sensor_mqtt_config,
            'pellet_qty_sensor_discovery_topic': self.pellet_qty_sensor_discovery_topic,
            'pellet_qty_sensor_mqtt_config': self.pellet_qty_sensor_mqtt_config,
            'fan_spd_sensor_discovery_topic': self.fan_spd_sensor_discovery_topic,
            'fan_spd_sensor_mqtt_config': self.fan_spd_sensor_mqtt_config,
            'power_lvl_sensor_discovery_topic': self.power_lvl_sensor_discovery_topic,
            'power_lvl_sensor_mqtt_config': self.power_lvl_sensor_mqtt_config,
            'timer_sensor_discovery_topic': self.timer_sensor_discovery_topic,
            'timer_sensor_mqtt_config': self.timer_sensor_mqtt_config,
            'target_temperature': self.target_temperature,
            'temp_step': self.temp_step,
            'room_temperature': self.room_temperature,
            'exit_temperature': self.exit_temperature,
            'fumes_temperature': self.fumes_temperature,
            'pellet_quantity': self.pellet_quantity,
            'fan_speed': self.fan_speed,
            'power_level': self.power_level,
            'timer_state': self.timer_state,
            'status': self.status,
            'mode': self.mode
        })

    def update_state(self, data):
        self.target_temperature = data["SETP"]
        self.temp_step = self.house.config.temp_step
        self.room_temperature = data["T1"]
        self.exit_temperature = data["T2"]
        self.fumes_temperature = data["T3"]
        self.pellet_quantity = float(data["PQT"])
        self.fan_speed = self.fanspd_names.get(data["F2L"], "Off")
        self.power_level = data["PWR"]
        self.timer_state = "on" if data["CHRSTATUS"] == 1 else "off"
        self.status = self.status_names.get(data["LSTATUS"], "Off")
        self.mode = "heat" if data["LSTATUS"] in self.is_heating_statuses else "off"
        if time.time() - self.last_update < self.house.config.offline_timeout:
            self.availability = "online"
        else:
            self.availability = "offline"
        self.last_update = time.time()

    def update_mqtt_config(self):
        self.climate_discovery_topic = self.house.config.mqtt_discovery_prefix + "/climate/" + self.device_id + "/config"
        self.climate_mqtt_config = {
            "name": self.name,
            "unique_id": self.device_id,

            "current_temperature_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/temp",
            "mode_state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/mode",
            "temperature_state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/target_temp",
            "fan_mode_state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/fan_speed",
            "hold_state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/power_level",
            "swing_mode_state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/timer",
            "availability_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/availability",

            "mode_command_topic": self.house.config.mqtt_command_prefix + "/" + self.device_id + "/mode",
            "temperature_command_topic": self.house.config.mqtt_command_prefix + "/" + self.device_id + "/target_temp",
            "temp_step": self.house.config.mqtt_command_prefix + "/" + self.device_id + "/temp_step",
            "fan_mode_command_topic": self.house.config.mqtt_command_prefix + "/" + self.device_id + "/fan_speed",
            "hold_command_topic": self.house.config.mqtt_command_prefix + "/" + self.device_id + "/power_level",
            "swing_mode_command_topic": self.house.config.mqtt_command_prefix + "/" + self.device_id + "/timer",
            "hold_modes": ["1", "2", "3", "4", "5"],
            "modes": ["off", "heat"],
            "fan_modes": ["off", "1", "2", "3", "4", "5", "hi", "auto"],
            "device": {"identifiers": self.device_id, "manufacturer": "Palazzetti"}
        }
        self.topic_to_func = {
            self.climate_mqtt_config["mode_command_topic"]: self.send_mode,
            self.climate_mqtt_config["temperature_command_topic"]: self.send_target_temperature,
            self.climate_mqtt_config["fan_mode_command_topic"]: self.send_fan_speed,
            self.climate_mqtt_config["hold_command_topic"]: self.send_power_level,
            self.climate_mqtt_config["swing_mode_command_topic"]: self.send_timer,
        }
        self.status_sensor_discovery_topic = self.house.config.mqtt_discovery_prefix + "/sensor/" + self.device_id + "_status/config"
        self.status_sensor_mqtt_config = {
            "name": self.name + " (status)",
            "state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/status"
        }
        self.exit_temp_sensor_discovery_topic = self.house.config.mqtt_discovery_prefix + "/sensor/" + self.device_id + "_exit_temp/config"
        self.exit_temp_sensor_mqtt_config = {
            "name": self.name + " (exit temperature)",
            "device_class": "temperature",
            "unit_of_measurement": self.house.config.temperature_unit,
            "state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/exit_temp"
        }
        self.fumes_temp_sensor_discovery_topic = self.house.config.mqtt_discovery_prefix + "/sensor/" + self.device_id + "_fumes_temp/config"
        self.fumes_temp_sensor_mqtt_config = {
            "name": self.name + " (fumes temperature)",
            "device_class": "temperature",
            "unit_of_measurement": self.house.config.temperature_unit,
            "state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/fumes_temp"
        }
        self.pellet_qty_sensor_discovery_topic = self.house.config.mqtt_discovery_prefix + "/sensor/" + self.device_id + "_pellet_qty/config"
        self.pellet_qty_sensor_mqtt_config = {
            "name": self.name + " (pellet quantity)",
            "unit_of_measurement": self.house.config.pellet_quantity_unit,
            "state_topic": self.house.config.mqtt_state_prefix + "/" + self.device_id + "/pellet_qty"
        }

    def register_mqtt(self):
        mqtt_client = self.house.mqtt_client

        mqtt_client.subscribe(self.climate_mqtt_config["mode_command_topic"], 0)
        mqtt_client.subscribe(self.climate_mqtt_config["temperature_command_topic"], 0)
        mqtt_client.subscribe(self.climate_mqtt_config["fan_mode_command_topic"], 0)
        mqtt_client.subscribe(self.climate_mqtt_config["hold_command_topic"], 0)
        mqtt_client.subscribe(self.climate_mqtt_config["swing_mode_command_topic"], 0)

        if self.house.config.mqtt_discovery:
            retain = self.house.config.mqtt_config_retain
            mqtt_client.publish(self.climate_discovery_topic, json.dumps(self.climate_mqtt_config),
                                qos=1, retain=retain)
            mqtt_client.publish(self.status_sensor_discovery_topic, json.dumps(self.status_sensor_mqtt_config),
                                qos=1, retain=retain)
            mqtt_client.publish(self.exit_temp_sensor_discovery_topic, json.dumps(self.exit_temp_sensor_mqtt_config),
                                qos=1, retain=retain)
            mqtt_client.publish(self.fumes_temp_sensor_discovery_topic, json.dumps(self.fumes_temp_sensor_mqtt_config),
                                qos=1, retain=retain)
            mqtt_client.publish(self.pellet_qty_sensor_discovery_topic, json.dumps(self.pellet_qty_sensor_mqtt_config),
                                qos=1, retain=retain)

    def unregister_mqtt(self):
        mqtt_client = self.house.mqtt_client

        mqtt_client.unsubscribe(self.climate_mqtt_config["mode_command_topic"], 0)
        mqtt_client.unsubscribe(self.climate_mqtt_config["temperature_command_topic"], 0)
        mqtt_client.unsubscribe(self.climate_mqtt_config["fan_mode_command_topic"], 0)
        mqtt_client.unsubscribe(self.climate_mqtt_config["hold_command_topic"], 0)
        mqtt_client.unsubscribe(self.climate_mqtt_config["swing_mode_command_topic"], 0)

        if self.house.config.mqtt_discovery:
            retain = self.house.config.mqtt_config_retain
            mqtt_client.publish(self.climate_discovery_topic, None, qos=1, retain=retain)
            mqtt_client.publish(self.status_sensor_discovery_topic, None, qos=1, retain=retain)
            mqtt_client.publish(self.exit_temp_sensor_discovery_topic, None, qos=1, retain=retain)
            mqtt_client.publish(self.fumes_temp_sensor_discovery_topic, None, qos=1, retain=retain)
            mqtt_client.publish(self.pellet_qty_sensor_discovery_topic, None, qos=1, retain=retain)

    def on_message(self, topic, payload):
        func = self.topic_to_func.get(topic, None)
        if func is not None:
            func(payload)

    def send_mode(self, payload):
        self.house.palazzetti.set_power_state(self.hostname, payload == "heat")

    def send_target_temperature(self, target_temperature):
        if self.temp_step == 0.2:
            self.house.palazzetti.set_float_target_temperature(self.hostname, target_temperature)
        else:
            self.house.palazzetti.set_target_temperature(self.hostname, target_temperature)

    def send_fan_speed(self, fan_speed):
        self.house.palazzetti.set_fan_speed(self.hostname, self.fanspd_val.get(fan_speed,"0"))

    def send_power_level(self, power_level):
        self.house.palazzetti.set_power_level(self.hostname, power_level)

    def send_timer(self, timer_state):
        self.house.palazzetti.set_timer(self.hostname, timer_state)

    def publish_state(self):
        mqtt_client = self.house.mqtt_client
        if mqtt_client is not None:
            retain = self.house.config.mqtt_state_retain
            mqtt_client.publish(self.climate_mqtt_config["current_temperature_topic"],
                                self.room_temperature, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["mode_state_topic"],
                                self.mode, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["temperature_state_topic"],
                                self.target_temperature, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["temp_step"],
                                self.temp_step, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["fan_mode_state_topic"],
                                self.fan_speed, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["hold_state_topic"],
                                self.power_level, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["swing_mode_state_topic"],
                                self.timer_state, retain=retain)
            mqtt_client.publish(self.climate_mqtt_config["availability_topic"],
                                self.availability, retain=retain)
            mqtt_client.publish(self.status_sensor_mqtt_config["state_topic"],
                                self.status, retain=retain)
            mqtt_client.publish(self.exit_temp_sensor_mqtt_config["state_topic"],
                                self.exit_temperature, retain=retain)
            mqtt_client.publish(self.fumes_temp_sensor_mqtt_config["state_topic"],
                                self.fumes_temperature, retain=retain)
            mqtt_client.publish(self.pellet_qty_sensor_mqtt_config["state_topic"],
                                self.pellet_quantity, retain=retain)


################

class Config:
    devices = None
    api_user_agent = 'cbox'
    mqtt_discovery_prefix = "homeassistant"
    mqtt_state_prefix = "palazzetti/state"
    mqtt_command_prefix = "palazzetti/command"
    mqtt_reset_topic = "palazzetti/reset"
    mqtt_host = "127.0.0.1"
    mqtt_port = 1883
    mqtt_discovery = True
    mqtt_config_retain = True
    mqtt_state_retain = True
    mqtt_username = None
    mqtt_password = None
    mqtt_client_name = "cbox"
    logging_level = "INFO"
    refresh_delays = [3, 5, 10, 30]
    refresh_delay_randomness = 2
    offline_timeout = 120
    temperature_unit = "°C"
    temp_step = 1
    pellet_quantity_unit = "kg"

    def __init__(self, raw):
        self.devices = raw.get("devices")
        self.mqtt_discovery_prefix = raw.get("mqtt_discovery_prefix", self.mqtt_discovery_prefix)
        self.mqtt_state_prefix = raw.get("mqtt_state_prefix", self.mqtt_state_prefix)
        self.mqtt_command_prefix = raw.get("mqtt_command_prefix", self.mqtt_command_prefix)
        self.mqtt_reset_topic = raw.get("mqtt_reset_topic", self.mqtt_reset_topic)
        self.mqtt_host = raw.get("mqtt_host", self.mqtt_host)
        self.mqtt_port = raw.get("mqtt_port", self.mqtt_port)
        self.mqtt_discovery = raw.get("mqtt_discovery", self.mqtt_discovery)
        self.mqtt_config_retain = raw.get("mqtt_config_retain", self.mqtt_config_retain)
        self.mqtt_state_retain = raw.get("mqtt_state_retain", self.mqtt_state_retain)
        self.mqtt_username = raw.get("mqtt_username", self.mqtt_username)
        self.mqtt_password = raw.get("mqtt_password", self.mqtt_password)
        self.mqtt_client_name = raw.get("mqtt_client_name", self.mqtt_client_name)
        self.logging_level = raw.get("logging_level", self.logging_level)
        self.refresh_delays = raw.get("refresh_delays", self.refresh_delays)
        self.refresh_delay_randomness = raw.get("refresh_delay_randomness", self.refresh_delay_randomness)
        self.offline_timeout = raw.get("offline_timeout", self.offline_timeout)
        self.temperature_unit = raw.get("temperature_unit",self.temperature_unit)
        self.temp_step = raw.get("temp_step",self.temp_step)
        self.pellet_quantity_unit = raw.get("pellet_quantity_unit", self.pellet_quantity_unit)


################ 

class PalazzettiAdapter:
    last_successful_response = 0

    def __init__(self):
        self.delayer = Delayer([1], 2)
        self.session = requests.Session()

    def get_api(self, url, retry=1):
        logging.debug("API call: %s", url)
        try:
            response = self.session.get(url=url, data=None, headers=None, timeout=(2, 2))
        except Exception as e:
            logging.warning(e)
            response = None

        if response is None:
            status_code = -1
        else:
            status_code = response.status_code

        if status_code != 200:
            if retry > 0:
                logging.debug("API call failed with status code %s. Retrying.", status_code)
                time.sleep(self.delayer.next())
                return self.get_api(url, retry - 1)
            else:
                logging.debug("API call failed with status code %s. No more retry.", status_code)
                return {}
        else:
            logging.debug("API response: %s", response.text)
            self.last_successful_response = time.time()
            return json.loads(response.text)

    def send_command(self, hostname, command):
        return self.get_api("http://{}/cgi-bin/sendmsg.lua?cmd={}".format(hostname, command))

    def fetch_state(self, hostname):
        return self.send_command(hostname, "GET ALLS")

    def set_power_state(self, hostname, power_state):
        return self.send_command(hostname, "CMD {}".format(("ON", "OFF")[power_state]))

    def set_target_temperature(self, hostname, target_temperature):
        return self.send_command(hostname, "SET SETP {}".format(target_temperature))

    def set_float_target_temperature(self, hostname, target_temperature):
        return self.send_command(hostname, "SET STPF {}".format(target_temperature))

    def set_fan_speed(self, hostname, fan_speed):
        return self.send_command(hostname, "SET RFAN {}".format(fan_speed))

    def set_power_level(self, hostname, power_level):
        return self.send_command(hostname, "SET POWR {}".format(power_level))

    def set_timer(self, hostname, timer_state):
        timer_payload = "1" if timer_state == "on" else "0"
        return self.send_command(hostname, "SET CSST {}".format(timer_payload))

    def last_successful_response_age(self):
        return time.time() - self.last_successful_response

################

class Delayer:
    def __init__(self, delays, randomness):
        self.delays = delays
        self.delay_index = 0
        self.randomness = randomness

    def reset(self):
        self.delay_index = 0

    def next(self):
        delay = self.delays[self.delay_index] + self.randomness * (random.random() - .5)
        self.delay_index = min(len(self.delays) - 1, self.delay_index + 1)
        return delay


################

class House:
    def __init__(self):
        self.config = self.read_config()
        logging.basicConfig(level=self.config.logging_level, format="%(asctime)-15s %(levelname)-8s %(message)s")
        self.mqtt_client = mqtt.Client(self.config.mqtt_client_name)
        if self.config.mqtt_username is not None:
            self.mqtt_client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)
        self.mqtt_client.connect(self.config.mqtt_host, self.config.mqtt_port)
        self.devices = {}
        self.delayer = Delayer(self.config.refresh_delays, self.config.refresh_delay_randomness)
        self.palazzetti = PalazzettiAdapter()

    @staticmethod
    def read_config():
        with open("config/default.yml", 'r', encoding="utf-8") as yml_file:
            raw_default_config = yaml.safe_load(yml_file)

        try:
            with open("config/local.yml", 'r', encoding="utf-8") as yml_file:
                raw_local_config = yaml.safe_load(yml_file)
                raw_default_config.update(raw_local_config)
        except IOError:
            logging.info("No local config file found")

        return Config(raw_default_config)

    def register_all(self):
        self.mqtt_client.loop_start()
        self.mqtt_client.subscribe(self.config.mqtt_reset_topic, 0)
        for device_id, device in self.devices.items():
            device.register_mqtt()
        self.mqtt_client.on_message = self.on_message

    def unregister_all(self):
        self.mqtt_client.on_message(None)
        self.mqtt_client.unsubscribe(self.config.mqtt_reset_topic, 0)
        for device_id, device in self.devices.items():
            device.unregister_mqtt()
        self.mqtt_client.loop_stop()

    def update_all_states(self):
        logging.debug("update_all_states: begin")
        logging.debug("devices at beginning: %s", str(self.devices))
        for device_cfg in self.config.devices:
            logging.debug("update_all_states: %s begin", device_cfg["hostname"])
            raw_device = self.palazzetti.fetch_state(device_cfg["hostname"])
            logging.debug("update_all_states: raw_device %s", json.dumps(raw_device))
            try:
                device_id = raw_device["DATA"]["MAC"].replace(':', '_')
            except KeyError:
                logging.debug("Payload received: %s", json.dumps(raw_device))
                logging.error("Device response payload is missing a MAC identifier")
                return
            logging.debug("update_all_states: device_id %s", device_id)
            if device_id in self.devices:
                device = self.devices[device_id]
            else:
                device = Device(self, device_id,  device_cfg["name"], device_cfg["hostname"])
                self.devices[device.device_id] = device
            logging.debug("device before update: %s", str(device))
            device.update_state(raw_device["DATA"])
            logging.debug("device after update: %s", str(device))
        logging.debug("devices at end: %s", str(self.devices))
        logging.debug("update_all_states: end")

    def refresh_all(self):
        self.update_all_states()
        for device in self.devices.values():
            device.publish_state()

    def setup(self):
        self.update_all_states()
        for device in self.devices.values():
            device.update_mqtt_config()
            logging.info("Device found: %s (%s | %s)", device.name, device.device_id, device.hostname)

    def loop_start(self):
        self.setup()
        self.register_all()
        while True:
            self.refresh_all()
            time.sleep(self.delayer.next())

    def on_message(self, client, userdata, message):
        if message.topic == self.config.mqtt_reset_topic:
            self.setup()
            self.register_all()
            return

        topic_tokens = message.topic.split('/')
        # TODO validation

        device_id = topic_tokens[len(topic_tokens) - 2]
        command = topic_tokens[len(topic_tokens) - 1]
        value = str(message.payload.decode("utf-8"))
        logging.info("MQTT message received device '%s' command '%s' value '%s'", device_id, command, value)

        device = self.devices.get(device_id, None)
        if device is not None:
            device.on_message(message.topic, value)
        self.delayer.reset()


################

House().loop_start()
