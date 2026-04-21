---
name: opencode-serve-media-embed
description: Find exported PDF/PNG artifacts on the machine running `opencode serve` or `opencode web`, start or verify a web file service on `0.0.0.0:8765`, resolve the machine Tailscale IP, and produce app-ready embedded Markdown links and image tags. Use this skill whenever the user asks to show images/PDFs in the OpenCode app, mentions embedded preview not rendering, asks for Tailscale-accessible links, or needs a reproducible serve-to-app media display workflow.
compatibility: opencode
---

# OpenCode Serve Media Embed

Use this skill to publish local exported media (usually schematic PNG/PDF) from the serve machine and render it correctly in the OpenCode app.

## What this skill does

1. Locate candidate `.pdf` and `.png` files on the serve machine.
2. Start or verify a static web server bound to `0.0.0.0:8765`.
3. Resolve the serve machine Tailscale IPv4 address.
4. Build app-ready embed output:
   - clickable links for PNG/PDF
   - Markdown image embed for PNG
   - optional HTML `<img>` and `<iframe>` fallback probes
5. Validate URLs return `200 OK` before sending to the user.

## Default workflow

Follow this order every time:

1. Confirm export files exist (prefer `tmp_exports/` first).
2. Choose web root deliberately:
   - If serving `.../tmp_exports`, URLs are `http://<TAILSCALE_IP>:8765/<filename>`.
   - If serving repo root, URLs are `http://<TAILSCALE_IP>:8765/tmp_exports/<filename>`.
3. Check whether port `8765` is already listening. Reuse an existing valid server when possible.
4. If needed, start server:

```bash
python3 -m http.server 8765 --bind 0.0.0.0 --directory /home/cloud/projects/skillbridge/tmp_exports
```

5. Get Tailscale IPv4 (prefer JSON parsing when available).
6. Probe final URLs with `curl -I` (or equivalent) and verify `200 OK`.
7. Reply with ready-to-paste embed markdown.

## Embedded output template

Always give both direct links and an image embed:

```md
[Open PNG](http://<TAILSCALE_IP>:8765/<PNG_FILENAME>)
[Open PDF](http://<TAILSCALE_IP>:8765/<PDF_FILENAME>)

![schematic](http://<TAILSCALE_IP>:8765/<PNG_FILENAME>)
```

If the app may sanitize HTML, mention that Markdown image is the primary render path and HTML is only a fallback test.

Optional fallback probe:

```html
<img src="http://<TAILSCALE_IP>:8765/<PNG_FILENAME>" alt="schematic" width="900" />
<iframe src="http://<TAILSCALE_IP>:8765/<PDF_FILENAME>" width="100%" height="700"></iframe>
```

## Troubleshooting checklist

- `404` on URL: wrong server root vs URL path shape.
- Port occupied: inspect listening process and reuse or restart intentionally.
- Tailscale URL unreachable: verify both machines are in the same tailnet and target machine is online.
- App not rendering image but link opens: keep Markdown link + image; HTML likely sanitized.
- Multiple candidate files: pick the most recent export unless user names a specific file.

## Guardrails

- Do not assume app can read serve machine filesystem paths directly.
- Do not return local absolute paths as the final viewing method.
- Always include at least one network URL that the app machine can fetch.
- Prefer deterministic, copy-pasteable output.

## Bundled helper

Use `scripts/publish_embed_links.py` to automate file discovery, optional server start, URL checks, and markdown snippet generation.

Example:

```bash
python3 "/home/cloud/projects/skillbridge/opencode-skills/opencode-serve-media-embed/scripts/publish_embed_links.py" \
  --exports-dir "/home/cloud/projects/skillbridge/tmp_exports" \
  --port 8765 \
  --start-server
```
