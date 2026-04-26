# Advanced Programming Techniques Lab
## Team Information
Members: 
- Marios Ioannis Papadopoulos 1092834  
- Filippos Neofytos Theologos 1092633  
- Xristina Tzouda 1097346

---
# SECTION A - RUNBOOK 
## Nesessary hardware and software from previous labs
- Hardware:
  - Raspberry Pi 5
  - HC-SR501 PIR motion sensor
  - Jumper wires(female to female)
- Wiring the sensor:
  Use the example given on lab02, made sure to connect the OUT on the same pin.
- Connection
  As shown in lab01, in order to run the following code it's nesessary to connect to the raspberry pi 5 via ssh. Clear instructions can be found on lab01.
- Software:
  - The PIR sensor logic (`sampler.py`, `interpreter.py`) is reused from Lab 02 and placed inside `pirlib/`. 
  - Use a venv just like lab01 and lab02.
  - Make sure to inastall a `requirments.txt`.
## Part 1 — Install and start Mosquitto
On the laptop connected to the rpi run:
```
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients
```
After installing Mosquito run this command in order to make sure it works :
```
systemctl status mosquitto
```
This should give *Active : Active (running)* as a result.
## Part 2 — Explore MQTT from the terminal
1. Open 2 terminals (both connected to the rpi):
  1. Start a subscriber :
 ```
 mosquitto_sub -h localhost -t "test/hello"
```
  3. In the second terminal publish th following message :
```
mosquitto_pub -h localhost -t "test/hello" -m "world"
```
Correct output: "world" appears on the subscriber's terminal.
## Topic hierarchy :
   1. On the subscriber's terminal write :
```
mosquitto_sub -h localhost -t "smartbin/pir-01/motion"
```
  2. On the publisher's terminal type:
```
mosquitto_pub -h localhost -t "smartbin/pir-01/motion" -m '{"state": "detected"}'
```
By this, it is clear that  MQTT does not care about the format, it just delivers bytes.

## Wildcards: 
With the subscriber still running, try these in separate terminals. On the first:
```
# Subscribe to ALL topics under smartbin/pir-01/
mosquitto_sub -h localhost -t "smartbin/pir-01/#"
```
On the second :
```
# Subscribe to motion events from ANY device
mosquitto_sub -h localhost -t "smartbin/+/motion"
```
In another terminal, publish to different topics and see which subscribers receive what:
```
mosquitto_pub -h localhost -t "smartbin/pir-01/motion" -m "detected"
mosquitto_pub -h localhost -t "smartbin/pir-01/status" -m "online"
mosquitto_pub -h localhost -t "smartbin/pir-02/motion" -m "detected"
mosquitto_pub -h localhost -t "smartbin/ultrasonic-01/fill" -m "72"
```
## QoS levels
- Publish different Quality of Service levels :
```
# QoS 0: at most once (fire and forget)
mosquitto_pub -h localhost -t "test/qos" -m "qos0 message" -q 0

# QoS 1: at least once (acknowledged)
mosquitto_pub -h localhost -t "test/qos" -m "qos1 message" -q 1

# QoS 2: exactly once (four-step handshake)
mosquitto_pub -h localhost -t "test/qos" -m "qos2 message" -q 2
```
With a subscriber listening on test/qos, all three should arrive. 
By testing these we decided to use QoS 1 for our project.
## Retained messages
1. Publish a retained message :
```
mosquitto_pub -h localhost -t "smartbin/pir-01/status" -m "online" -r
```
2. Start a new subscriber after the publish:
```
mosquitto_sub -h localhost -t "smartbin/pir-01/status"
```
The subscriber immediately receives themessage when it is online even though it was published before it connected. 
## Part 3 — Split the pipeline into publisher and subscriber
# Install the Python MQTT library
- Add paho-mqtt to the `requirments.txt`.
- Then install it by running:
```
pip install paho-mqtt
```
# Topic stracture 
The topic stracture we used is :
```
environments/environment-01/wastebins/wastebin-01/sensors/pir-01/events
```

# Run the `producer.py` and `consumer.py`
- Using the pseudocode given, we wrote the necessary code.
- Connect to the rpi using the instructions given on lab01 and made sure we have enabled the `venv`.
- On one terminal, run the consumer:
```
python consumer.py --broker localhost --topic "smartbin/bin-01/pir-01/events" --out events.jsonl --verbose
```
- On another terminal run the producer:
```
python producer.py --broker localhost --topic smartbin/bin-01/pir-01/events --pin 17 --verbose
```
- Output example, both consumer and producer are online:
```
[producer] broker=localhost:1883 topic=smartbin/bin-01/pir-01/events qos=0 device=pir-motion-sensor-01 pin=17 interval=0.1s cooldown=5.0s min_high=0.0s duration=60.0s
[producer] published seq=1 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:24:56.982Z
[producer] published seq=2 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:03.887Z
[producer] published seq=3 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:11.192Z
[producer] published seq=4 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:16.195Z
[producer] published seq=5 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:21.200Z
[producer] published seq=6 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:28.705Z
[producer] published seq=7 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:36.110Z
[producer] published seq=8 topic=smartbin/bin-01/pir-01/events state=detected event_time=2026-04-26T09:25:50.519Z
[producer] done. produced=8 dropped=0
```
- Event logger(JSONL)
```
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:22.096Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 4, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:27.800Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 5, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:35.005Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 6, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:42.010Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 7, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:47.014Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 8, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
```
- Output example, producer online - consumer offline
![alt text](con_off.png)
![alt text](con_off_1.png)

