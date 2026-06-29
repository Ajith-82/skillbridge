#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from skillbridge import Workspace


DEFAULT_HELPER_FILE = (
    Path(__file__).resolve().parent.parent / 'references' / 'sb_skillbridge_shell.il'
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run a shell command through Virtuoso via skillbridge'
    )
    parser.add_argument('--workspace-id', default='default')
    parser.add_argument(
        '--helper-file',
        type=Path,
        default=DEFAULT_HELPER_FILE,
    )
    parser.add_argument('--shell-command', required=True)
    parser.add_argument('--workdir', default=None)
    parser.add_argument('--log-path', default=None)
    parser.add_argument('--tail-lines', type=int, default=80)
    args = parser.parse_args()

    ws = Workspace.open(None if args.workspace_id == 'default' else args.workspace_id)
    try:
        print(ws._channel.send(f'load({json.dumps(str(args.helper_file))})').strip())

        pieces = [
            'sbRunShellCommand(',
            json.dumps(args.shell_command),
        ]
        if args.workdir is not None:
            pieces.extend([' ?workDir ', json.dumps(args.workdir)])
        if args.log_path is not None:
            pieces.extend([' ?logPath ', json.dumps(args.log_path)])
        if args.tail_lines is not None:
            pieces.extend([' ?tailLines ', str(args.tail_lines)])
        pieces.append(')')
        expr = ''.join(pieces)
        print(ws._channel.send(expr).strip())
    finally:
        ws.close()


if __name__ == '__main__':
    main()
