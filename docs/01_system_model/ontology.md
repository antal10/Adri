# Ontology Schema

This document defines the conceptual schema that lets Adri reason across
engineering domains. It specifies entity types, relationship types, and
property types. It is tool-agnostic and contains no implementation details.

## Design principles

1. **Extensible without breaking.** New domains add entity and relationship
   types; they never modify existing definitions.
2. **Tool-agnostic.** No entity or relationship encodes a specific tool's data
   model. Adapters translate tool-native representations into this schema.
3. **Signals are first-class.** Signals have their own entity type with
   domain-specific properties (spectrum, noise model, transfer function).
4. **Relationships are typed and directional.** Every relationship has a
   source, target, and type. Direction encodes causality or dependency.

---

## Entity types

### Physical entities

| Entity type | Description | Example |
|-------------|-------------|---------|
| `Component` | A discrete physical part or assembly. | Suspension upright, PCB, chassis tube |
| `Interface` | A boundary where two components meet. | Bolt pattern, connector pin header, weld joint |
| `Material` | A material with defined mechanical/thermal/electrical properties. | 7075-T6 aluminum, FR-4, PLA |
| `SpatialRegion` | A named region in 3D space, not necessarily a component. | "Rear-left wheel well," "cockpit zone" |

### Signal entities

| Entity type | Description | Example |
|-------------|-------------|---------|
| `Signal` | A time-varying quantity with defined domain properties. | Accelerometer output, thermocouple voltage, audio waveform |
| `SignalChain` | An ordered sequence of processing stages a signal traverses. | Sensor to conditioning to ADC to filter to storage |
| `TransferFunction` | A mathematical input-output relationship (s-domain or z-domain). | Low-pass filter H(s), plant model G(s) |

### Sensing and actuation entities

| Entity type | Description | Example |
|-------------|-------------|---------|
| `Sensor` | A device that converts a physical measurand to a signal. | ADXL345 accelerometer, K-type thermocouple |
| `Actuator` | A device that converts a signal to a physical action. | Servo motor, solenoid valve, speaker |
| `DAQChannel` | A single data acquisition input or output channel. | NI-9234 channel 0 |

### System entities

| Entity type | Description | Example |
|-------------|-------------|---------|
| `Subsystem` | A logical grouping of components that performs a function. | "Rear suspension," "telemetry stack," "cooling loop" |
| `Artifact` | A file or dataset that an adapter can ingest. | SLDASM file, .mat dataset, .wav recording |
| `Constraint` | A named design constraint with a bound and unit. | "Total sensor budget ≤ $2000," "Max added mass ≤ 0.5 kg," "Channel count ≤ 16" |

---

## Relationship types

All relationships are directional: `source --[type]--> target`.

| Relationship | Source type(s) | Target type(s) | Meaning |
|--------------|----------------|-----------------|---------|
| `mounts_to` | Component, Sensor, Actuator | Component, Interface | Physical attachment. |
| `contains` | Subsystem, Component | Component, Sensor, Actuator, Interface | Hierarchical containment. |
| `senses` | Sensor | Signal | The sensor produces this signal from a measurand. |
| `drives` | Actuator | Component | The actuator acts on this component. |
| `feeds` | Signal, DAQChannel | SignalChain, DAQChannel, TransferFunction | Signal flow from one stage to the next. |
| `constrains` | Interface, Material | Component, Sensor, Signal | A physical or electrical limitation imposed by the source's properties (e.g., a connector's pin count limits sensor channels; a material's conductivity limits shielding effectiveness). |
| `bounded_by` | Component, Sensor, Subsystem, Signal | Constraint | This entity is subject to this design constraint. |
| `controls` | TransferFunction, Actuator | Signal, Component | Control-loop authority: the source governs the target's behavior. |
| `implements` | TransferFunction | SignalChain | This transfer function describes a stage in the chain. |
| `part_of` | Component, Signal, DAQChannel | Subsystem, SignalChain | Membership in a logical grouping. |
| `derived_from` | Signal, TransferFunction | Signal, Artifact | Provenance: this entity was computed from another. |
| `references` | Artifact | any entity | An artifact is the source-of-truth for an entity's properties. |
| `located_in` | Component, Sensor, Actuator | SpatialRegion | Physical location in 3D space. |
| `made_of` | Component | Material | Material assignment. |

---

## Property types

Properties are key-value pairs attached to entities. Properties are typed to
enable validation and comparison.

### Universal properties (all entities)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier within the ontology instance. |
| `name` | string | Human-readable label. |
| `source_adapter` | string | Which adapter created this entity. |
| `source_artifact` | string (ref) | ID of the artifact this entity was ingested from. |
| `created_at` | timestamp | When the entity was added to the ontology. |

### Signal properties

| Property | Type | Description |
|----------|------|-------------|
| `domain` | enum: `time`, `frequency`, `spatial` | Signal domain. |
| `sample_rate` | float (Hz) | Sampling rate (if discrete). |
| `bandwidth` | float (Hz) | Signal bandwidth (-3 dB). |
| `noise_floor` | float (dB or unit-specific) | Noise floor level. |
| `dynamic_range` | float (dB) | Ratio of max signal to noise floor. |
| `unit` | string | Physical unit of the signal (e.g., m/s², V, Pa). |
| `spectrum` | reference | Link to a spectral representation artifact. |

### Component properties

| Property | Type | Description |
|----------|------|-------------|
| `mass` | float (kg) | Mass of the component. |
| `bounding_box` | float[6] | Axis-aligned bounding box [xmin,ymin,zmin,xmax,ymax,zmax]. |
| `material_ref` | string (ref) | Reference to a Material entity. |

### Sensor properties

| Property | Type | Description |
|----------|------|-------------|
| `measurand` | string | What physical quantity the sensor measures (e.g., acceleration, temperature). |
| `modality` | string | Sensing modality (e.g., piezoelectric, resistive, optical). |
| `range` | float[2] | Measurement range [min, max] in measurand units. |
| `sensitivity` | float | Output per unit measurand. |
| `bandwidth` | float (Hz) | Sensor bandwidth. |
| `resolution` | float | Smallest detectable change. |

### Constraint properties

| Property | Type | Description |
|----------|------|-------------|
| `bound_type` | enum: `upper`, `lower`, `equality`, `range` | Type of bound. |
| `bound_value` | float or float[2] | The numeric bound (single value or [min, max] for range). |
| `unit` | string | Unit of the constrained quantity. |

### TransferFunction properties

| Property | Type | Description |
|----------|------|-------------|
| `representation` | enum: `zpk`, `tf`, `ss`, `frd` | Math representation (zero-pole-gain, polynomial, state-space, frequency-response data). |
| `order` | int | System order. |
| `domain` | enum: `continuous`, `discrete` | s-domain or z-domain. |
| `sample_rate` | float (Hz) | If discrete, the associated sample rate. |

---

## Extensibility rules

1. **Adding a domain.** Define new entity types and relationship types in a new
   section. Existing types must not be modified.
2. **Adding properties.** New properties may be added to any entity type.
   Existing property definitions must not be changed.
3. **Adapter registration.** When an adapter creates entities, it must set
   `source_adapter` and `source_artifact` so provenance is traceable.
4. **Cross-domain links.** Relationships that span domains (e.g., a Sensor
   `mounts_to` a Component) are how the ontology enables cross-domain
   reasoning. These should be created during context assembly, not by
   individual adapters in isolation.
