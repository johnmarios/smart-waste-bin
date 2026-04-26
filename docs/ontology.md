# Smart Wastebin Ontology (Lab 05)

Base namespace: https://github.com/johnmarios/advanced-programming-techniques-lab/blob/main/docs/ontology.md#


This document defines the custom terms used by the team models and event context in Lab 05.
Standard terms from SOSA/SSN, schema.org, BOT, and GeoSPARQL are reused directly and are not redefined here.

The ontology covers:
- Device modeling for a PIR sensor
- Wastebin and deployment environment modeling
- Streaming event metadata used by the pipeline

## Reused Standard Vocabularies

- SOSA: http://www.w3.org/ns/sosa/
- SSN: http://www.w3.org/ns/ssn/
- schema.org: https://schema.org/
- BOT: https://w3id.org/bot#
- GeoSPARQL: http://www.opengis.net/ont/geosparql#
- XML Schema Datatypes: http://www.w3.org/2001/XMLSchema#

## Custom Classes

### ck801:PirSensor

- Type: class
- Subclass of: sosa:Sensor
- Description: Passive infrared sensor entity (HC-SR501 type) used to detect motion-related events.

### ck801:Wastebin

- Type: class
- Subclass of: schema:Product
- Description: Waste collection container where one or more sensors may be hosted.

## Custom Properties

### Sensor Properties

### ck801:deployedIn

- Domain: sosa:Sensor
- Range: schema:Place or bot:Space
- Description: Connects a sensor to the environment where it is deployed.

### ck801:sensingPrinciple

- Domain: ck801:PirSensor
- Range: xsd:string
- Description: Physical sensing principle (e.g., passive infrared).

### ck801:connection

- Domain: ck801:PirSensor
- Range: xsd:string
- Description: Hardware connection style (e.g., physical pins).

### ck801:pins

- Domain: ck801:PirSensor
- Range: JSON object
- Description: Board pin mapping.

### ck801:operationMode

- Domain: ck801:PirSensor
- Range: JSON object
- Description: Operating electrical values and pin mode metadata.

### ck801:range

- Domain: ck801:PirSensor
- Range: JSON object
- Description: Detection range bounds and unit.

### ck801:cooldown

- Domain: ck801:PirSensor
- Range: JSON object
- Description: Minimum interval metadata between valid detections.

### ck801:operatingTemperature

- Domain: ck801:PirSensor
- Range: JSON object
- Description: Supported operating temperature range and unit.

### ck801:environment

- Domain: ck801:PirSensor
- Range: xsd:string
- Description: Deployment type (e.g., indoor/outdoor).


### Wastebin Properties

### ck801:locatedIn

- Domain: ck801:Wastebin
- Range: bot:Space or schema:Place
- Description: Connects a wastebin to the environment where it is located.

### ck801:material

- Domain: ck801:Wastebin
- Range: xsd:string
- Description: Primary material of the wastebin.

### ck801:capacityLiters

- Domain: ck801:Wastebin
- Range: xsd:decimal
- Description: Total wastebin capacity in liters.

### ck801:dimensions

- Domain: ck801:Wastebin
- Range: JSON object
- Description: Height, width, depth, and unit metadata.

### ck801:color

- Domain: ck801:Wastebin
- Range: xsd:string
- Description: Color of the wastebin.

### ck801:wasteType

- Domain: ck801:Wastebin
- Range: xsd:string
- Description: Waste category accepted by the wastebin.

### ck801:collectionZone

- Domain: ck801:Wastebin
- Range: xsd:string
- Description: Collection zone assignment used by operations.

### ck801:status

- Domain: ck801:PirSensor, ck801:Wastebin
- Range: xsd:string
- Description: Operational status value (e.g., active/inactive, maintenance).

### Environment Properties

### ck801:containsWastebins

- Domain: bot:Space or schema:Place
- Range: ck801:Wastebin
- Description: Connects an environment to the wastebins placed inside it.

### ck801:environmentType

- Domain: bot:Space or schema:Place
- Range: xsd:string
- Description: Broad environment category (e.g., indoor/outdoor).

### ck801:zone

- Domain: bot:Space or schema:Place
- Range: xsd:string
- Description: Internal zoning label for routing/monitoring.

### ck801:traffic

- Domain: bot:Space or schema:Place
- Range: xsd:string
- Description: Traffic/load level (e.g., low/medium/high).

### Pipeline Properties

### pipeline:motionState

- Domain: sosa:Observation
- Range: xsd:string
- Description: Human-readable motion state emitted by the pipeline (e.g., detected).

### pipeline:eventType

- Domain: sosa:Observation
- Range: xsd:string
- Description: Human-readable event category emitted by the pipeline (e.g., motion).

### pipeline:sequenceNumber

- Domain: sosa:Observation
- Range: xsd:integer
- Description: Monotonic sequence index per pipeline run.

### pipeline:runId

- Domain: sosa:Observation
- Range: xsd:string
- Description: Unique identifier for one producer-consumer execution session.

### pipeline:ingestTime

- Domain: sosa:Observation
- Range: xsd:dateTime
- Description: Time when the event was consumed by the pipeline.

### pipeline:latencyMs

- Domain: sosa:Observation
- Range: xsd:decimal
- Description: End-to-end producer-to-consumer latency in milliseconds.

### pipeline:wastebinId

- Domain: sosa:Observation
- Range: ck801:Wastebin
- Description: References the wastebin the observation is associated with.

### pipeline:environmentId

- Domain: sosa:Observation
- Range: bot:Space or schema:Place
- Description: References the environment the observation is associated with.

## JSON-LD Mapping Notes

In the current context model:
- event_time maps to sosa:resultTime
- device_id maps to sosa:madeBySensor (as @id)
- event_type maps to pipeline:eventType (as xsd:string)
- motion_state maps to pipeline:motionState
- seq maps to pipeline:sequenceNumber
- run_id maps to pipeline:runId
- ingest_time maps to pipeline:ingestTime
- pipeline_latency_ms maps to pipeline:latencyMs
- wastebin_id maps to pipeline:wastebinId
- environment_id maps to pipeline:environmentId

## Versioning

- Version: 0.1.0
- Last updated: 2026-04-06
- Change policy: additive changes preferred; avoid renaming terms already used in stored JSONL events.
