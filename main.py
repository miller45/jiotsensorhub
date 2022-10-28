import paho.mqtt.client as mqtt
import configparser
import mqttcom
import syslog
import time

print("Starting MQTT Sensor Hub")

hpConfig = configparser.ConfigParser()
hpConfig.read("config.ini")


def slog(msg):

   # syslog.syslog(msg)
    print(msg)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.

hubnames = hpConfig['mqtt']['bluehub_names'].split(",")

mqttClient = mqttcom.MQTTComm(hpConfig["mqtt"]["server_address"], hpConfig["mqtt"]["base_name"],
                              hpConfig["mqtt"]["virtual_topic"],  hubnames)
onon=True

while onon:
    try:
        mqttClient.loop_forever()

    except BaseException as error:
        slog('An exception occurred during onon')  #: {}'.format(error))
        slog('{}: {}'.format(type(error).__name__, error))
        if type(error) == KeyboardInterrupt:
            exit(0)
        slog("restarting after 5 secs")
        time.sleep(5)