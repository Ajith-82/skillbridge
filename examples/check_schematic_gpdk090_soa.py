from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from skillbridge import Workspace


def skill_string(value: str) -> str:
    return json.dumps(value)


def build_pdk_list_expr(pdk_libs: list[str]) -> str:
    return f"list({' '.join(skill_string(lib) for lib in pdk_libs)})"


def get_current_edit_cellview(ws: Workspace) -> tuple[str, str, str]:
    result = ws._channel.send(
        'let((cv) cv=geGetEditCellView() if(cv then list(cv~>libName cv~>cellName cv~>viewName) else nil))',
    ).strip()
    values = json.loads(result)
    return values[0], values[1], values[2]


def load_schematic_json(ws: Workspace, out_path: Path, pdk_libs: list[str], skill_file: Path) -> dict[str, Any]:
    ws._channel.send(f'load({skill_string(str(skill_file))})')
    lib, cell, view = get_current_edit_cellview(ws)
    expr = (
        'sbExportOaSchematicToJson('
        f'{skill_string(lib)} '
        f'{skill_string(cell)} '
        f'{skill_string(view)} '
        f'{skill_string(str(out_path))} '
        f'{build_pdk_list_expr(pdk_libs)}'
        ')'
    )
    ws._channel.send(expr)
    return json.loads(out_path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check current schematic against compact gpdk090 SOA JSON")
    parser.add_argument(
        "--soa-json",
        type=Path,
        default=Path("/home/cloud/projects/skillbridge/build/gpdk090_typical_soa_compact.json"),
    )
    parser.add_argument(
        "--skill-file",
        type=Path,
        default=Path("/home/cloud/projects/skillbridge/examples/export_oa_schematic_json.il"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/home/cloud/projects/skillbridge/build/gpdk090_schematic_soa_check.json"),
    )
    parser.add_argument("--workspace-id", default="default")
    args = parser.parse_args()

    soa_data = json.loads(args.soa_json.read_text())
    soa_by_cell = {entry["cell"]: entry for entry in soa_data["cells"]}
    temp_json = Path("/tmp") / f"gpdk090_schematic_export_{uuid.uuid4().hex}.json"

    ws = Workspace.open(None if args.workspace_id == "default" else args.workspace_id)
    try:
        schematic = load_schematic_json(ws, temp_json, ["gpdk090"], args.skill_file)
    finally:
        ws.close()

    instances = []
    unresolved = []
    for inst in schematic["instances"]:
        if inst.get("libName") != "gpdk090":
            continue
        cell_name = inst.get("cellName")
        soa = soa_by_cell.get(cell_name)
        if soa is None:
            unresolved.append(inst["name"])
            continue
        instances.append(
            {
                "instance": inst["name"],
                "cell": cell_name,
                "model": soa["model"],
                "deviceClass": soa["deviceClass"],
                "overlayParameters": inst.get("parameters", []),
                "soa": soa["soa"],
                "connections": inst.get("connections", []),
            },
        )

    report = {
        "cellView": schematic["cellView"],
        "gpdk090InstanceCount": len(instances),
        "instances": instances,
        "unresolvedInstances": unresolved,
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True))
    try:
        temp_json.unlink(missing_ok=True)
    except PermissionError:
        pass
    print(args.out)


if __name__ == "__main__":
    main()
