import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
import uuid

import paho.mqtt.client as mqtt

from pirlib.interpreter import PirInterpreter
from pirlib.sampler import PirSampler


def str_to_bool(value: str) -> bool:
    value = value.strip().lower()
    if value in ("1", "true", "t", "yes", "y", "on"):
        return True
    if value in ("0", "false", "f", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError("expected boolean value (true/false)")


def create_run_id() -> str:
    '''generates a unique run ID using UUID4'''
    return str(uuid.uuid4())


def epoch_to_utc_iso(epoch_seconds: float) -> str:
    '''Convert epoch seconds to ISO 8601 UTC string with milliseconds precision.'''
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

## kollane ta paths me to : :
# def normalize_entity_id(value: str, default_prefix: str = "urn:dev:team-06:") -> str:

#     '''Normalize an entity ID by ensuring it starts with a URN prefix. 
#     If the value already starts with "urn:", it is returned unchanged. 
#     Otherwise, the default prefix is prepended to the value.'''

#     if value.startswith("urn:"):
#         return value
#     return f"{default_prefix}{value}"


def create_event(
    event_time: str,
    device_id: str,
    wastebin_id: str,
    environment_id: str,
    event_type: str,
    seq: int,
    run_id: str,
    motion_state: str,
    context_iri: str,
) -> dict:
    return {
        "@context": context_iri,
        "@type": "sosa:Observation",
        "event_time": event_time,
        "device_id": device_id,
        "wastebin_id": wastebin_id,
        "environment_id": environment_id,
        "event_type": event_type,
        "motion_state": motion_state,
        "seq": seq,
        "run_id": run_id,
    }
    # context_iri: Internationalized Resource Identifier // a unique string to identify the JSON-LD context that defines the semantics of the data
    # (unique identifier for the data schema, e.g. "https://example.com/context.jsonld")

    # motion_state: "detected" or "not_detected" or other string representing the state of motion

def parse_args() -> argparse.Namespace:

    ''' Parse command-line arguments using argparse and return the parsed arguments as a Namespace object.'''

    parser = argparse.ArgumentParser(description="PIR producer")

    parser.add_argument("--context", default="models/context.jsonld")
    parser.add_argument("--device-id", default="pir-motion-sensor-01")
    parser.add_argument("--wastebin-id", default="wastebin-01")
    parser.add_argument("--environment-id", default="environment-01")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="environments/environment-01/wastebins/wastebin-01/sensors/pir-01/events")
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--clean-session", type=str_to_bool, default=False)
    parser.add_argument("--pin", type=int)
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--simulate-prob", type=float, default=0.1)
    parser.add_argument("--seq-start", type=int, default=0)
    parser.add_argument("--sample-interval", type=float, default=0.1) # Time interval between sensor readings in seconds (default: 0.1s)
    parser.add_argument("--cooldown", type=float, default=5.0) # Cooldown period in seconds after motion is detected during which no new motion events will be generated (default: 5s)
    parser.add_argument("--min-high", type=float, default=0.0) # Minimum duration in seconds that the sensor signal must be high to consider it a valid motion event (default: 0s, i.e. any high signal is valid)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.simulate and args.pin is None:
        raise ValueError("--pin is required unless --simulate is enabled")
    if args.pin is not None and args.pin < 0:
        raise ValueError("--pin must be >= 0")
    if args.sample_interval <= 0:
        raise ValueError("--sample-interval must be > 0")
    if args.cooldown < 0:
        raise ValueError("--cooldown must be >= 0")
    if args.min_high < 0:
        raise ValueError("--min-high must be >= 0")
    if args.duration <= 0:
        raise ValueError("--duration must be > 0")
    if args.port <= 0 or args.port > 65535:
        raise ValueError("--port must be in range [1, 65535]")
    if args.simulate_prob < 0 or args.simulate_prob > 1:
        raise ValueError("--simulate-prob must be in range [0, 1]")
    if args.seq_start < 0:
        raise ValueError("--seq-start must be >= 0")


class SimulatedPirSampler:
    def __init__(self, probability: float = 0.1):
        self.probability = probability

    def read(self) -> bool:
        return random.random() < self.probability


