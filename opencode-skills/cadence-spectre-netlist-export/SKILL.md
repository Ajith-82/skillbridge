---
name: cadence-spectre-netlist-export
description: Export a Spectre netlist from a Virtuoso schematic or config by preparing `si.env` and `cds.lib`, then running `si -batch -command nl` through the associated Virtuoso session via skillbridge. Use this skill whenever the user asks to export a Spectre netlist from a schematic, mentions `si.env`, `cds.lib`, schematic-to-Spectre flows, or wants verification of generated netlist artifacts and Cadence logs.
compatibility: opencode
---

# Cadence Spectre Netlist Export

Use this skill for the specific workflow of exporting a Spectre netlist from a schematic or config through the live Virtuoso session.

## Relationship to other skills

- Use `cadence-skillbridge-shell` for general Cadence shell execution through Virtuoso.
- Use this skill when the task is specifically schematic-to-Spectre export, `si.env` preparation, `cds.lib` setup, or validation of generated netlists.

## Workflow

1. Gather or infer the target `lib/cell/view`, simulator, and writable run directory.
2. Prefer `/tmp/...` for the run directory unless a different Virtuoso-writable path has already been verified.
3. Ensure `cds.lib` contains the required library definitions for the target design and dependencies.
4. Write `si.env` with the required schematic and simulator fields.
5. Run `si -batch -command nl` through the associated Virtuoso session, not plain Bash.
6. Verify the exit code, read the generated `si.stdout.log`, and inspect the produced netlist artifact.
7. Report the exact paths for `si.env`, `cds.lib`, log, and netlist.

## Required details

Minimum `si.env` fields:

- `simLibName`
- `simCellName`
- `simViewName`
- `simSimulator`
- `simNotIncremental`
- `simReNetlistAll`

Common optional fields:

- `simLibConfigName`
- `simVersionName`
- `simViewList`
- `simStopList`
- `simNetlistHier`

## Preferred implementation path

Prefer the bundled helper from `cadence-skillbridge-shell` rather than rebuilding the flow from scratch:

- load `references/sb_skillbridge_shell.il`
- call `sbWriteSiEnv`, `sbRunSiNetlist`, or `sbExportSpectreNetlist`
- or use `scripts/run_si_netlist_via_skillbridge.py`

When using the Python helper, the typical shape is:

```bash
PYTHONPATH="/home/cloud/projects/skillbridge" python "/home/cloud/.config/opencode/skills/cadence-skillbridge-shell/scripts/run_si_netlist_via_skillbridge.py" \
  --workspace-id default \
  --run-dir /tmp/my_run \
  --cds-lib-path /tmp/my_run/cds.lib \
  --lib-name myLib \
  --cell-name myCell \
  --view-name schematic
```

## Verification expectations

Always verify as many of these as possible:

1. skillbridge session responds
2. helper file loads into Virtuoso
3. `si` returns exit code `0`
4. the log contains start/end netlisting messages or other plausible Cadence output
5. the generated netlist exists, usually at `runDir/netlist`
6. the netlist content matches the requested design hierarchy

## Important caveats

- For ADE netlisters, use `si -batch -command nl`, not `-command netlist`.
- Do not assume the netlist lands at `runDir/netlist/input.scs`; check `runDir/netlist` too.
- If Virtuoso cannot resolve `~/.config/opencode/skills/...`, use the real repo path under `/home/cloud/projects/skillbridge/opencode-skills/...` when loading helper files.
- If the user explicitly requires Cadence commands to run in Virtuoso, do not execute `/opt/cadence/...` directly from the normal host shell.

## Output expectations

Usually provide:

- the target `lib/cell/view`
- the chosen run directory and why it is writable
- the `si.env` and `cds.lib` paths
- the command path used to invoke `si`
- the verification evidence from exit code, log, and netlist contents
