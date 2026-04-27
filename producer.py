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


def normalize_entity_id(value: str, default_prefix: str = "urn:dev:team-06:") -> str:

    '''Normalize an entity ID by ensuring it starts with a URN prefix. 
    If the value already starts with "urn:", it is returned unchanged. 
    Otherwise, the default prefix is prepended to the value.'''

    if value.startswith("urn:"):
        return value
    return f"{default_prefix}{value}"


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
        "device_id": normalize_entity_id(device_id),
        "wastebin_id": normalize_entity_id(wastebin_id),
        "environment_id": normalize_entity_id(environment_id),
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

    def produce(self):
        try:
            self.client.connect(self.args.broker, self.args.port, 60) # 60 is the keepalive interval in seconds
            self.client.loop_start()

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
                    seq = self.seq
                    self.seq += 1
                    event_time = epoch_to_utc_iso(event["t"])
                    state = "detected" if event.get("kind") == "motion_detected" else str(event.get("kind", "unknown"))

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