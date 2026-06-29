# OA Schematic JSON Schema

`export_oa_schematic_json.il` emits one JSON document per schematic.

## Top Level

- `exporter`: exporter name and version
- `cellView`: source schematic identity plus cellView-level `rawProps`
- `instances`: flattened instance list for the schematic only
- `pins`: top-level schematic terminals exported by terminal name
- `pdkDeviceCdfs`: deduplicated catalog of PDK device cell CDFs referenced by instances
- `nets`: schematic nets and resolved connections

## Nets

Each net contains:

- `name`
- `instConnections`: connected instance terminals
- `pinConnections`: connected top-level schematic pins
- `rawProps`

This keeps top-level pin references separate from instance connectivity.

## Instance Objects

Common fields:

- `name`
- `kind`: `pdkDevice` or `blackBox`
- `cdfRef`: `lib/cell` for PDK devices, `null` for black boxes
- `libName`, `cellName`, `viewName`
- `isPCell`
- `connections`
- `parameters`
- `rawProps`
- `masterTerminals`

### PDK Devices

- classified from the supplied `pdkLibs`, except `basic/ipin` and `basic/opin`
- `parameters` contains only per-instance overlay values relative to the shared cell CDF defaults
- `rawProps` is an empty array
- full default parameter metadata lives in `pdkDeviceCdfs`

### Black Boxes

- not expanded beyond master identity and pin connectivity
- `cdfRef` is `null`
- `parameters` is an empty array
- `rawProps` preserves instance properties from OA

## Pins

- `pins` is exported from `cv~>terminals`, not from `basic/ipin` or `basic/opin` instance names
- each pin contains `name`, `direction`, and `netName`
- `basic/ipin` and `basic/opin` helper instances are omitted from `instances`

## PDK Device CDF Catalog

Each object in `pdkDeviceCdfs` contains:

- `cdfRef`
- `libName`
- `cellName`
- `viewName`
- `parameters`

Each catalog parameter contains:

- `name`
- `defaultValue`
- `prompt`
- `type`
- `paramType`
- `units`
- `display`
- `callback`

Callbacks are exported as text only and are never evaluated.