- Output example : Run the consumer with a wildcard topic




# Part 4 — Containerize with Docker Compose 
Like it was shown in lab04

---
# SECTION B - REPORT
## RQ1
The broker is a middleman that receives published messages and forwards them to subscribers. Without it, the producer would need to know the consumer's address, both would need to run simultaneously, and adding a second consumer would require changing the producer. The broker removes all these dependencies.
## RQ2
`smartbin/<bin-id>/<sensor-id>/events`. The hierarchy goes location → device → type, enabling wildcards like `smartbin/bin-01/#` which gives us all data from one bin or `smartbin/+/pir-01/events`which means pir-01 across all bins, new sensors and bins can be added without changing existing subscribers.
## RQ3
- QoS 0: At most once. The broker delivers the message once with no acknowledgement. Messages can be lost if the network drops.
- QoS 1: At least once. The broker acknowledges receipt of the message. If the acknowledgment is lost, the message is retransmitted, which may result in duplicate messages, but delivery is guaranteed at least once.
- QoS 2 : Exactly once. A four-step handshake ensures that the message is delivered exactly once, without duplicates. It is the safest level but also the slowest due to the additional overhead.

We used QoS 1 for motion events because it guarantees delivery while keeping latency and overhead low. Although duplicates may occur, they can be handled by the application, making it a good balance between reliability and performance.
## RQ4
A retained message is stored by the broker and delivered immediately to any new online subscriber. In our project it can be used so that the user knows the remaining capacity of the bin. Even though the subscriber might be offline the message won't be lost.  
## RQ5
`smartbin/+/motion` received messages on `smartbin/pir-01/motion` and `smartbin/pir-02/motion`, but not `smartbin/pir-01/status` or `smartbin/ultrasonic-01/fill`. The `+` wildcard matches exactly one level, so only topics with that exact three-level structure and motion at the end matched.
## RQ6
`#` received everything flowing through the broker. It's useful for debugging because you see all traffic without knowing topic names.
## RQ7
No. Without the retain flag, the broker discards messages if no subscriber is currently connected. MQTT doesn't queue messages for future subscribers by default.
## RQ8
In the threaded version, producer and consumer share a Python Queue in the same process and must start/stop together. In the MQTT version they are separate processes communicating through the broker, can run independently, on different machines, and multiple consumers are supported with no code changes.
## RQ9
In the threaded version, a full queue blocked or dropped messages directly in the producer. In the MQTT version, the producer is unaffected, it publishes to the broker regardless.  If the consumer is offline , with QoS 1,  by default all messages will be lost.
## RQ10
Polling `queue.get(timeout=0.5)` has the consumer doing loops every 0.5 seconds, whether there was motion detectd or not. The callback pattern (on_message) is passive which means the consumer registers a function and paho-mqtt calls it automatically when a message arrives. 
## RQ11
```
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:22.096Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 4, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:27.800Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 5, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:35.005Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 6, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:42.010Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 7, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
{"@context": "models/context.jsonld", "@type": "sosa:Observation", "event_time": "2026-04-25T17:21:47.014Z", "device_id": "urn:dev:team-06:pir-motion-sensor-01", "wastebin_id": "urn:dev:team-06:wastebin-01", "environment_id": "urn:dev:team-06:environment-01", "event_type": "motion", "motion_state": "detected", "seq": 8, "run_id": "44135bee-992c-4341-b8ea-72227b912cf2"}
```
The JSON structure is identical to previous labs.
## RQ12
With a persistent session (clean_session=False) and QoS 1, the broker queues the messages and delivers the time the consumer reconnects.
## RQ13
Yes, both received every message because the broker fans out to all matching subscribers. This matters because you can add consumer independently without modifying the producer or any other consumer.
## RQ14
Yes. You'd need to make some changes so that the Mosquitto can connect to all interfaces not just localhost, and point the consumer's `--broker` argument to the rpi's IP address.
## RQ15
Decoupling means producer and consumer share no direct connection only a topic name and message format.
## RQ16
If the broker crashes, the pipeline stops entirely and in-flight messages are lost.