class Producer:

    '''MQTT producer that reads from a PIR sensor, interprets the readings to detect motion events, 
    and publishes the events as JSON messages to an MQTT topic.'''

    @staticmethod
    def create_mqtt_client(client_id: str, clean_session: bool) -> mqtt.Client:
        if hasattr(mqtt, "CallbackAPIVersion"):
            return mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
                clean_session=clean_session,
            )
        return mqtt.Client(client_id=client_id, clean_session=clean_session)

    def __init__(self, args, metrics, sampler, interpreter, stop_flag):
        self.args = args
        self.metrics = metrics
        self.sampler = sampler
        self.interpreter = interpreter
        self.stop_flag = stop_flag
        self.run_id = create_run_id()
        self.seq = args.seq_start

        self.client = self.create_mqtt_client(client_id=self.args.client_id, clean_session=self.args.clean_session)


    def ha_pub_discovery(self, client, environment_id, wastebin_id, device_id):
        
        # Publish Home Assistant MQTT Discovery configuration for a binary sensor representing the motion state (detected/clear) of the PIR motion sensor.
        config = {
            "name": "Motion Sensor",
            "state_topic": f"pir_sensor/{device_id}/motion",
            "payload_on": "detected",
            "payload_off": "clear",
            "device_class": "motion",
            "unique_id": f"{device_id}_motion_sensor",

            "availability_topic": f"pir_sensor/{device_id}/availability",
            "payload_available": "online",
            "payload_not_available": "offline",

            "device": {
                "identifiers": [f"{environment_id}_{wastebin_id}_{device_id}"],
                "name": f"Device {device_id}",
                "model": "Motion Sensor",
                "manufacturer": "Team 06"
            }
        }

        payload = json.dumps(config)

        topic = f"homeassistant/binary_sensor/{device_id}/motion/config"

        client.publish(topic, payload, qos=1, retain=True)


        # Additionally, we can publish a sensor configuration for the wastebin status
        config = {
            "name": "Wastebin Status",
            "state_topic": f"smartbin/{wastebin_id}/status",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": f"smartbin/{wastebin_id}/status",
            "unique_id": f"wastebin_{wastebin_id}_status",

            "device": {
                "identifiers": [f"{environment_id}_{wastebin_id}"],
                "name": f"Smart Wastebin {wastebin_id}",
                "model": "Smart Wastebin v1",
                "manufacturer": "Team 06"
            }
        }

        payload = json.dumps(config)

        topic = f"homeassistant/sensor/{wastebin_id}_status/config"

        client.publish(topic, payload, qos=1, retain=True)

        # we can publish a sensor configuration for the activity level (active/inactive) based on the wastebin status 
        # output from node red
        client.publish(
            f"homeassistant/sensor/{wastebin_id}_activity_level/config",
            json.dumps({
                "name": "Activity Level",
                "state_topic": f"smartbin/{wastebin_id}/alerts",
                "value_template": "{{ value_json.activity_level }}",
                "json_attributes_topic": f"smartbin/{wastebin_id}/alerts",
                "unique_id": f"wastebin_{wastebin_id}_activity_level",
                "icon": "mdi:motion-sensor",

                "device": {
                    "identifiers": [f"{wastebin_id}"],
                    "name": f"Smart Wastebin {wastebin_id}",
                    "model": "Smart Wastebin v1",
                    "manufacturer": "Team 06"
                }
            }),
            retain=True
        )


    
    def produce(self):
        try:
            self.client.connect(self.args.broker, self.args.port, 60) # 60 is the keepalive interval in seconds
            self.client.loop_start()

            # Publish Home Assistant MQTT Discovery configuration for the PIR motion sensor and wastebin status sensor
            self.ha_pub_discovery(self.client, self.args.environment_id, self.args.wastebin_id, self.args.device_id)

            # Publish initial availability status for Home Assistant
            self.client.publish(f"pir_sensor/{self.args.device_id}/availability", "online", qos=1, retain=True)
            self.client.publish(f"pir_sensor/{self.args.device_id}/motion", "clear", qos=1, retain=True) # Initial state is "clear" (no motion)


            # Publish initial status for the wastebin 
            status_payload = {
                "state": "active",
                "location": "Kypes",
                "last_motion": None,
                "total_events_today": 0
            }

            # publish the initial status to the MQTT topic for the wastebin status sensor, using JSON format and retaining the message so that new subscribers get the latest status immediately
            self.client.publish(f"smartbin/{self.args.wastebin_id}/status", json.dumps(status_payload), qos=1, retain=True)


            start_t = time.time()

            while not self.stop_flag["stop"]:
                if self.args.duration > 0 and (time.time() - start_t) >= self.args.duration:
                    break

                try:
                    now = time.time()
                    raw = self.sampler.read()
                except Exception as exc:
                    print(f"[producer] sensor read error: {exc}", file=sys.stderr)
                    time.sleep(self.args.sample_interval)
                    continue

                for event in self.interpreter.update(raw, now):
                    event_time = epoch_to_utc_iso(event["t"])
                    if event.get("kind") == "motion_detected":
                        state = "detected"
                    else:
                        state = "clear"

                    # Publish the event count to a separate topic for Home Assistant integration
                    if event.get("kind") == "motion_detected":
                        self.seq += 1

                        self.client.publish(
                            f"smartbin/{self.args.wastebin_id}/motion_count",
                            str(self.seq),
                            retain=True
                        )
                    seq = self.seq

                    # Update the wastebin status with the latest motion event information
                    if event.get("kind") == "motion_detected":
                        status_payload = {
                            "state": "active",
                            "location": "Kypes",
                            "last_motion": event_time,
                            "total_events_today": self.seq
                        }

                        self.client.publish(
                            f"smartbin/{self.args.wastebin_id}/status",
                            json.dumps(status_payload),
                            retain=True
                        )
                    # send the dictionary as a JSON message to the MQTT topic
                    
                    record = create_event(
                        event_time=event_time,
                        device_id=self.args.device_id,
                        wastebin_id=self.args.wastebin_id,
                        environment_id=self.args.environment_id,
                        event_type="motion",
                        motion_state=state,
                        seq=seq,
                        run_id=self.run_id,
                        context_iri=self.args.context
                    )

                    payload = json.dumps(record) # Convert the event record dictionary to a JSON string for MQTT payload
                    result = self.client.publish(self.args.topic, payload, qos=self.args.qos)
                    
                    # # Publish simplified HA state (detected / clear)
                    ha_topic = f"pir_sensor/{self.args.device_id}/motion"

                    
                    if event.get("kind") == "motion_detected":
                        ha_state = "detected"
                    else:
                        ha_state = "clear"

                    self.client.publish(ha_topic, ha_state, qos=1, retain=True)
                    
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        self.metrics["produced"] += 1
                        if self.args.verbose:
                            print(
                                f"[producer] published seq={seq} topic={self.args.topic} "
                                f"state={record['motion_state']} event_time={event_time}",
                                flush=True,
                            )
                    else:
                        self.metrics["dropped"] += 1
                        if self.args.verbose:
                            print(
                                f"[producer] publish failed seq={seq} rc={result.rc}",
                                file=sys.stderr,
                                flush=True,
                            )

                time.sleep(self.args.sample_interval)
        finally:
            # Before disconnecting, publish an offline status for Home Assistant and the wastebin status sensor
            status_payload = {
                "state": "inactive",
                "location": "Kypes",
                "last_motion": None,
                "total_events_today": self.seq
            }

            self.client.publish(
                f"smartbin/{self.args.wastebin_id}/status",
                json.dumps(status_payload),
                qos=1,
                retain=True
            )

            self.client.publish(
                f"pir_sensor/{self.args.device_id}/availability",
                "offline",
                qos=1,
                retain=True
            )
            self.client.loop_stop()
            self.client.disconnect()



