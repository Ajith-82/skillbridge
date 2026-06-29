#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Iterable

FINDER_ROOT = Path('/opt/cadence/IC231/doc/finder/SKILL')
DOC_ROOT = Path('/opt/cadence/IC231/doc')

ENTRY_RE = re.compile(
    r'\("((?:[^"\\]|\\.)*)"\s*"((?:[^"\\]|\\.)*)"\s*"((?:[^"\\]|\\.)*)"\)',
    re.S,
)
HREF_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')
SPACE_RE = re.compile(r'\s+')
FUNC_TOKEN_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*[!?]?$')


@dataclass
class FunctionEntry:
    name: str
    display_name: str
    signature: str
    summary: str
    finder_file: str
    finder_product: str
    doc_dir: str


def normalize_text(text: str) -> str:
    text = unescape(TAG_RE.sub(' ', text))
    return SPACE_RE.sub(' ', text).strip()


def normalize_signature(text: str) -> str:
    return SPACE_RE.sub(' ', text.replace('\t', ' ')).strip()


def canonical_names(display_name: str) -> list[str]:
    parts = [part.strip() for part in display_name.split(',')]
    names = [part for part in parts if FUNC_TOKEN_RE.fullmatch(part)]
    if names:
        return names
    first = parts[0] if parts else display_name.strip()
    return [first]


def parse_fnd_file(path: Path) -> list[FunctionEntry]:
    text = path.read_text(errors='ignore')
    product = path.parent.name
    doc_dir = path.stem
    results: list[FunctionEntry] = []

    for display_name, signature, summary in ENTRY_RE.findall(text):
        for name in canonical_names(display_name):
            results.append(
                FunctionEntry(
                    name=name,
                    display_name=display_name.strip(),
                    signature=normalize_signature(signature),
                    summary=normalize_text(summary),
                    finder_file=str(path),
                    finder_product=product,
                    doc_dir=doc_dir,
                ),
            )
    return results


def iter_toc_lines(path: Path) -> Iterable[str]:
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if line:
            yield line


def parse_html_description(path: Path) -> str:
    text = path.read_text(errors='ignore')
    chunks = [normalize_text(match) for match in re.findall(r'<p[^>]*>(.*?)</p>', text, re.I | re.S)]
    chunks = [chunk for chunk in chunks if chunk and len(chunk) > 30]
    return ' '.join(chunks[:2])[:1200]


def parse_title(path: Path) -> str:
    text = path.read_text(errors='ignore')
    match = re.search(r'<title>(.*?)</title>', text, re.I | re.S)
    if match:
        return normalize_text(match.group(1))
    return path.stem


def parse_toc_categories(toc_path: Path, known_functions: set[str]) -> list[dict]:
    categories: list[dict] = []
    current: dict | None = None

    for line in iter_toc_lines(toc_path):
        anchor_match = HREF_RE.search(line)
        if not anchor_match:
            continue

        href, label_html = anchor_match.groups()
        label = normalize_text(label_html)
        if not label:
            continue

        if '<p' in line.lower():
            page_name = href.split('#', 1)[0]
            page_path = toc_path.parent / page_name
            current = {
                'name': label,
                'href': str(page_path),
                'description': parse_html_description(page_path) if page_path.exists() else '',
                'functions': [],
                'subtopics': [],
            }
            categories.append(current)
            continue

        if '<dd' not in line.lower() or current is None:
            continue

        page_name = href.split('#', 1)[0]
        page_path = toc_path.parent / page_name
        item = {'label': label, 'href': str(page_path)}
        if label in known_functions:
            current['functions'].append(label)
        else:
            current['subtopics'].append(item)

    return categories


