import json
import time
import argparse
from datetime import datetime, timedelta, timezone
from collections import deque
from threading import Lock

import paho.mqtt.client as mqtt


# Queue to store event timestamps
event_times = deque()

# Lock for thread safety
event_lock = Lock()


def on_message(client, userdata, message):
    try:
        # Decode MQTT payload
        payload_text = message.payload.decode("utf-8").strip()

        # Parse JSON payload
        data = json.loads(payload_text)

        """
        Expected payload example:
        {
            "motion_state": "detected"
        }

        If your sender publishes plain text instead:
        detected

        then use:
            if payload_text == "detected":
        """

        if data["motion_state"] == "detected":
            with event_lock:
                event_times.append(datetime.now(timezone.utc))

    except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
        # Ignore invalid messages
        pass


def evaluate_usage(window_minutes=10):
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    with event_lock:
        # Remove old events
        while (
            len(event_times) > 0
            and event_times[0] < cutoff_time
        ):
            event_times.popleft()

        count = len(event_times)

    # Usage classification
    if count == 0:
        return "idle", count

    elif count <= 5:
        return "low", count

    elif count <= 10:
        return "medium", count

    else:
        return "high", count

def publish_ha_discovery(client):
    config_payload = {
        "name": "Wastebin Usage Level",
        "state_topic": "virtual_smartbin/bin-01/usage",
        "value_template": "{{ value_json.usageLevel }}",
        "json_attributes_topic": "virtual_smartbin/bin-01/usage",
        "unique_id": "wastebin_01_usage_level",
        "icon": "mdi:chart-bar",

        "availability_topic": "virtual_smartbin/bin-01/usage/status",
        "payload_available": "online",
        "payload_not_available": "offline",

        "device": {
            "identifiers": ["bin-01"],
            "name": "Smart Wastebin 01",
            "model": "Virtual Sensor",
            "manufacturer": "Team 06"
        }
    }

    client.publish(
        "homeassistant/sensor/virtual_smartbin_bin-01_usage/config",
        json.dumps(config_payload),
        qos=1,
        retain=True
    )


def main():
    parser = argparse.ArgumentParser(
        description="Virtual sensor rules engine"
    )

    parser.add_argument(
        "--broker",
        default="localhost",
        help="MQTT broker address"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port"
    )

    parser.add_argument(
        "--subscribe-topic",
        default="environments/+/wastebins/wastebin-01/sensors/pir-01/#",
        help="MQTT topic to subscribe to"
    )

    parser.add_argument(
        "--publish-topic",
        default="virtual_smartbin/bin-01/usage",
        help="MQTT topic to publish usage results"
    )

    parser.add_argument(
        "--window",
        type=int,
        default=10,
        help="Usage evaluation window in minutes"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Time between evaluations in seconds"
    )

    args = parser.parse_args()

    # Create MQTT client
    client = mqtt.Client(client_id="virtual-sensor-rules")

    # Register callback
    client.on_message = on_message

    # Connect to broker
    client.connect(args.broker, args.port)

    # Subscribe to sensor events
    client.subscribe(args.subscribe_topic, qos=1)

    # Start background MQTT loop
    client.loop_start()

    # Publish Home Assistant discovery config
    publish_ha_discovery(client)


    # Publish initial availability status
    client.publish(
        "virtual_smartbin/bin-01/usage/status",
        "online",
        qos=1,
        retain=True
    )

    print("========================================")
    print("Virtual Sensor Rules Engine Started")
    print(f"Subscribed topic : {args.subscribe_topic}")
    print(f"Publish topic    : {args.publish_topic}")
    print(f"Window size      : {args.window} minutes")
    print(f"Eval interval    : {args.interval} seconds")
    print("========================================")

    try:
        while True:
            usage_level, count = evaluate_usage(args.window)

            payload = {
                "usageLevel": usage_level,
                "eventCount": count,
                "windowMinutes": args.window,
                "evaluatedAt": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            client.publish(
                args.publish_topic,
                json.dumps(payload),
                qos=1,
                retain=True
            )

            print(
                f"[{datetime.now().isoformat()}] "
                f"Usage={usage_level} | Events={count}"
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopping virtual sensor...")

    finally:
        # Publish offline status
        client.publish(
            "virtual_smartbin/bin-01/usage/status",
            "offline",
            qos=1,
            retain=True
        )

        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()