from flask import Flask, request
from flask_restx import Api, Resource, fields, reqparse
from datetime import datetime, timezone
import json
import os
import threading
import paho.mqtt.client as mqtt

# -----------------------------------
# Paths
# -----------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS_DIR = os.path.join(BASE_DIR, "models")

CONTEXT_FILE = os.path.join(MODELS_DIR, "context.jsonld")

BINS_FILE = os.path.join(MODELS_DIR, "wastebin.jsonld")

SENSORS_FILE = os.path.join(MODELS_DIR, "sensor.jsonld")

ENVIRONMENT_FILE = os.path.join(MODELS_DIR, "environment.jsonld")

EVENTS_FILE = os.path.join(BASE_DIR, "data/consumer/events.jsonl")
# -----------------------------------
# Load JSON file
# -----------------------------------

def load_json(filepath):

    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as file:

        data = json.load(file)

    return data


# -----------------------------------
# Save JSON file
# -----------------------------------

def save_json(filepath, data):

    with open(filepath, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


# -----------------------------------
# Load events from JSONL file
# -----------------------------------


def load_events(
    filepath,
    limit=None,
    device_id=None,
    start=None,
    end=None
):

    events = []

    if not os.path.exists(filepath):
        return events

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            try:

                record = json.loads(line)

                if device_id is not None:

                    if record.get("device_id") != device_id:
                        continue

                # Filter by start datetime

                event_time = record.get("event_time")

                if event_time is None:
                    continue

                if start is not None:

                    if event_time < start:
                        continue

                # Filter by end datetime
                if end is not None:

                    if event_time > end:
                        continue

                events.append(record)

            except json.JSONDecodeError:
                continue

    # Most recent first
    events.reverse()

    # Limit results
    if limit is not None:

        events = events[:limit]

    return events

def load_jsonl(filepath):

    records = []

    if not os.path.exists(filepath):
        return records

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            try:

                records.append(json.loads(line))

            except json.JSONDecodeError:
                continue

    return records



# -----------------------------------
# Flask app and API setup
# -----------------------------------

app = Flask(__name__)

mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="wastebin-api",
    clean_session=False
)

topic_store = {}

topic_lock = threading.Lock()

def on_message(client, userdata, msg):

    with topic_lock:

        topic_store[msg.topic] = {
            "topic": msg.topic,
            "payload": msg.payload.decode(
                "utf-8",
                errors="replace"
            ),
            "qos": msg.qos,
            "retain": msg.retain,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat().replace("+00:00", "Z")
        }


api = Api(
    app,
    version="1.0",
    title="Smart Wastebin Semantic API",
    description="Semantic REST API for Smart Wastebin IoT System",
)



# -----------------------------------
# Swagger Models
# -----------------------------------

bin_model = api.model(
    "Wastebin",
    {
        "@id": fields.String(required=True, description="Wastebin unique identifier"),
        "@type": fields.List(fields.String, description="Semantic types of the wastebin"),
        "name": fields.String(description="Human-readable wastebin name"),
        "description": fields.String(description="Wastebin description"),
        "ck801:material": fields.String(description="Wastebin material"),
        "ck801:capacityLiters": fields.Float(description="Wastebin capacity in liters"),
        "ck801:color": fields.String(description="Wastebin color"),
        "ck801:wasteType": fields.String(description="Type of waste collected"),
        "ck801:collectionZone": fields.String(description="Assigned collection zone"),
        "ck801:status": fields.String(description="Current wastebin status"),
        "ck801:fillLevel": fields.Integer(description="Current fill level percentage"),
    }
)

bin_summary_model = api.model(
    "BinSummary",
    {
        "@id": fields.String,
        "name": fields.String
    }
)


sensor_model = api.model(
    "Sensor",
    {
        "@id": fields.String(required=True, description="Sensor unique identifier"),
        "@type": fields.List(fields.String, description="Semantic types of the sensor"),
        "name": fields.String(description="Human-readable sensor name"),
        "description": fields.String(description="Sensor description"),
        "sosa:isHostedBy": fields.Raw(description="Wastebin hosting this sensor"),
    }
)


environment_model = api.model(
    "Environment",
    {
        "@id": fields.String(required=True, description="Environment unique identifier"),
        "@type": fields.List(fields.String, description="Semantic types of the environment"),
        "name": fields.String(description="Environment name"),
        "description": fields.String(description="Environment description"),
    }
)


