import paho.mqtt.client as mqtt
import json
import time
import argparse
import joblib
import numpy as np
import pandas as pd

from datetime import datetime, timezone


def load_model(path):
    """
    Load trained ML model from disk.
    """
    return joblib.load(path)


def predict_next_hour(model):

    now = datetime.now()

    # Predict next hour
    next_hour = (now.hour + 1) % 24

    # Monday = 0, Sunday = 6
    day_of_week = now.weekday()

    # Weekend flag
    is_weekend = 1 if day_of_week in [5, 6] else 0

    # Feature vector
    features = pd.DataFrame([
        {
            "day_of_week": day_of_week,
            "hour": next_hour,
            "is_weekend": is_weekend
        }
    ])

    # Prediction
    prediction = model.predict(features)[0]

    # Prediction probabilities
    probabilities = model.predict_proba(features)[0]

    # Probability for predicted class
    class_index = list(model.classes_).index(prediction)

    confidence = probabilities[class_index]

    return (
        prediction,
        confidence,
        next_hour,
        day_of_week,
        is_weekend
    )


def publish_ha_discovery(client):

    config_payload = {
        "name": "Wastebin Busy Prediction",

        "state_topic": "smartbin/bin-01/prediction",

        "value_template": "{{ value_json.prediction }}",

        "json_attributes_topic": "smartbin/bin-01/prediction",

        "unique_id": "wastebin_01_busy_prediction",

        "icon": "mdi:brain",

        "availability_topic": "smartbin/bin-01/prediction/status",

        "payload_available": "online",

        "payload_not_available": "offline",

        "device": {
            "identifiers": ["bin-01"],
            "name": "Smart Wastebin 01",
            "model": "ML Virtual Sensor",
            "manufacturer": "Team 06"
        }
    }

    client.publish(
        "homeassistant/sensor/wastebin_01_prediction/config",
        json.dumps(config_payload),
        qos=1,
        retain=True
    )


def main():

    parser = argparse.ArgumentParser(
        description="ML Virtual Sensor"
    )

    parser.add_argument(
        "--broker",
        default="localhost",
        help="MQTT broker hostname"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port"
    )

    parser.add_argument(
        "--publish-topic",
        default="smartbin/bin-01/prediction",
        help="MQTT prediction topic"
    )

    parser.add_argument(
        "--model-path",
        default="models/busy_predictor.joblib",
        help="Path to trained ML model"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Prediction interval in seconds"
    )

    parser.add_argument(
        "--bin-id",
        default="bin-01",
        help="Smart bin identifier"
    )

    args = parser.parse_args()

    # Load ML model
    model = load_model(args.model_path)

    print(f"Loaded model from: {args.model_path}")

    # Create MQTT client
    client = mqtt.Client(
        client_id="virtual-sensor-ml"
    )

    # Connect to broker
    client.connect(
        args.broker,
        args.port
    )

    # Start MQTT loop
    client.loop_start()

    # Publish HA discovery config
    publish_ha_discovery(client)

    # Publish availability status
    client.publish(
        "smartbin/bin-01/prediction/status",
        "online",
        qos=1,
        retain=True
    )

    print("========================================")
    print("ML Virtual Sensor Started")
    print(f"Publish topic : {args.publish_topic}")
    print(f"Interval      : {args.interval} seconds")
    print("========================================")

    try:

        while True:

            (
                prediction,
                confidence,
                next_hour,
                day_of_week,
                is_weekend
            ) = predict_next_hour(model)

            payload = {
                "prediction": prediction,

                "confidence": round(
                    float(confidence),
                    3
                ),

                "predictedHour": next_hour,

                "predictedAt": datetime.now(
                    timezone.utc
                ).isoformat(),

                "model": "RandomForestClassifier",

                "features": {
                    "day_of_week": day_of_week,
                    "hour": next_hour,
                    "is_weekend": is_weekend
                }
            }

            client.publish(
                args.publish_topic,
                json.dumps(payload),
                qos=1,
                retain=True
            )

            print(
                f"[Prediction] "
                f"Hour={next_hour} "
                f"Prediction={prediction} "
                f"Confidence={confidence:.2%}"
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:

        print("\nStopping ML virtual sensor...")

    finally:

        # Publish offline status
        client.publish(
            "smartbin/bin-01/prediction/status",
            "offline",
            qos=1,
            retain=True
        )

        client.loop_stop()

        client.disconnect()


if __name__ == "__main__":
    main()