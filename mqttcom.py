import paho.mqtt.client as mqtt
import posixpath as path
import syslog
import json

print(mqtt.__name__)


class MQTTComm:
    swState = {}
    last_dir = {}  # last direction of shutters
    stateCounter = 0
    timeMS = 0
    connected = False
    eintraege = []

    def __init__(self, server_address, base_name, virtual_topic, hub_names):
        self.server_address = server_address
        self.base_name = base_name
        self.virtual_topic = virtual_topic
        self.hubtopics = hub_names
        self.roller_topic = path.join("cmnd", virtual_topic)
        self.result_topic = path.join("stat", virtual_topic)
        self.tele_topic = path.join("tele", virtual_topic)
        self.tele_availtopic = path.join("tele/sonoff")  # needed to pass throught availbility of real devices
        self.shutter_names = hub_names
        self.slog("roller topic: {}".format(self.roller_topic))

        self.client = mqtt.Client()
        self.connect()

    def connect(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        #        self.client.will_set(path.join(self.tele_topic, "allshutters", "LWT"), payload="Offline", qos=0, retain=True)

        self.client.connect(self.server_address, 1883, 60)

        for tp in self.hubtopics:
            subpath = path.join(self.base_name, tp, '#')
            print('subscribing to {}'.format(subpath))
            self.client.subscribe(subpath)

    def on_connect(self, client, userdata, flags, rc):
        # self.client.publish(path.join(self.tele_topic, "allshutters", "LWT"), payload="Online", qos=0, retain=True)
        self.slog("Connect with result code " + str(rc))

    def on_message(self, client, userdata, msg):
        parts = msg.topic.split("/")
        item = parts[-1]

        print (msg.topic)
        if item == 'SENSOR':
            payload = str(msg.payload)
            if len(payload) > 2:
                data = json.loads(payload)
                for key in data:
                    if key.startswith('ATC'):
                        name = key
                        sensordata = data[key]
                        retopic = path.join(self.virtual_topic, name, 'SENSOR')
                        self.client.publish(retopic, json.dumps(sensordata))
             #           print('republish on {}'.format(json.dumps(retopic)))
        #  tele/sonoff/13DC54/SENSOR {"Time":"2022-10-28T12:09:22","ATC04b555":{"mac":"a4c13804b555","Temperature":25.1,"Humidity":57.6,"DewPoint":16.2,"Btn":1,"Battery":55,"RSSI":-49}}

    def on_messageoff(self, client, userdata, msg):
        # (head, tail) = path.split(msg.topic)
        parts = msg.topic.split("/")
        item = parts[-1]
        is_hass = False
        if item == "set":  # detect home assistant
            is_hass = True
            item = parts[-2]  # the name is before the set
        payload = str(msg.payload)

        # home assitant handling
        if is_hass:
            if payload:
                if payload == "OPEN":
                    self.swState[item] = "BLINDSUP"
                    self.send_to_real(item, "POWER1", "ON")
                    self.send_to_real(item, "POWER2", "OFF")
                    self.slog("home assissent open (UP)")
                    self.client.publish(path.join(self.result_topic, item, "operation"), payload="opening", qos=0,
                                        retain=False)
                    self.client.publish(path.join(self.result_topic, item, "position"), payload="33", qos=0,
                                        retain=False)
                elif payload == "CLOSE":
                    self.swState[item] = "BLINDSDOWN"
                    self.send_to_real(item, "POWER1", "OFF")
                    self.send_to_real(item, "POWER2", "ON")
                    self.slog("home assissant close (DOWN)")
                    self.client.publish(path.join(self.result_topic, item, "operation"), payload="closing", qos=0,
                                        retain=False)
                    self.client.publish(path.join(self.result_topic, item, "position"), payload="66", qos=0,
                                        retain=False)
                elif payload == "STOP":
                    self.slog("home assissant stop")
                    self.send_to_real(item, "POWER1", "ON")
                    self.send_to_real(item, "POWER2", "ON")
                    self.swState[item] = "BLINDSSTOP2"
                    self.enqueue_next_event(self.timeMS + 100, "POWER1:OFF", item)
                    self.enqueue_next_event(self.timeMS + 100, "POWER2:OFF", item)
                    finstate = "stopped"
                    # Last direction is hint to final state
                    self.client.publish(path.join(self.result_topic, item, "operation"), payload=finstate, qos=0,
                                        retain=False)
                    # that  is is only for keeping homeassistant happy.  We do not really no were the shutters are

        # openhab handling
        elif payload and payload.startswith("BLINDS"):
            laststate = self.swState.get(item, "")
            if msg.payload == "BLINDSUP":
                self.swState[item] = "BLINDSUP"
                self.send_to_real(item, "POWER1", "ON")
                self.send_to_real(item, "POWER2", "OFF")
                self.slog("Getting Up")
            elif msg.payload == "BLINDSDOWN":
                self.swState[item] = "BLINDSDOWN"
                self.send_to_real(item, "POWER1", "OFF")
                self.send_to_real(item, "POWER2", "ON")
                self.slog("Getting DOWN")
            elif msg.payload == "BLINDSSTOP":
                self.slog("Getting STOP")
                if laststate == "BLINDSSTOP":
                    self.send_to_real(item, "POWER1", "ON")
                    self.send_to_real(item, "POWER2", "ON")
                    self.enqueue_next_event(self.timeMS + 100, "POWER1:OFF", item)
                    self.enqueue_next_event(self.timeMS + 100, "POWER2:OFF", item)
                    self.swState[item] = "BLINDSSTOP2"
                else:
                    self.swState[item] = "BLINDSSTOP"

        self.stateCounter = self.stateCounter + 1
        # if(msg.topic.ends)

        self.slog(msg.topic + " " + str(msg.payload))

    def send_to_real(self, item_name, switch_name, value):
        pass
        #  self.client.publish(path.join(self.actuator_topic, item_name, switch_name), value)

    def send_tele(self, stamp, connected):
        msg = "CONNECTED {}" if connected else "NOT CONNECTED {}"
        self.client.publish(path.join(self.tele_topic, 'STATE'), msg.format(stamp))

    def slog(self, msg):
        syslog.syslog(msg)
        print(msg)

    def loop_forever(self):
        self.client.loop_forever()
