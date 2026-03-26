#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, cast

INDEX_ROOT = Path(__file__).resolve().parent.parent / 'references' / 'index'
TOKEN_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_!?-]*')


def load_json(name: str) -> Any:
    return json.loads((INDEX_ROOT / name).read_text())


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def score_text(query_tokens: list[str], *values: str) -> int:
    haystack = ' '.join(values).lower()
    score = 0
    for token in query_tokens:
        if token in haystack:
            score += 3
        if f' {token}' in haystack or haystack.startswith(token):
            score += 1
    return score


def do_summary() -> None:
    print(json.dumps(load_json('metadata.json'), indent=2))


def do_function(name: str) -> None:
    functions = cast(dict[str, dict[str, Any]], load_json('functions.json'))
    if name in functions:
        print(json.dumps(functions[name], indent=2))
        return
    lowered = name.lower()
    for func_name, info in functions.items():
        aliases = [alias.lower() for alias in info.get('aliases', [])]
        if func_name.lower() == lowered or lowered in aliases:
            print(json.dumps(info, indent=2))
            return
    raise SystemExit(f'Function not found: {name}')


def do_category(query: str, limit: int) -> None:
    categories = cast(dict[str, list[dict[str, Any]]], load_json('categories.json'))
    query_tokens = tokenize(query)
    results = []
    for doc_dir, items in categories.items():
        for item in items:
            score = score_text(query_tokens, doc_dir, item['name'], item.get('description', ''))
            if score:
                results.append(
                    {
                        'score': score,
                        'doc_dir': doc_dir,
                        'name': item['name'],
                        'description': item.get('description', ''),
                        'function_count': len(item.get('functions', [])),
                        'functions': item.get('functions', [])[:30],
                        'href': item.get('href'),
                    },
                )
    results.sort(key=lambda item: (-item['score'], item['doc_dir'], item['name']))
    print(json.dumps(results[:limit], indent=2))


def do_search(query: str, limit: int) -> None:
    functions = cast(dict[str, dict[str, Any]], load_json('functions.json'))
    query_tokens = tokenize(query)
    results = []
    for name, info in functions.items():
        score = score_text(
            query_tokens,
            name,
            info.get('display_name', ''),
            info.get('summary', ''),
            ' '.join(info.get('categories', [])),
            ' '.join(info.get('aliases', [])),
        )
        if score:
            results.append(
                {
                    'score': score,
                    'name': name,
                    'summary': info.get('summary', ''),
                    'categories': info.get('categories', []),
                    'html_page': info.get('html_page'),
                    'finder_product': info.get('finder_product'),
                },
            )
    results.sort(key=lambda item: (-item['score'], item['name']))
    print(json.dumps(results[:limit], indent=2))


def do_mapping(query: str | None, limit: int) -> None:
    mapping = cast(dict[str, dict[str, Any]], load_json('fnd_to_html_mapping.json'))
    if not query:
        print(json.dumps(mapping, indent=2))
        return
    lowered = query.lower()
    filtered = {
        key: value
        for key, value in mapping.items()
        if lowered in key.lower() or lowered in value['doc_dir'].lower() or lowered in value['finder_product'].lower()
    }
    sliced = dict(list(filtered.items())[:limit])
    print(json.dumps(sliced, indent=2))


def do_recommend(task: str, limit: int) -> None:
    categories = cast(dict[str, list[dict[str, Any]]], load_json('categories.json'))
    functions = cast(dict[str, dict[str, Any]], load_json('functions.json'))
    query_tokens = tokenize(task)
    category_score_map: dict[tuple[str, str], dict[str, Any]] = {}
    for doc_dir, items in categories.items():
        for item in items:
            if not item.get('functions'):
                continue
            score = score_text(query_tokens, doc_dir, item['name'], item.get('description', ''))
            if score:
                category_score_map[(doc_dir, item['name'])] = {
                    'score': score,
                    'doc_dir': doc_dir,
                    'name': item['name'],
                    'description': item.get('description', ''),
                    'functions': item.get('functions', [])[:20],
                    'href': item.get('href'),
                }

    function_hits = []
    for name, info in functions.items():
        categories_for_function = info.get('categories', [])
        category_bonus = sum(
            category_score_map.get((str(info.get('doc_dir', '')).split('/')[-1], category_name), {}).get('score', 0)
            for category_name in categories_for_function
        )
        info = functions[name]
        score = score_text(
            query_tokens,
            name,
            info.get('summary', ''),
            ' '.join(info.get('categories', [])),
            info.get('finder_product', ''),
        ) + category_bonus
        if score:
            function_hits.append(
                {
                    'score': score,
                    'name': name,
                    'summary': info.get('summary', ''),
                    'categories': info.get('categories', []),
                    'html_page': info.get('html_page'),
                },
            )
    function_hits.sort(key=lambda item: (-item['score'], item['name']))

    for hit in function_hits[: limit * 2]:
        info = functions[hit['name']]
        doc_dir = str(info.get('doc_dir', '')).split('/')[-1]
        for category_name in info.get('categories', []):
            key = (doc_dir, category_name)
            if key in category_score_map:
                category_score_map[key]['score'] += hit['score']

    top_categories = sorted(category_score_map.values(), key=lambda item: (-item['score'], item['doc_dir'], item['name']))[:limit]
    print(json.dumps({'task': task, 'top_categories': top_categories, 'candidate_functions': function_hits[:limit]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description='Query the prebuilt Cadence SKILL documentation index')
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('summary')

    function_parser = subparsers.add_parser('function')
    function_parser.add_argument('name')

    category_parser = subparsers.add_parser('category')
    category_parser.add_argument('query')
    category_parser.add_argument('--limit', type=int, default=10)

    search_parser = subparsers.add_parser('search')
    search_parser.add_argument('query')
    search_parser.add_argument('--limit', type=int, default=20)

    mapping_parser = subparsers.add_parser('mapping')
    mapping_parser.add_argument('query', nargs='?')
    mapping_parser.add_argument('--limit', type=int, default=20)

    recommend_parser = subparsers.add_parser('recommend')
    recommend_parser.add_argument('task')
    recommend_parser.add_argument('--limit', type=int, default=12)

    args = parser.parse_args()
    if args.command == 'summary':
        do_summary()
    elif args.command == 'function':
        do_function(args.name)
    elif args.command == 'category':
        do_category(args.query, args.limit)
    elif args.command == 'search':
        do_search(args.query, args.limit)
    elif args.command == 'mapping':
        do_mapping(args.query, args.limit)
    elif args.command == 'recommend':
        do_recommend(args.task, args.limit)


if __name__ == '__main__':
    main()
