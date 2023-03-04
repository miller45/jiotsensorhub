import paho.mqtt.client as mqtt
import posixpath as path
import syslog
import json
from caseconverter import kebabcase
from datetime import datetime


def replace_all(text, dic):
    for i in dic:
        text = text.replace(i, dic[i])
    return text


class MQTTComm:
    sensState = {}
    lastContact = {}
    timeMS = 0
    connected = False
    online_count = 0

    def __init__(self, server_address, base_name, virtual_topic, hub_names, virtual_mac):
        self.server_address = server_address
        self.base_name = base_name
        self.virtual_topic = virtual_topic
        self.hub_names = hub_names
        self.virtual_mac = virtual_mac
        #  self.tele_topic = path.join("tele", virtual_topic)
        # self.tele_availtopic = path.join("tele/sonoff")  # needed to pass throught availbility of real devices
        self.shutter_names = hub_names

        self.tasmota_topic = "tasmota/discovery/{}".format(virtual_mac)
        self.client = mqtt.Client()
        self.connect()

    def connect(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.will_set(path.join(self.virtual_topic, "VHUB", "LWT"), payload="Offline", qos=0, retain=True)

        self.client.connect(self.server_address, 1883, 60)

        for tp in self.hub_names:
            subpath = path.join(self.base_name, tp, '#')
            print('subscribing to {}'.format(subpath))
            self.client.subscribe(subpath)

    def on_connect(self, client, userdata, flags, rc):
        # self.client.publish(path.join(self.tele_topic, "allshutters", "LWT"), payload="Online", qos=0, retain=True)
        self.slog("Connect with result code " + str(rc))
        self.client.publish(path.join(self.virtual_topic, "VHUB", "LWT"), payload="Online", qos=0, retain=True)
        self.publish_hass_state()

    def on_message(self, client, userdata, msg):
        parts = msg.topic.split("/")
        item = parts[-1]
        hub = parts[-2]
        # print(msg.topic)
        if item == 'LWT':
            payload = msg.payload.decode('utf-8')
            if payload == "Online":
                self.online_count += 1
            elif payload == "Offline":
                self.online_count -= 1
            print(payload)

        if item == 'SENSOR':
            payload = msg.payload.decode('utf-8')
            if len(payload) > 2:
                data = json.loads(payload)
                for key in data:
                    if key.startswith('ATC'):
                        name = key
                        self.lastContact[name] = datetime.now()
                        sensordata = data[name]
                        if name not in self.sensState:
                            self.sensState[name] = {}
                        for skey in sensordata:
                            if skey == "RSSI":
                                self.sensState[name]["{}_{}".format(skey, hub)] = sensordata[skey]
                            else:
                                self.sensState[name][skey] = sensordata[skey]

                        retopic = path.join(self.virtual_topic, name, 'SENSOR')
                        for hub in self.hub_names:
                            hkey = "RSSI_{}".format(hub)
                            if not hkey in self.sensState[name]:
                               self.sensState[name][hkey] = "0"
                        self.client.publish(retopic, json.dumps(self.sensState[name]))

        #  tele/sonoff/13DC54/SENSOR {"Time":"2022-10-28T12:09:22","ATC04b555":{"mac":"a4c13804b555","Temperature":25.1,"Humidity":57.6,"DewPoint":16.2,"Btn":1,"Battery":55,"RSSI":-49}}

    def slog(self, msg):
        syslog.syslog(msg)
        print(msg)

    def loop_forever(self):
        self.client.loop_forever()

    def publish_hass_state(self):
        hasst = path.join(self.virtual_topic, "VHUB", "HASS_STATE")
        htmpl = """{
  "Version": "$VERSION",
  "BuildDateTime": "2022-04-11T12:04:35",        
  "RSSI": "100"
}"""
        np = {
            '$VERSION': "1.1"
        }
        hastmplout = replace_all(htmpl, np)
        self.client.publish(hasst, hastmplout)

    def publish_hass_core_config(self, devicename):
        # homeassistant/sensor/13DC54_status/config =
        htmpl = """{"name":"BlueHub $DEVICE status","stat_t":"tele/sonoff/$DEVICE/HASS_STATE","avty_t":"tele/sonoff/$DEVICE/LWT","pl_avail":"Online","pl_not_avail":"Offline","json_attr_t":"tele/sonoff/$DEVICE/HASS_STATE","unit_of_meas":"%","val_tpl":"{{value_json['RSSI']}}","ic":"mdi:information-outline","uniq_id":"$DEVICE_status","dev":{"ids":["$DEVICE"],"name":"BlueHub$DEVICE","mdl":"Generic","sw":"10.0.0.4(tasmota)","mf":"Tasmota"}}"""
        # htmpl = """{"name":"VBlueHub status","stat_t":"$SHASST","avty_t":"$SLWT","pl_avail":"Online","pl_not_avail":"Offline","json_attr_t":"$SHASST","unit_of_meas":"%","val_tpl":"{{value_json['RSSI']}}","ic":"mdi:information-outline","uniq_id":"$DEVICE_status","dev":{"ids":["$DEVICE"],"name":"VBlueHub","mdl":"Generic","sw":"$VERSION(jiotsensorhub)","mf":"JIOT"}}"""
        hasst = path.join(self.virtual_topic, devicename, "HASS_STATE")
        np = {
            '$DEVICE': devicename,
            '$SLWT': path.join(self.virtual_topic, devicename, "LWT"),
            '$SHASST': hasst,
            '$VERSION': "1.1"
        }
        htmplout = replace_all(htmpl, np)
        self.client.publish("homeassistant/sensor/{}_status/config".format(devicename), htmplout, 0,
                            retain=True)
        stattmplout = replace_all("""{"Version":"$VERSION","RSSI":"100"}""", np)
        self.client.publish(hasst, stattmplout, 0,
                            retain=False)

    def publish_hass_sensor_config(self, devicename, sensorname):
        # homeassistant/sensor/13DC54_status/config =
        httmpl = """{"name":"BlueHub$DEVICE $SENSOR Temperature","stat_t":"tele/xiaomisensors/$SENSOR/SENSOR","avty_t":"tele/sonoff/$DEVICE/LWT","pl_avail":"Online","pl_not_avail":"Offline","uniq_id":"$DEVICE_$SENSOR_Temperature","dev":{"ids":["$DEVICE"]},"unit_of_meas":"°C","dev_cla":"temperature","frc_upd":true,"val_tpl":"{{value_json['Temperature']}}"}"""
        hdtmpl = """{"name":"BlueHub$DEVICE $SENSOR DewPoint","stat_t":"tele/xiaomisensors/$SENSOR/SENSOR","avty_t":"tele/sonoff/$DEVICE/LWT","pl_avail":"Online","pl_not_avail":"Offline","uniq_id":"$DEVICE_$SENSOR_DewPoint","dev":{"ids":["$DEVICE"]},"unit_of_meas":"°C","dev_cla":"temperature","frc_upd":true,"val_tpl":"{{value_json['DewPoint']}}"}"""
        hhtmpl = """{"name":"BlueHub$DEVICE $SENSOR Humidity","stat_t":"tele/xiaomisensors/$SENSOR/SENSOR","avty_t":"tele/sonoff/$DEVICE/LWT","pl_avail":"Online","pl_not_avail":"Offline","uniq_id":"$DEVICE_$SENSOR_Humidity","dev":{"ids":["$DEVICE"]},"unit_of_meas":"%","dev_cla":"humidity","frc_upd":true,"val_tpl":"{{value_json['Humidity']}}"}"""
        np = {
            '$DEVICE': devicename,
            '$SENSOR': sensorname
        }
        outht = replace_all(httmpl, np)
        outdt = replace_all(hdtmpl, np)
        outhh = replace_all(hhtmpl, np)
        self.client.publish("homeassistant/sensor/{}_{}_Temperature/config".format(devicename, sensorname), outht, 0,
                            retain=True)
        self.client.publish("homeassistant/sensor/{}_{}_DewPoint/config".format(devicename, sensorname), outdt, 0,
                            retain=True)
        self.client.publish("homeassistant/sensor/{}_{}_Humidity/config".format(devicename, sensorname), outhh, 0,
                            retain=True)

    # def publishhasssensors(self, data):
    #     stmpl = """{
    #        "sn": {
    #           "Time": "$DT",
    #           "ESP32": {
    #              "Temperature": 55.3
    #           },
    #           "TempUnit": "C"
    #        },
    #        "ver": 1
    #     }"""
    #     smtplout = replace_all(stmpl, np)
    #     self.client.publish("tasmota/discovery/{}/sensors".format(mac), smtplout, 0, retain=True)
    def publish_mqtt_config(self, mac, ip, name):

        np = {
            '$MAC6': mac[6:],
            '$MAC': mac,
            '$IP': ip,
            '$NAME': name,
            '$KBNAME': kebabcase(name),
            '$DT': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        tmpl = """{
   "ip": "$IP",
   "dn": "$NAME$MAC6",
   "fn": [
      "$NAME1",
      null,
      null,
      null,
      null,
      null,
      null,
      null
   ],
   "hn": "$KBNAME-$MAC6-0001",
   "mac": "$MAC",
   "md": "$NAME",
   "ty": 0,
   "if": 0,
   "ofln": "Offline",
   "onln": "Online",
   "state": [
      "OFF",
      "ON",
      "TOGGLE",
      "HOLD"
   ],
   "sw": "1.0.0.1",
   "t": "xiaomisensors/$MAC6",
   "ft": "%prefix%/%topic%/",
   "tp": [
      "cmnd",
      "stat",
      "tele"
   ],
   "rl": [
   ],
   "swc": [
   ],
   "swn": [
   ],
   "btn": [
   ],
   "so": {
      "4": 0,
      "11": 0,
      "13": 0,
      "17": 0,
      "20": 0,
      "30": 0,
      "68": 0,
      "73": 0,
      "82": 0,
      "114": 0,
      "117": 0
   },
   "lk": 0,
   "lt_st": 0,
   "sho": [     
   ],
   "ver": 1
}"""
        tmplout = replace_all(tmpl, np)
        self.client.publish("tasmota/discovery/{}/config".format(mac), tmplout, 0, retain=True)
