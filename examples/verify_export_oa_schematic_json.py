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
    if not pdk_libs:
        return 'nil'
    return f"list({' '.join(skill_string(lib) for lib in pdk_libs)})"


def get_current_edit_cellview(ws: Workspace) -> tuple[str, str, str]:
    result = ws._channel.send(
        'let((cv) cv=geGetEditCellView() if(cv then list(cv~>libName cv~>cellName cv~>viewName) else nil))',
    ).strip()
    if result in {'nil', '()'}:
        raise RuntimeError('No current edit cellView is available in the Virtuoso session')
    values = json.loads(result)
    if not isinstance(values, list) or len(values) != 3:
        raise RuntimeError(f'Unexpected current cellView response: {result}')
    return values[0], values[1], values[2]


def validate_export(data: dict[str, Any], lib: str, cell: str, view: str) -> dict[str, int]:
    exporter = data.get('exporter')
    if not isinstance(exporter, dict):
        raise RuntimeError('Missing or invalid exporter object')
    if exporter.get('name') != 'oa_schematic_exporter':
        raise RuntimeError(f'Unexpected exporter name: {exporter.get("name")!r}')
    if exporter.get('version') != 'v1':
        raise RuntimeError(f'Unexpected exporter version: {exporter.get("version")!r}')

    cellview = data.get('cellView')
    if not isinstance(cellview, dict):
        raise RuntimeError('Missing or invalid cellView object')
    expected = {'libName': lib, 'cellName': cell, 'viewName': view}
    for key, value in expected.items():
        if cellview.get(key) != value:
            raise RuntimeError(f'cellView.{key} mismatch: expected {value!r}, got {cellview.get(key)!r}')

    instances = data.get('instances')
    pins = data.get('pins')
    nets = data.get('nets')
    pdk_device_cdfs = data.get('pdkDeviceCdfs')
    if not isinstance(instances, list):
        raise RuntimeError('instances is not a JSON array')
    if not isinstance(pins, list):
        raise RuntimeError('pins is not a JSON array')
    if not isinstance(nets, list):
        raise RuntimeError('nets is not a JSON array')
    if not isinstance(pdk_device_cdfs, list):
        raise RuntimeError('pdkDeviceCdfs is not a JSON array')

    cdf_refs: set[str] = set()
    for device_cdf in pdk_device_cdfs:
        if not isinstance(device_cdf, dict):
            raise RuntimeError('Found non-object in pdkDeviceCdfs')
        for key in ('cdfRef', 'libName', 'cellName', 'viewName', 'parameters'):
            if key not in device_cdf:
                raise RuntimeError(f'Missing pdkDeviceCdfs key: {key}')
        if not isinstance(device_cdf['cdfRef'], str):
            raise RuntimeError('pdkDeviceCdfs.cdfRef is not a string')
        if not isinstance(device_cdf['parameters'], list):
            raise RuntimeError('pdkDeviceCdfs.parameters is not a JSON array')
        cdf_refs.add(device_cdf['cdfRef'])
        for parameter in device_cdf['parameters']:
            if not isinstance(parameter, dict):
                raise RuntimeError('Found non-object in pdkDeviceCdfs.parameters')
            for key in ('name', 'defaultValue', 'prompt', 'type', 'paramType', 'units', 'display', 'callback'):
                if key not in parameter:
                    raise RuntimeError(f'Missing device CDF parameter key: {key}')

    for instance in instances:
        if not isinstance(instance, dict):
            raise RuntimeError('Found non-object in instances')
        for key in ('name', 'kind', 'cdfRef', 'connections', 'parameters', 'rawProps', 'masterTerminals'):
            if key not in instance:
                raise RuntimeError(f'Missing instance key: {key}')
        if instance['kind'] not in {'pdkDevice', 'blackBox'}:
            raise RuntimeError(f'Unexpected instance kind: {instance["kind"]!r}')
        if not isinstance(instance['connections'], list):
            raise RuntimeError('instance.connections is not a JSON array')
        if not isinstance(instance['parameters'], list):
            raise RuntimeError('instance.parameters is not a JSON array')
        if instance['kind'] == 'pdkDevice':
            if not isinstance(instance['cdfRef'], str):
                raise RuntimeError('PDK instance cdfRef is not a string')
            if instance['cdfRef'] not in cdf_refs:
                raise RuntimeError(f'PDK instance cdfRef not found in pdkDeviceCdfs: {instance["cdfRef"]!r}')
        elif instance['cdfRef'] is not None:
            raise RuntimeError('blackBox instance cdfRef must be null')
        if 'masterProps' in instance and not isinstance(instance['masterProps'], list):
            raise RuntimeError('instance.masterProps is not a JSON array when present')
        for parameter in instance['parameters']:
            if not isinstance(parameter, dict):
                raise RuntimeError('Found non-object in instance.parameters')
            for key in ('name', 'value'):
                if key not in parameter:
                    raise RuntimeError(f'Missing parameter key: {key}')
        if instance.get('cellName') in {'ipin', 'opin'} and instance.get('libName') == 'basic':
            raise RuntimeError('basic ipin/opin should be exported via pins, not instances')

    for pin in pins:
        if not isinstance(pin, dict):
            raise RuntimeError('Found non-object in pins')
        for key in ('name', 'direction', 'netName'):
            if key not in pin:
                raise RuntimeError(f'Missing pin key: {key}')

    for net in nets:
        if not isinstance(net, dict):
            raise RuntimeError('Found non-object in nets')
        for key in ('name', 'instConnections', 'pinConnections', 'rawProps'):
            if key not in net:
                raise RuntimeError(f'Missing net key: {key}')
        if not isinstance(net['instConnections'], list):
            raise RuntimeError('net.instConnections is not a JSON array')
        if not isinstance(net['pinConnections'], list):
            raise RuntimeError('net.pinConnections is not a JSON array')

    return {'instance_count': len(instances), 'pin_count': len(pins), 'net_count': len(nets)}


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify the OA schematic JSON exporter through skillbridge')
    parser.add_argument('--workspace-id', default='default')
    parser.add_argument(
        '--skill-file',
        type=Path,
        default=Path('/home/cloud/projects/skillbridge/examples/export_oa_schematic_json.il'),
    )
    parser.add_argument('--lib', default=None)
    parser.add_argument('--cell', default=None)
    parser.add_argument('--view', default=None)
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--pdk-lib', action='append', default=[])
    parser.add_argument('--keep-json', action='store_true')
    args = parser.parse_args()

    out_path = args.out
    created_temp_path = False
    if out_path is None:
        out_path = Path('/tmp') / f'oa_export_verify_{uuid.uuid4().hex}.json'
        created_temp_path = True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_path.unlink(missing_ok=True)
    except PermissionError:
        out_path = Path('/tmp') / f'oa_export_verify_{uuid.uuid4().hex}.json'
        created_temp_path = True

    ws = Workspace.open(None if args.workspace_id == 'default' else args.workspace_id)
    try:
        ws._channel.send(f'load({skill_string(str(args.skill_file))})')

        if args.lib and args.cell and args.view:
            lib, cell, view = args.lib, args.cell, args.view
        elif any(value is not None for value in (args.lib, args.cell, args.view)):
            raise RuntimeError('Pass all of --lib/--cell/--view together, or omit all three')
        else:
            lib, cell, view = get_current_edit_cellview(ws)

        call_expr = (
            'sbExportOaSchematicToJson('
            f'{skill_string(lib)} '
            f'{skill_string(cell)} '
            f'{skill_string(view)} '
            f'{skill_string(str(out_path))} '
            f'{build_pdk_list_expr(args.pdk_lib)}'
            ')'
        )
        result = ws._channel.send(call_expr).strip()
    finally:
        ws.close()

    normalized_result = json.loads(result) if result.startswith('"') else result
    if normalized_result not in {str(out_path), 't', 'True', True}:
        raise RuntimeError(f'Exporter returned unexpected result: {result}')

    data = json.loads(out_path.read_text())
    counts = validate_export(data, lib, cell, view)

    report = {
        'verified': True,
        'skill_file': str(args.skill_file),
        'json_file': str(out_path),
        'cellView': {'libName': lib, 'cellName': cell, 'viewName': view},
        **counts,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    if created_temp_path and not args.keep_json:
        try:
            out_path.unlink(missing_ok=True)
        except PermissionError:
            pass


if __name__ == '__main__':
    main()
