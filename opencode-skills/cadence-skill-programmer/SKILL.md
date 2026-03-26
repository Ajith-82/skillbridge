---
name: cadence-skill-programmer
description: Write, debug, explain, or refactor Cadence SKILL code for Virtuoso. Use this skill whenever the user asks for SKILL automation, Virtuoso editor commands, layout or schematic scripting, bindkeys, forms, database access, PCells, tech file manipulation, OCEAN/DFII SKILL, or wants a Cadence API/function identified from local documentation. This skill uses a prebuilt index of `/opt/cadence/IC231/doc/finder/SKILL/` and the matching HTML reference docs, then verifies code through an existing skillbridge session when possible.
compatibility: opencode
---

# Cadence SKILL Programmer

Use this skill for Cadence Virtuoso SKILL work. Prefer the prebuilt local documentation index before doing broad filesystem searches.

## What is bundled

- `references/index/functions.json` - prebuilt function index from the local finder `.fnd` files
- `references/index/categories.json` - category definitions with descriptions and function membership
- `references/index/fnd_to_html_mapping.json` - prebuilt mapping from finder files to HTML doc sets
- `references/index/README.md` - compact summary of the generated resources
- `scripts/query_skill_docs.py` - fast query helper over the prebuilt index
- `scripts/verify_skillbridge.py` - helper for evaluating SKILL through an already running skillbridge session
- `scripts/build_index.py` - rebuilds the index if Cadence docs change; do not run this during ordinary programming tasks

## Default workflow

1. Understand the user's real goal, not just the first function they mention.
2. Query the prebuilt index to find likely categories and functions.
3. Read the specific function docs or category docs for the short list you plan to use.
4. Write the SKILL code.
5. Verify it through the existing skillbridge session if verification is possible.
6. If verification fails, inspect the error, revise the code, and test again.

## How to query the docs

Start with the helper script instead of raw grep.

Typical commands:

```bash
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/query_skill_docs.py" summary
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/query_skill_docs.py" search "bindkey selected object refresh window" --limit 15
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/query_skill_docs.py" category "database access shapes nets" --limit 10
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/query_skill_docs.py" function dbCreateRect
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/query_skill_docs.py" mapping skdfref
```

Use `recommend` only as a starting point. Treat it as heuristic, not authoritative.

```bash
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/query_skill_docs.py" recommend "create a layout bindkey that zooms to the selected object"
```

## When the index is not enough

If the query results are ambiguous or incomplete:

1. Read the referenced HTML pages directly from the paths returned by the query helper.
2. Search the local Cadence docs with `grep` for exact function names, object classes, keywords, or examples.
3. Cross-check neighboring functions from the same category before choosing private or unsupported APIs.

Prefer documented public functions from the indexed categories. Avoid private or undocumented functions unless the user explicitly accepts that risk.

## Verification loop

When the user wants working SKILL, not just a sketch, verify against the running Virtuoso session.

Use the helper script when appropriate:

```bash
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/verify_skillbridge.py" --workspace-id default --expr "1+2"
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/verify_skillbridge.py" --workspace-id default --file /tmp/test.il
```

Verification pattern:

1. Create a minimal testable version first.
2. Load or evaluate it through skillbridge.
3. Check the result, warnings, and behavioral outcome.
4. If it fails, explain the likely cause, revise the code, and verify again.
5. Only stop once the code works or you hit an environment limitation you can state clearly.

## Practical guidance

- Prefer the smallest set of functions that directly accomplish the task.
- Choose APIs that match the editor/domain: `ge*` for graphics/editor actions, `db*` for database objects, `de*` for design editor behavior, `hi*` for forms/UI, layout-specific functions from `sklayoutref` when the task is layout-only, and core language functions from `sklangref` for general SKILL structure.
- For bindkeys and UI customization, expect useful functions in `skuiref`, `skdfref`, and `sklayoutref`.
- For database mutations, verify on a minimal object or current edit cellview before producing a final answer.
- When several functions are plausible, tell the user which one you chose and why.

## Output expectations

For implementation requests, usually provide:

- the SKILL code
- a short explanation of the chosen APIs
- how it was verified, or exactly what blocked verification
- any follow-up steps needed in Virtuoso

For exploratory requests, usually provide:

- likely function categories
- candidate functions with brief rationale
- relevant doc paths for deeper reading

## Rebuilding the prebuilt index

Only do this when the Cadence documentation install changes.

```bash
python "/home/cloud/.config/opencode/skills/cadence-skill-programmer/scripts/build_index.py" --output "/home/cloud/.config/opencode/skills/cadence-skill-programmer/references/index"
```
