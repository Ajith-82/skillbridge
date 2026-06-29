#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from skillbridge import Workspace


def main() -> None:
    parser = argparse.ArgumentParser(description='Evaluate SKILL code through an existing skillbridge session')
    parser.add_argument('--workspace-id', default='default')
    parser.add_argument('--expr', default=None)
    parser.add_argument('--file', type=Path, default=None)
    parser.add_argument('--keep-temp', action='store_true')
    args = parser.parse_args()

    if bool(args.expr) == bool(args.file):
        raise SystemExit('Pass exactly one of --expr or --file')

    ws = Workspace.open(None if args.workspace_id == 'default' else args.workspace_id)
    try:
        if args.expr is not None:
            command = args.expr
        else:
            source = args.file.read_text()
            temp_path = None
            if args.file.suffix.lower() == '.il':
                temp_path = args.file
            else:
                handle = tempfile.NamedTemporaryFile('w', suffix='.il', delete=False)
                handle.write(source)
                handle.close()
                temp_path = Path(handle.name)
            command = f'load({json.dumps(str(temp_path))})'
        result = ws._channel.send(command).strip()
        print(result)
    finally:
        ws.close()


if __name__ == '__main__':
    main()
