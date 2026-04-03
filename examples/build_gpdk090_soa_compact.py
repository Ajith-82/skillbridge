from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOA_KEYS_BY_CLASS = {
    "mos": [
        "nominalVoltageClass",
        "ijth",
        "bforward",
        "breverse",
        "cforward",
        "creverse",
        "vth0",
        "tox",
        "u0",
        "vsat",
    ],
    "diode": [
        "bv",
        "ibv",
        "imax",
        "is",
        "cj",
        "cjsw",
    ],
    "bipolar": [
        "bf",
        "br",
        "va",
        "var",
        "ikf",
        "ikr",
        "is",
        "ise",
        "rc",
        "rb",
        "re",
    ],
    "resistor": [
        "rsh",
        "tc1",
        "tc2",
        "mr",
    ],
    "capacitor": [
        "cj",
        "cjsw",
        "tc1",
        "tc2",
    ],
}


def trim_entry(cell_entry: dict[str, Any]) -> dict[str, Any]:
    hints = cell_entry.get("soaHints", {})
    device_class = hints.get("deviceClass", "other")
    keep_keys = SOA_KEYS_BY_CLASS.get(device_class, [])
    trimmed_hints = {key: hints[key] for key in keep_keys if key in hints}

    result = {
        "cell": cell_entry["cell"],
        "model": cell_entry["model"],
        "deviceClass": device_class,
        "source": cell_entry.get("source"),
        "soa": trimmed_hints,
    }
    if cell_entry.get("cdfDefaults"):
        defaults = cell_entry["cdfDefaults"]
        result["importantCdfDefaults"] = {
            key: defaults[key]
            for key in ("model", "simModel", "m", "l", "w", "fw", "fingers", "area", "pj", "ad", "as", "pd", "ps")
            if key in defaults
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a compact gpdk090 SOA JSON")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("/home/cloud/projects/skillbridge/build/gpdk090_typical_soa_specs.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/home/cloud/projects/skillbridge/build/gpdk090_typical_soa_compact.json"),
    )
    args = parser.parse_args()

    data = json.loads(args.input.read_text())
    compact = {
        "pdk": data["pdk"],
        "corner": data["corner"],
        "sourceDir": data["sourceDir"],
        "cellCount": len(data["cells"]),
        "cells": [trim_entry(entry) for entry in data["cells"]],
    }
    args.out.write_text(json.dumps(compact, indent=2, sort_keys=True))
    print(args.out)


if __name__ == "__main__":
    main()