event_model = api.model(
    "Event",
    {
        "event_time": fields.String(description="ISO timestamp of the event"),
        "device_id": fields.String(description="Sensor ID that generated the event"),
        "event_type": fields.String(description="Type of generated event"),
        "wastebin_id": fields.String(description="Associated wastebin ID"),
        "environment_id": fields.String(description="Associated environment ID"),
        "motion_state": fields.String(description="Motion state detected by PIR sensor"),
        "seq": fields.Integer(description="Event sequence number"),
        "run_id": fields.String(description="Pipeline execution ID"),
        "ingest_time": fields.String(description="Ingestion timestamp"),
        "pipeline_latency_ms": fields.Float(description="Pipeline latency in milliseconds"),
    }
)


mqtt_model = api.model(
    "MQTTPublish",
    {
        "topic": fields.String(required=True, description="MQTT topic to publish to"),
        "payload": fields.String(required=True, description="Message payload"),
        "qos": fields.Integer(description="Quality of Service", default=1),
        "retain": fields.Boolean(description="Retain message", default=False),
    }
)



# -----------------------------------
# Query Parsers
# -----------------------------------

events_parser = reqparse.RequestParser()

events_parser.add_argument(
    "limit",
    type=int,
    default=50,
    help="Max events to return"
)

events_parser.add_argument(
    "start",
    type=str,
    help="Start datetime (ISO format)"
)

events_parser.add_argument(
    "end",
    type=str,
    help="End datetime (ISO format)"
)

events_parser.add_argument(
    "device_id",
    type=str,
    help="Filter events by device ID"
)


# -----------------------------------
# Namespaces
# -----------------------------------

bins_ns = api.namespace(
    "bins",
    description="Wastebin operations"
)

sensors_ns = api.namespace(
    "sensors",
    description="Sensor operations"
)

environment_ns = api.namespace(
    "environment",
    description="Environment operations"
)

mqtt_ns = api.namespace(
    "mqtt",
    description="MQTT operations"
)

events_ns = api.namespace(
    "events",
    description="Motion event operations"
)

contexts_ns = api.namespace(
    "contexts",
    description="JSON-LD context operations"
)




# -----------------------------------
# GET /contexts/context.jsonld
# -----------------------------------

@contexts_ns.route("/context.jsonld")
class Context(Resource):

    def get(self):

        context = load_json(CONTEXT_FILE)

        return context, 200

# -----------------------------------
# GET /bins
# -----------------------------------

@bins_ns.route("/")
class BinList(Resource):

    @bins_ns.marshal_list_with(bin_summary_model)
    def get(self):

        bins = load_json(BINS_FILE)

        return bins


# -----------------------------------
# GET /bins/<bin_id>
# -----------------------------------

@bins_ns.route("/<string:bin_id>")

@bins_ns.param(
    "bin_id",
    "The wastebin identifier"
)

@bins_ns.response(
    404,
    "Wastebin not found"
)

class Bin(Resource):

    @bins_ns.marshal_with(bin_model)
    def get(self, bin_id):

        bins = load_json(BINS_FILE)

        for bin_item in bins:

            if bin_item["@id"] == bin_id:
                return bin_item

        api.abort(
            404,
            f"Wastebin {bin_id} not found"
        )

# -----------------------------------
# GET /bins/<bin_id>/sensors
# -----------------------------------

@bins_ns.route("/<string:bin_id>/sensors")

@bins_ns.param(
    "bin_id",
    "The wastebin identifier"
)

class BinSensors(Resource):

    @bins_ns.marshal_list_with(sensor_model)
    def get(self, bin_id):

        sensors = load_json(SENSORS_FILE)

        bin_sensors = []

        for sensor in sensors:

            hosted_by = sensor.get(
                "sosa:isHostedBy",
                {}
            )

            if hosted_by.get("@id") == bin_id:

                bin_sensors.append(sensor)

        return bin_sensors

# -----------------------------------
# GET /bins/<bin_id>/events
# -----------------------------------

@bins_ns.route("/<string:bin_id>/events")

@bins_ns.param(
    "bin_id",
    "The wastebin identifier"
)

class BinEvents(Resource):

    @bins_ns.expect(events_parser)

    @bins_ns.marshal_list_with(event_model)
    def get(self, bin_id):

        args = events_parser.parse_args()

        events = load_events(
            EVENTS_FILE,
            limit=args["limit"],            # Limit number of events returned
            device_id=args["device_id"],    # Filter by device ID if provided
            start=args["start"],            # Filter by start datetime if provided
            end=args["end"]                 # Filter by end datetime if provided
        )

        bin_events = []

        for event in events:

            if event.get("wastebin_id") == bin_id:

                bin_events.append(event)

        return bin_events



#-----------------------------------
# Run app
# -----------------------------------

if __name__ == "__main__":


    mqtt_client.on_message = on_message

    print("CONNECTING MQTT CLIENT")

    mqtt_client.connect("broker",1883,60)

    mqtt_client.subscribe("smartbin/#",qos=1)
    mqtt_client.subscribe("environments/#",qos=1)

    mqtt_client.loop_start()

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
