# jiotsensorhub
family project: republish mqtt messages from xiaomi temp/humidity sensors from tasmota in a way to consume easier

e.g.
tele/sonoff/13DC54/SENSOR with payload
{
"Time":"2022-10-28T13:44:23","ATC04b555":{"mac":"a4c13804b555","Temperature":25.1,"Humidity":56.3,"DewPoint":15.8,"Btn":
1,"Battery":54,"RSSI":-43}
}
turns into 
tele/sonoff/ATC04b555/SENSOR with payload 
{"mac":"a4c13804b555","Temperature":25.1,"Humidity":56.3,"DewPoint":15.8,"Btn":
1,"Battery":54,"RSSI":-43}

so it can be consumed in homeassistant with:

```
  - platform: mqtt name: "BathTemp2"
    state_topic: "tele/xiaomisensors/ATC04b555/SENSOR" 
    unit_of_measurement: '°C' value_template: "{{ value_json.Temperature }}" 
    device_class: temperature
```