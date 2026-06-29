#!/usr/bin/env python3
"""Build an HTTP-friendly netlist viewer for OpenCode app sessions."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f1117;
      --panel: #151925;
      --text: #d8deeb;
      --muted: #9aa8bf;
      --line: #2a3347;
      --comment: #7f8ea5;
      --kw: #7cc7ff;
      --inst: #ffd479;
      --num: #9fe29a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      padding: 10px 14px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    header .title {{ font-size: 13px; color: var(--muted); }}
    button {{
      border: 1px solid var(--line);
      background: #1a2030;
      color: var(--text);
      border-radius: 6px;
      padding: 4px 8px;
      cursor: pointer;
      font-size: 12px;
    }}
    main {{ padding: 12px; }}
    details.block {{
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 0 0 10px;
      overflow: hidden;
      background: #111622;
    }}
    summary {{
      cursor: pointer;
      padding: 8px 10px;
      background: #171d2b;
      color: var(--muted);
      font-size: 12px;
      user-select: none;
    }}
    pre {{
      margin: 0;
      padding: 12px;
      white-space: pre;
      overflow: auto;
      line-height: 1.42;
      font-size: 12px;
    }}
    .comment {{ color: var(--comment); }}
    .kw {{ color: var(--kw); }}
    .inst {{ color: var(--inst); }}
    .num {{ color: var(--num); }}
    .error {{ color: #ff9b9b; }}
  </style>
</head>
<body>
  <header>
    <span class="title">{banner}</span>
    <button id="expand-all" type="button">Expand all</button>
    <button id="collapse-all" type="button">Collapse all</button>
  </header>
  <main id="app"><div class="title">Loading netlist...</div></main>

  <script>
    function esc(s) {{
      return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function highlight(src) {{
      const lines = esc(src).split("\\n");
      return lines
        .map((line) => {{
          if (/^\\s*\/\//.test(line)) {{
            return `<span class="comment">${{line}}</span>`;
          }}
          let t = line;
          t = t.replace(/\\b(subckt|ends|parameters)\\b/g, "<span class=\\"kw\\">$1</span>");
          t = t.replace(/^\\s*([A-Z][A-Za-z0-9_]*)\\b/, "<span class=\\"inst\\">$1</span>");
          t = t.replace(/\\b\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+|[munpfkMGT])?\\b/g, "<span class=\\"num\\">$&</span>");
          return t;
        }})
        .join("\\n");
    }}

    function splitBlocks(text) {{
      const lines = text.replace(/\\r\\n/g, "\\n").split("\\n");
      const blocks = [];
      const outside = [];
      const isCommentOrBlank = (line) => /^\\s*(?:\/\/.*)?$/.test(line);

      const flushOutside = () => {{
        if (!outside.length) return;
        const joined = outside.join("\\n");
        if (joined.trim()) blocks.push({{ label: "Top-level", text: joined }});
        outside.length = 0;
      }};

      let i = 0;
      while (i < lines.length) {{
        const line = lines[i];
        const open = line.match(/^\\s*subckt\\s+([^\\s]+)/i);

        if (!open) {{
          outside.push(line);
          i += 1;
          continue;
        }}

        const prefix = [];
        while (outside.length && isCommentOrBlank(outside[outside.length - 1])) {{
          prefix.unshift(outside.pop());
        }}
        flushOutside();

        const name = open[1];
        const section = [...prefix, line];
        i += 1;

        while (i < lines.length) {{
          const l = lines[i];
          section.push(l);
          i += 1;

          if (/^\\s*ends\\b/i.test(l)) {{
            while (i < lines.length) {{
              const next = lines[i];
              if (!isCommentOrBlank(next)) break;

              const isNextHeader = /^\\s*\/\/\\s*(Library name|Cell name|View name)\\s*:/i.test(next);
              if (isNextHeader) break;

              section.push(next);
              i += 1;
            }}
            break;
          }}
        }}

        blocks.push({{ label: `subckt ${{name}}`, text: section.join("\\n") }});
      }}

      flushOutside();
      return blocks;
    }}

    function render(text) {{
      const app = document.getElementById("app");
      app.innerHTML = "";
      const blocks = splitBlocks(text);

      blocks.forEach((b, i) => {{
        if (!b.text.trim()) return;
        const lines = b.text.split("\\n").length;
        const details = document.createElement("details");
        details.className = "block";
        details.open = i < 2;

        const summary = document.createElement("summary");
        summary.textContent = `${{b.label}} (${{lines}} lines)`;

        const pre = document.createElement("pre");
        pre.innerHTML = highlight(b.text);

        details.appendChild(summary);
        details.appendChild(pre);
        app.appendChild(details);
      }});
    }}

    async function boot() {{
      const app = document.getElementById("app");
      try {{
        const res = await fetch("./{raw_name}", {{ cache: "no-store" }});
        if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
        const text = await res.text();
        render(text);
      }} catch (err) {{
        app.innerHTML = `<div class=\\"error\\">Failed to load netlist: ${{esc(String(err))}}</div>`;
      }}
    }}

    document.getElementById("expand-all").addEventListener("click", () => {{
      document.querySelectorAll("details.block").forEach(el => (el.open = true));
    }});
    document.getElementById("collapse-all").addEventListener("click", () => {{
      document.querySelectorAll("details.block").forEach(el => (el.open = false));
    }});

    boot();
  </script>
</body>
</html>
"""


def build_viewer(raw_name: str, title: str, banner: str) -> str:
    return HTML_TEMPLATE.format(raw_name=raw_name, title=title, banner=banner)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build netlist viewer HTML + raw netlist copy")
    parser.add_argument("--input-netlist", required=True, help="Path to source netlist file")
    parser.add_argument("--output-dir", required=True, help="Directory to write .scs and _view.html")
    parser.add_argument("--base-name", required=True, help="Base filename without extension")
    parser.add_argument(
      "--banner",
      default="Spectre netlist viewer",
      help="Banner text shown at top of viewer"
    )
    args = parser.parse_args()

    src = Path(args.input_netlist)
    out_dir = Path(args.output_dir)
    base = args.base_name

    if not src.exists() or not src.is_file():
        raise SystemExit(f"Input netlist not found: {src}")

    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / f"{base}.scs"
    html_path = out_dir / f"{base}_view.html"

    shutil.copy2(src, raw_path)

    html = build_viewer(
      raw_name=raw_path.name,
      title=f"{base} netlist viewer",
      banner=args.banner,
    )
    html_path.write_text(html)

    print(raw_path)
    print(html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
