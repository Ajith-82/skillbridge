---
name: cadence-skillbridge-shell
description: Run Cadence CLI or shell commands through the associated Virtuoso session via skillbridge instead of the host shell. Use this skill whenever the user mentions `si`, Spectre netlisting, schematic export, `si.env`, `cds.lib`, `/opt/cadence/...` executables, SKILL wrappers around `system()` or `sh()`, or asks to verify command behavior through the CIW or `CDS.log`, even if they describe it as a shell command task rather than a SKILL task.
compatibility: opencode
---

# Cadence Skillbridge Shell

Use this skill when Cadence commands must run inside the live Virtuoso environment, not as ordinary host-shell processes.

## What is bundled

- `scripts/verify_skillbridge.py` - evaluate a SKILL expression or load a SKILL file through an existing skillbridge session
- `scripts/run_cadence_shell_via_skillbridge.py` - helper that loads the SKILL shell wrapper and runs a shell command through Virtuoso
- `references/sb_skillbridge_shell.il` - SKILL helpers for quoting, log tailing, and command execution through `system()`
- `scripts/run_si_netlist_via_skillbridge.py` - helper that writes or reuses `si.env` data and runs `si -batch -command nl` through Virtuoso

## When to use this skill

Use it when the task involves any of the following:

- running `si`, `spectre`, or another Cadence executable in a way that depends on the current Virtuoso session
- executing `/opt/cadence/...` commands under user instructions that explicitly require skillbridge mediation
- building a SKILL wrapper around `system()` or `sh()` for reproducible shell execution
- checking command output via the CIW or `CDS.log`
- generating or verifying netlisting artifacts such as `si.env`, `cds.lib`, and Spectre netlists
- turning a one-off shell recipe into a reusable SKILL-backed command runner for Virtuoso

## Default workflow

1. Confirm the command really should run through Virtuoso rather than plain Bash.
2. Verify the active skillbridge session with a trivial expression.
3. Prefer `system("/bin/sh -c ...")` for shell execution because it returns an exit code and supports redirection reliably.
4. For multi-step or repeatable flows, load `references/sb_skillbridge_shell.il` and call `sbRunShellCommand`, `sbRunSiNetlist`, `sbWriteSiEnv`, or `sbExportSpectreNetlist` as appropriate.
5. Write temporary logs and generated artifacts to a location the Virtuoso process can write, usually `/tmp/...`, unless another writable location is known.
6. Verify success by checking the SKILL return value, reading the generated files, and noting what should appear in the CIW or `CDS.log`.

## Important practical rules

- Do not run `/opt/cadence/...` directly with the ordinary Bash tool when the user asked for the command to execute in the associated Virtuoso.
- Prefer `system()` over `sh()` for command execution. In this environment, `system()` behaved better for exit-code capture and shell redirection.
- Wrap the actual command with `/bin/sh -c '...'` so `cd`, redirection, and compound commands behave predictably.
- Assume repo paths under `/home/cloud/projects/...` may not be writable from Virtuoso. Use `/tmp/...` for run directories unless you have already verified a path is writable.
- Print the command, exit code, and relevant log tail from SKILL so the CIW and `CDS.log` capture a human-auditable trace.
- If Virtuoso cannot resolve `~/.config/opencode/skills/...`, load helper files from the real repo path instead. The bundled runner script resolves its helper path this way automatically.

## Verified command patterns

Check skillbridge first:

```bash
PYTHONPATH="/home/cloud/projects/skillbridge" python "/home/cloud/.config/opencode/skills/cadence-skillbridge-shell/scripts/verify_skillbridge.py" --workspace-id default --expr "1+2"
```

Run a shell command through Virtuoso with the bundled helper:

```bash
PYTHONPATH="/home/cloud/projects/skillbridge" python "/home/cloud/.config/opencode/skills/cadence-skillbridge-shell/scripts/run_cadence_shell_via_skillbridge.py" \
  --workspace-id default \
  --shell-command "cd /tmp/my_run && /opt/cadence/IC231/bin/si -batch -command nl -cdslib /tmp/my_run/cds.lib > /tmp/my_run/si.stdout.log 2>&1" \
  --log-path /tmp/my_run/si.stdout.log
```

Run a dedicated `si` netlist export through Virtuoso:

```bash
PYTHONPATH="/home/cloud/projects/skillbridge" python "/home/cloud/.config/opencode/skills/cadence-skillbridge-shell/scripts/run_si_netlist_via_skillbridge.py" \
  --workspace-id default \
  --run-dir /tmp/my_run \
  --cds-lib-path /tmp/my_run/cds.lib \
  --lib-name myLib \
  --cell-name myCell \
  --view-name schematic
```

Load the SKILL helper directly:

```bash
PYTHONPATH="/home/cloud/projects/skillbridge" python "/home/cloud/.config/opencode/skills/cadence-skillbridge-shell/scripts/verify_skillbridge.py" --workspace-id default --expr "load(\"/home/cloud/projects/skillbridge/opencode-skills/cadence-skillbridge-shell/references/sb_skillbridge_shell.il\")"
```

## `si` and Spectre netlisting guidance

Cadence docs for direct integration confirm the following:

- the `si` flow supports ADE netlisters `spectre` and `Ultrasim`
- for netlist-only operation, use `si -batch -command nl`
- do not use `-command netlist` for ADE netlisters

Minimum `si.env` fields usually needed for schematic-to-Spectre export:

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

Verification notes from the working flow:

- a successful `si` netlisting run can produce the main netlist at `runDir/netlist`
- do not assume the file is always `runDir/netlist/input.scs`
- keep `cds.lib` and `si.env` in the same writable run directory unless you have a reason not to
- the bundled wrapper already knows how to write `si.env` and invoke `si` from the same Virtuoso session

## Verification checklist

For any command run through this skill, try to confirm all of these when applicable:

1. skillbridge session is reachable
2. helper SKILL file loads without error
3. shell command exit code is captured
4. redirected log file exists and contains the expected messages
5. expected output artifact exists and has plausible contents
6. CIW or `CDS.log` should show the printed command, exit code, and log tail

## Output expectations

When using this skill, usually provide:

- the exact shell command path and why it must run through Virtuoso
- the SKILL wrapper or helper invocation used
- the writable run directory chosen
- the verification evidence: exit code, log snippets, and artifact paths
- any environment caveats such as path permissions or missing libraries
