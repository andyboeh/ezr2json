# ezr2json - An Alpha2 to JSON bridge

This utility is a Python script that should be run in the background. It
connects to a number of given Möhlenhoff Alpha2 IP floor heating controllers
and bridges the XML output to JSON. So far, only reading the actual and target
temperatures as well as writing the target temperature is supported.

## Home-Assistant setup

In order to use this bridge with home-assistant, quite some configuration
is required. This example configuration adds exactly one room, represented in
the Alpha 2 system as one specific heat area. The names need to match!

configuration.yaml:
```
group: !include groups.yaml
automation: !include automations.yaml
sensor: !include sensors.yaml
input_number: !include input_numbers.yaml
rest_command: !include rest_commands.yaml
```

groups.yaml:
```
  ezr_eg_wz_group:
    name: EG Wohnzimmer
    entities:
      - sensor.ezr_eg_wz
      - input_number.ezr_eg_wz
```

automations.yaml:
```
  - alias: EG Wohnzimmer Solltemperatur
    trigger:
      platform: state
      entity_id: input_number.ezr_eg_wz
    action:
      - service: rest_command.ezr_set_target_command
        data_template:
          ezr: "EG"
          room: "Wohnzimmer"
          value: "{{ states('input_number.ezr_eg_wz') | float }}"
  - alias: EG Wohnzimmer Solltemperatur Refresh
    trigger:
      platform: state
      entity_id: sensor.hidden_ezr_state
    action:
      - service: input_number.set_value
        data_template:
          entity_id: input_number.ezr_eg_wz
          value: "{{ states('sensor.hidden_ezr_eg_wz_target') | float }}"
```

sensors.yaml:
```
  - platform: rest
    name: hidden_ezr_state
    resource: http://127.0.0.1:8008/
    force_update: true
    scan_interval: 30
    json_attributes:
      - EG
    value_template: 'OK'
  - platform: template
    sensors:
      ezr_eg_wz:
        friendly_name: "EG Wohnzimmer Temperatur"
        value_template: '{{ states.sensor.hidden_ezr_state.attributes["EG"]["Wohnzimmer"]["actual_temperature"] }}'
      hidden_ezr_eg_wz_target:
        value_template: '{{ states.sensor.hidden_ezr_state.attributes["EG"]["Wohnzimmer"]["target_temperature"] }}'
```

input_numbers.yaml:
```
  ezr_eg_wz:
    name: EG Wohnzimmer Solltemperatur
    min: 0
    max: 34
    step: 0.2
    mode: box
    icon: mdi:target
```

rest_commands.yaml:
```
  ezr_set_target_command:
    url: http://127.0.0.1:8008/set_target.json?ezr={{ ezr }}&room={{ room }}&target={{ value }}
    method: GET
```

The hosts to poll and their mapping to JSON values need to be defined in ezr_config.json. An example
file with three Alpha 2 devices ("EG", "OG1" and "OG2") is provided in the repository.

## Representation in Home Assistant

With this setup you get a temperature sensor and an input box, whereas the sensor
represents the actual temperature and the input box the target temperature. If
the target temperature is changed on the system outside of HA, the change
is reflected shortly afterwards in HA. Syncing a change in HA to the system might take 
some seconds, the Alpha 2 needs some minutes to sync the settings to the room controllers.
