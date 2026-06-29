from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from skillbridge import Workspace

SECTION_RE = re.compile(
    r'^;\*+\n;\s*(?P<name>[^\n]+?)\s*\n;\*+\n',
    re.MULTILINE,
)
PAIR_RE = re.compile(r'^\s*\(\s*([A-Za-z0-9_]+)\b', re.MULTILINE)


def slugify(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')


def build_default_paths(lib_name: str) -> tuple[Path, Path]:
    slug = slugify(lib_name)
    return (
        Path(f'/tmp/{slug}_techfile_ascii.tf'),
        Path(f'/home/cloud/projects/skillbridge/examples/{slug}_technology_dump.md'),
    )


def summarize_section(section_text: str) -> dict[str, Any]:
    lines = [line for line in section_text.splitlines() if line.strip()]
    forms = PAIR_RE.findall(section_text)
    unique_forms = []
    seen = set()
    for form in forms:
        if form not in seen:
            unique_forms.append(form)
            seen.add(form)
    return {
        'nonempty_line_count': len(lines),
        'top_level_form_count': len(forms),
        'top_level_forms': unique_forms[:12],
        'preview': '\n'.join(lines[:8]),
    }


def split_sections(dump_text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_RE.finditer(dump_text))
    if not matches:
        return [('Full Dump', dump_text)]
    sections = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(dump_text)
        sections.append((match.group('name').strip(), dump_text[start:end].strip()))
    return sections


def format_markdown(lib_name: str, ascii_dump_path: Path, dump_text: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    sections = split_sections(dump_text)
    fence = '````'
    lines = [
        f'# {lib_name} Technology File Dump',
        '',
        f'- Library: `{lib_name}`',
        f'- Generated: `{timestamp}`',
        f'- Source dump: `{ascii_dump_path}`',
        f'- Section count: `{len(sections)}`',
        '',
        'This markdown file contains a section summary followed by the raw ASCII technology file dump generated through `techGetTechFile` and `tcDumpTechFile` via skillbridge.',
        '',
        '## Section Summary',
        '',
    ]

    for name, text in sections:
        summary = summarize_section(text)
        top_level_forms = cast(list[str], summary['top_level_forms'])
        lines.extend(
            [
                f'### {name}',
                '',
                f'- Non-empty lines: `{summary["nonempty_line_count"]}`',
                f'- Top-level form count: `{summary["top_level_form_count"]}`',
                f'- Top-level forms: `{", ".join(top_level_forms) if top_level_forms else "none detected"}`',
                '',
                'Preview:',
                '',
                '```text',
                str(summary['preview']),
                '```',
                '',
            ],
        )

    lines.extend(['## Raw ASCII Dump', '', f'{fence}skill', dump_text, fence, ''])
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description='Dump a Virtuoso library technology file to markdown')
    parser.add_argument('--workspace-id', default='default')
    parser.add_argument('--lib', default='ether')
    parser.add_argument('--skill-file', type=Path, default=Path('/home/cloud/projects/skillbridge/examples/dump_lib_tech.il'))
    parser.add_argument('--ascii-out', type=Path, default=None)
    parser.add_argument('--markdown-out', type=Path, default=None)
    args = parser.parse_args()

    default_ascii_out, default_markdown_out = build_default_paths(args.lib)
    ascii_out = args.ascii_out or default_ascii_out
    markdown_out = args.markdown_out or default_markdown_out

    ascii_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)

    ws = Workspace.open(None if args.workspace_id == 'default' else args.workspace_id)
    try:
        ws._channel.send(f'load("{args.skill_file}")')
        result = ws._channel.send(f'sbDumpTechFileForMarkdown("{args.lib}" "{ascii_out}" )').strip()
    finally:
        ws.close()

    if result not in {'t', 'True'}:
        raise RuntimeError(f'Tech file dump failed: {result}')

    dump_text = ascii_out.read_text(errors='replace')
    markdown_out.write_text(format_markdown(args.lib, ascii_out, dump_text))
    print(markdown_out)


if __name__ == '__main__':
    main()
