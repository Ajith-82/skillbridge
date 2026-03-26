from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from skillbridge import Workspace


def format_markdown(lib_name: str, ascii_dump_path: Path, dump_text: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    fence = '````'
    return (
        f'# {lib_name} Technology File Dump\n\n'
        f'- Library: `{lib_name}`\n'
        f'- Generated: `{timestamp}`\n'
        f'- Source dump: `{ascii_dump_path}`\n\n'
        'This markdown file contains the raw ASCII technology file dump generated through '\
        '`techGetTechFile` and `tcDumpTechFile` via skillbridge.\n\n'
        f'{fence}skill\n{dump_text}\n{fence}\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='Dump a Virtuoso library technology file to markdown')
    parser.add_argument('--workspace-id', default='default')
    parser.add_argument('--lib', default='ether')
    parser.add_argument('--skill-file', type=Path, default=Path('/home/cloud/projects/skillbridge/examples/dump_lib_tech.il'))
    parser.add_argument('--ascii-out', type=Path, default=Path('/tmp/ether_techfile_ascii.tf'))
    parser.add_argument('--markdown-out', type=Path, default=Path('/home/cloud/projects/skillbridge/examples/ether_technology_dump.md'))
    args = parser.parse_args()

    args.ascii_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)

    ws = Workspace.open(None if args.workspace_id == 'default' else args.workspace_id)
    try:
        ws._channel.send(f'load("{args.skill_file}")')
        result = ws._channel.send(f'sbDumpLibTechFile("{args.lib}" "{args.ascii_out}" nil "w" t)').strip()
    finally:
        ws.close()

    if result not in {'t', 'True'}:
        raise RuntimeError(f'Tech file dump failed: {result}')

    dump_text = args.ascii_out.read_text(errors='replace')
    args.markdown_out.write_text(format_markdown(args.lib, args.ascii_out, dump_text))
    print(args.markdown_out)


if __name__ == '__main__':
    main()