def main() -> int:
    try:
        args = parse_args()
        validate_args(args)
    except Exception as exc:
        print(f"[producer] argument error: {exc}", file=sys.stderr)
        return 2

    metrics = {"produced": 0, "consumed": 0, "dropped": 0}
    stop_flag = {"stop": False}

    try:
        if args.simulate:
            sampler = SimulatedPirSampler(args.simulate_prob)
        else:
            try:
                sampler = PirSampler(args.pin)
            except Exception as exc:
                print(f"[producer] sensor initialization error: {exc}", file=sys.stderr)
                return 1

        interp = PirInterpreter(cooldown_s=args.cooldown, min_high_s=args.min_high)
        producer = Producer(args=args, metrics=metrics, sampler=sampler, interpreter=interp, stop_flag=stop_flag)

        if args.verbose:
            print(
                f"[producer] broker={args.broker}:{args.port} topic={args.topic} qos={args.qos} "
                f"device={args.device_id} pin={args.pin if args.pin is not None else 'simulated'} interval={args.sample_interval}s "
                f"cooldown={args.cooldown}s min_high={args.min_high}s duration={args.duration}s seq_start={args.seq_start}",
                flush=True,
            )

        try:
            producer.produce()
        except KeyboardInterrupt:
            print("\n[producer] Ctrl-C: stopping...", flush=True)
            stop_flag["stop"] = True

    except Exception as exc:
        print(f"[producer] runtime error: {exc}", file=sys.stderr)
        return 1

    print(
        f"[producer] done. produced={metrics['produced']} dropped={metrics['dropped']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())