def build_index(output_root: Path) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)

    functions: dict[str, dict] = {}
    functions_by_doc: dict[str, list[str]] = defaultdict(list)
    fnd_to_doc: dict[str, dict] = {}

    fnd_files = sorted(FINDER_ROOT.rglob('*.fnd'))
    parsed_entries: list[FunctionEntry] = []
    for fnd_file in fnd_files:
        entries = parse_fnd_file(fnd_file)
        parsed_entries.extend(entries)
        doc_dir = DOC_ROOT / fnd_file.stem
        html_files = sorted(str(path) for path in doc_dir.rglob('*.html')) if doc_dir.exists() else []
        fnd_to_doc[str(fnd_file)] = {
            'finder_product': fnd_file.parent.name,
            'doc_dir': str(doc_dir),
            'toc_file': str(doc_dir / f'{doc_dir.name}TOC.html') if (doc_dir / f'{doc_dir.name}TOC.html').exists() else None,
            'html_files': html_files,
        }

    for entry in parsed_entries:
        record = functions.setdefault(
            entry.name,
            {
                'name': entry.name,
                'display_name': entry.display_name,
                'signature': entry.signature,
                'summary': entry.summary,
                'finder_product': entry.finder_product,
                'finder_file': entry.finder_file,
                'doc_dir': str(DOC_ROOT / entry.doc_dir),
                'html_page': None,
                'categories': [],
                'subtopics': [],
                'aliases': [],
            },
        )
        if entry.display_name != entry.name and entry.display_name not in record['aliases']:
            record['aliases'].append(entry.display_name)
        functions_by_doc[entry.doc_dir].append(entry.name)

    categories_by_doc: dict[str, list[dict]] = {}
    for doc_dir, function_names in sorted(functions_by_doc.items()):
        toc_candidates = list((DOC_ROOT / doc_dir).glob('*TOC.html'))
        if not toc_candidates:
            categories_by_doc[doc_dir] = []
            continue
        categories = parse_toc_categories(toc_candidates[0], set(function_names))
        categories_by_doc[doc_dir] = categories
        for category in categories:
            for function_name in category['functions']:
                record = functions[function_name]
                if category['name'] not in record['categories']:
                    record['categories'].append(category['name'])
                if category['href'] and record['html_page'] is None:
                    pass
            for function_name in category['functions']:
                page_prefix = function_name
                candidates = sorted((DOC_ROOT / doc_dir).glob(f'*{page_prefix}*.html'))
                if candidates and functions[function_name]['html_page'] is None:
                    functions[function_name]['html_page'] = str(candidates[0])

    # Second-pass page mapping by exact href lookup from TOC lines.
    for doc_dir, function_names in sorted(functions_by_doc.items()):
        toc_candidates = list((DOC_ROOT / doc_dir).glob('*TOC.html'))
        if not toc_candidates:
            continue
        toc_text = toc_candidates[0].read_text(errors='ignore')
        for function_name in function_names:
            match = re.search(
                rf'href="([^"]+)"[^>]*>{re.escape(function_name)}<',
                toc_text,
                re.I,
            )
            if match:
                functions[function_name]['html_page'] = str((toc_candidates[0].parent / match.group(1).split('#', 1)[0]).resolve())

    summary = {
        'finder_root': str(FINDER_ROOT),
        'doc_root': str(DOC_ROOT),
        'finder_files': len(fnd_files),
        'function_count': len(functions),
        'doc_sets': len(functions_by_doc),
        'generated_from': 'Cadence IC23.1 local documentation',
    }

    top_categories = []
    for doc_dir, categories in sorted(categories_by_doc.items()):
        for category in categories:
            top_categories.append(
                {
                    'doc_dir': doc_dir,
                    'name': category['name'],
                    'description': category['description'],
                    'function_count': len(category['functions']),
                    'href': category['href'],
                },
            )

    (output_root / 'metadata.json').write_text(json.dumps(summary, indent=2))
    (output_root / 'fnd_to_html_mapping.json').write_text(json.dumps(fnd_to_doc, indent=2))
    (output_root / 'categories.json').write_text(json.dumps(categories_by_doc, indent=2))
    (output_root / 'functions.json').write_text(json.dumps(dict(sorted(functions.items())), indent=2))
    (output_root / 'top_categories.json').write_text(json.dumps(top_categories, indent=2))

    lines = [
        '# Cadence SKILL Doc Index',
        '',
        f'- Finder files: {summary["finder_files"]}',
        f'- Unique function names: {summary["function_count"]}',
        f'- Documentation sets: {summary["doc_sets"]}',
        '',
        '## Main Documentation Sets',
        '',
    ]
    for finder_path, info in sorted(fnd_to_doc.items()):
        lines.append(f'- `{Path(finder_path).name}` -> `{info["doc_dir"]}` ({len(info["html_files"])} html files)')
    lines.extend(['', '## Top Categories', ''])
    for category in top_categories[:200]:
        lines.append(
            f'- `{category["doc_dir"]}` / {category["name"]} ({category["function_count"]} functions)'
        )
    (output_root / 'README.md').write_text('\n'.join(lines) + '\n')

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description='Build a precomputed Cadence SKILL documentation index')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    summary = build_index(args.output)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
