import paho.mqtt.client as mqtt
import configparser
import mqttcom
import syslog
import time

print("Starting MQTT Sensor Hub")

hpConfig = configparser.ConfigParser()
hpConfig.read("config.ini")


def slog(msg):
    syslog.syslog(msg)
    print(msg)


# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.

hubnames = hpConfig['mqtt']['bluehub_names'].split(",")

mqttClient = mqttcom.MQTTComm(hpConfig["mqtt"]["server_address"], hpConfig["mqtt"]["base_name"],
                              hpConfig["mqtt"]["virtual_topic"], hubnames, "00000000003C")
onon = True
mode = 0
REALHUB = "13DC54"
FAKEHUB = "VHUB"

VERSION = "1.1"

while onon:
    try:

        if mode == 2:
            ## mqttClient.publishconfig("00000000003C","192.168.0.137","VBlueHub")
            sss = ['ATC804c32', 'ATC2a6068', 'ATC4a759d', 'ATC9bb245','ATC6b0f29']
            ##sss = ['ATC04b555']
            for s in sss:
                mqttClient.publish_hass_sensor_config(REALHUB, s)

        elif mode == 1:
            mqttClient.publish_hass_core_config(REALHUB)

        mqttClient.loop_forever()

    except BaseException as error:
        slog('An exception occurred during onon')  #: {}'.format(error))
        slog('{}: {}'.format(type(error).__name__, error))
        if type(error) == KeyboardInterrupt:
            exit(0)
        slog("restarting after 5 secs")
        time.sleep(5)
