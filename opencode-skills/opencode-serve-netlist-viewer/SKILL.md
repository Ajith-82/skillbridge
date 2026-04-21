---
name: opencode-serve-netlist-viewer
description: Display a Spectre/SPICE netlist correctly in OpenCode app sessions by publishing it over HTTP and generating a browser viewer with syntax highlighting and section folding. Use this skill whenever the user asks to show netlists in app, embed netlist content via links, fix broken inline HTML rendering, or build a readable netlist viewer for opencode serve/web sessions.
compatibility: opencode
---

# OpenCode Serve Netlist Viewer

Use this skill when the user needs netlists to render correctly in OpenCode app environments that sanitize inline HTML.

## Why this skill exists

OpenCode app chat rendering is Markdown-first and may sanitize embedded HTML/iframe/script content. The reliable pattern is:

1. Keep the raw netlist as a plain `.scs` (or `.sp`) file.
2. Generate a separate HTTP-hosted viewer HTML page.
3. Share clickable links in chat instead of relying on inline iframe embedding.

## Default workflow

1. Identify the netlist file to publish.
2. Generate viewer assets in a static-served directory (typically `tmp_exports/`):
   - `<name>.scs` raw netlist
   - `<name>_view.html` interactive viewer
3. Ensure a static server is available from the serve machine (`0.0.0.0:8765`).
4. Resolve Tailscale IP of the serve machine.
5. Verify both URLs return `200 OK`.
6. Return app-friendly links:
   - `Open interactive netlist viewer`
   - `Open raw netlist`

## Required output format

Provide links like this:

```md
[Open interactive netlist viewer](http://<TAILSCALE_IP>:8765/<NAME>_view.html)
[Open raw netlist](http://<TAILSCALE_IP>:8765/<NAME>.scs)
```

Do not claim inline iframe embedding is guaranteed in app chat.

## Viewer behavior requirements

Generated HTML viewer should support:

- syntax highlighting for comments, `subckt/ends/parameters`, device instance lines, and numeric literals
- section folding by subcircuit
- section grouping that keeps `// Library name`, `// Cell name`, `// View name` comments with the matching `subckt`
- section boundary handling that does not swallow the next block header comments

## Bundled helper

Use:

```bash
python3 "/home/cloud/projects/skillbridge/opencode-skills/opencode-serve-netlist-viewer/scripts/build_netlist_viewer.py" \
  --input-netlist "/tmp/skillbridge_adc_ref_ladder_netlist/netlist" \
  --output-dir "/home/cloud/projects/skillbridge/tmp_exports" \
  --base-name "adc_ref_ladder_netlist"
```

This writes:

- `/home/cloud/projects/skillbridge/tmp_exports/adc_ref_ladder_netlist.scs`
- `/home/cloud/projects/skillbridge/tmp_exports/adc_ref_ladder_netlist_view.html`

## Troubleshooting

- Seeing literal `class="kw">...` in output: highlighter is mutating HTML instead of raw text; regenerate with helper.
- Missing colors in chat code block: expected for some app renderers; use the external viewer URL.
- Bad section split: ensure viewer uses guarded post-`ends` handling that stops at next `Library/Cell/View` header comments.
