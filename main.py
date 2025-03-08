# -*- coding: utf-8 -*-
import configparser
import mqttcom
import syslog
import time
import datetime


print("Starting MQTT Sensor Hub")

hpConfig = configparser.ConfigParser()
hpConfig.read("config.ini")


def slog(msg):
    syslog.syslog(msg)
    print(msg)

all_hubnames = hpConfig['mqtt']['bluehub_names'].split(",")
VERSION = "1.2.1"
mqttClient = mqttcom.MQTTComm(hpConfig["mqtt"]["server_address"], VERSION,
                              base_name=hpConfig["mqtt"]["base_name"],
                              virtual_topic=hpConfig["mqtt"]["virtual_topic"],
                              hub_names=all_hubnames, virtual_mac=hpConfig["mqtt"]["virtual_mac"],
                              auto_connect=False
                              )
mqttClient.configure_waterstats(hpConfig["watermqtt"]["waterpulse_topic"],hpConfig["watermqtt"]["waterliter_topic"])
onon = True
mode = 0 # do not touch:needs only be changed once for device setup e.g. whole homeassistant erased
REALHUB = "13DC54"
FAKEHUB = "VHUB"


main_exception_counter=0
last_main_exception_counter=0

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

#        if main_exception_counter > last_main_exception_counter:
#            last_main_exception_counter = main_exception_counter


        mqttClient.loop_forever()

    except BaseException as error:
        slog('An exception occurred during onon')  #: {}'.format(error))
        slog('{}: {}'.format(type(error).__name__, error))
        mqttClient.last_main_exception_localtime=datetime.datetime.now().isoformat()
        mqttClient.last_main_exception = '{}: {}'.format(type(error).__name__, error)
        main_exception_counter+=1
        if type(error) == KeyboardInterrupt:
            exit(0)
        slog("restarting after 5 secs")
        time.sleep(5)
