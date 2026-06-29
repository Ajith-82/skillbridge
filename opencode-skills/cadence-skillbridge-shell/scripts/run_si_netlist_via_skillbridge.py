#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from skillbridge import Workspace


DEFAULT_HELPER_FILE = (
    Path(__file__).resolve().parent.parent / 'references' / 'sb_skillbridge_shell.il'
)


def _skill_string_list(values: list[str]) -> str:
    return "'(" + ' '.join(json.dumps(value) for value in values) + ")"


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Export a Spectre netlist through Virtuoso via skillbridge and si'
    )
    parser.add_argument('--workspace-id', default='default')
    parser.add_argument('--helper-file', type=Path, default=DEFAULT_HELPER_FILE)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--cds-lib-path', required=True)
    parser.add_argument('--lib-name', required=True)
    parser.add_argument('--cell-name', required=True)
    parser.add_argument('--view-name', default='schematic')
    parser.add_argument('--config-name', default=None)
    parser.add_argument('--version-name', default='')
    parser.add_argument('--simulator', default='spectre')
    parser.add_argument('--not-incremental', action='store_true')
    parser.add_argument('--no-renetlist-all', action='store_true')
    parser.add_argument('--view-list', nargs='+', default=['spectre', 'schematic', 'symbol'])
    parser.add_argument('--stop-list', nargs='+', default=['spectre'])
    parser.add_argument('--no-netlist-hier', action='store_true')
    parser.add_argument('--si-binary', default='/opt/cadence/IC231/bin/si')
    parser.add_argument('--command', default='nl')
    parser.add_argument('--log-file-name', default='si.stdout.log')
    parser.add_argument('--tail-lines', type=int, default=80)
    args = parser.parse_args()

    expr = (
        'sbExportSpectreNetlist('
        f'{json.dumps(args.run_dir)} '
        f'{json.dumps(args.cds_lib_path)} '
        f'{json.dumps(args.lib_name)} '
        f'{json.dumps(args.cell_name)} '
        f'{json.dumps(args.view_name)}'
        f' ?configName {json.dumps(args.config_name) if args.config_name is not None else "nil"}'
        f' ?versionName {json.dumps(args.version_name)}'
        f' ?simulator {json.dumps(args.simulator)}'
        f' ?notIncremental {"t" if args.not_incremental else "nil"}'
        f' ?reNetlistAll {"nil" if args.no_renetlist_all else "t"}'
        f' ?viewList {_skill_string_list(args.view_list)}'
        f' ?stopList {_skill_string_list(args.stop_list)}'
        f' ?netlistHier {"nil" if args.no_netlist_hier else "t"}'
        f' ?siBinary {json.dumps(args.si_binary)}'
        f' ?command {json.dumps(args.command)}'
        f' ?logFileName {json.dumps(args.log_file_name)}'
        f' ?tailLines {args.tail_lines}'
        ')'
    )

    ws = Workspace.open(None if args.workspace_id == 'default' else args.workspace_id)
    try:
        print(ws._channel.send(f'load({json.dumps(str(args.helper_file))})').strip())
        print(ws._channel.send(expr).strip())
    finally:
        ws.close()


if __name__ == '__main__':
    main()
