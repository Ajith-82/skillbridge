from __future__ import annotations

import argparse
import ast
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skillbridge import Workspace


SOURCE_DIR = Path(
    "/home/cloud_no_ex_network/projects/RAKs/Custom_IC_Design_Flow/share/CDK090/gpdk090/models/spectre",
)
TYPICAL_TOP_SECTION = "NN"
TOP_FILE = "gpdk090.scs"
SPECTRE_SUFFIXES = {
    "t": 1e12,
    "g": 1e9,
    "meg": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    "a": 1e-18,
}


@dataclass
class IncludeRef:
    file_name: str
    section: str


def skill_string(value: str) -> str:
    return json.dumps(value)


def read_via_skillbridge(ws: Workspace, source: Path, dest_dir: Path) -> str:
    dest = dest_dir / source.name
    command = f'sh("mkdir -p {dest_dir} && cp {source} {dest}")'
    ws._channel.send(command)
    return dest.read_text()


def fetch_required_files(ws: Workspace, dest_dir: Path) -> dict[str, str]:
    files = [
        SOURCE_DIR / TOP_FILE,
        SOURCE_DIR / "gpdk090_mos.scs",
        SOURCE_DIR / "gpdk090_mos_iso.scs",
        SOURCE_DIR / "gpdk090_resistor.scs",
        SOURCE_DIR / "gpdk090_capacitor.scs",
        SOURCE_DIR / "gpdk090_diode.scs",
        SOURCE_DIR / "gpdk090_bipolar.scs",
    ]
    contents: dict[str, str] = {}
    for file_path in files:
        contents[file_path.name] = read_via_skillbridge(ws, file_path, dest_dir)
    return contents


def get_gpdk090_cells(ws: Workspace) -> list[dict[str, Any]]:
    expr = (
        'let((lib cells out cell cdf modelParam simModelParam paramList cdfParam) '
        'lib=ddGetObj("gpdk090") '
        'cells=lib~>cells '
        'out=nil '
        'foreach(cell cells '
        'cdf=cdfGetCellCDF(cell) '
        'modelParam=if(cdf cdfFindParamByName(cdf "model") nil) '
        'simModelParam=if(cdf cdfFindParamByName(cdf "simModel") nil) '
        'when(or(and(modelParam modelParam~>defValue) and(simModelParam simModelParam~>defValue)) '
        'paramList=nil '
        'foreach(cdfParam cdf~>parameters '
        'paramList=cons(list(cdfParam~>name cdfParam~>defValue cdfParam~>paramType cdfParam~>prompt) paramList)) '
        'out=cons(list(cell~>name if(modelParam modelParam~>defValue nil) if(simModelParam simModelParam~>defValue nil) reverse(paramList)) out))) '
        'reverse(out))'
    )
    raw = ws._channel.send(expr).strip()
    rows = ast.literal_eval(raw)
    cells: list[dict[str, Any]] = []
    for cell_name, model_name, sim_model_name, params in rows:
        cdf_defaults = {}
        cdf_meta = {}
        for name, default_value, param_type, prompt in params:
            cdf_defaults[name] = default_value
            cdf_meta[name] = {"paramType": param_type, "prompt": prompt}
        cells.append(
            {
                "cell": cell_name,
                "model": model_name,
                "simModel": sim_model_name,
                "cdfDefaults": cdf_defaults,
                "cdfMeta": cdf_meta,
            },
        )
    return cells


def extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        start = re.match(r"^\s*section\s+(\S+)", line)
        if start:
            current_name = start.group(1)
            current_lines = []
            continue
        end = re.match(r"^\s*endsection\s+(\S+)", line)
        if end and current_name:
            sections[current_name] = "\n".join(current_lines)
            current_name = None
            current_lines = []
            continue
        if current_name:
            current_lines.append(line)
    return sections


def parse_assignments(expr: str) -> dict[str, str]:
    normalized = re.sub(r"\\\n", " ", expr)
    normalized = re.sub(r"//.*?(?=\s+[A-Za-z_][A-Za-z0-9_]*\s*=|$)", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    result: dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)(?=\s+[A-Za-z_][A-Za-z0-9_]*\s*=|$)", normalized):
        value = re.sub(r"\s+\+\s*$", "", match.group(2).strip())
        result[match.group(1)] = value
    return result


def spectre_number_to_float(token: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(meg|[TGMKkmunpfa]?)", token)
    if not match:
        raise ValueError(f"Unsupported numeric token: {token}")
    number = float(match.group(1))
    suffix = match.group(2).lower()
    return number * SPECTRE_SUFFIXES.get(suffix, 1.0)


def substitute_spectre_numbers(expr: str) -> str:
    pattern = re.compile(r"(?<![A-Za-z0-9_])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:meg|[TGMKkmunpfa])?)(?![A-Za-z0-9_])")

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        try:
            return repr(spectre_number_to_float(token))
        except ValueError:
            return token

    return pattern.sub(repl, expr)


def safe_eval_numeric(expr: str, context: dict[str, float]) -> float | None:
    translated = substitute_spectre_numbers(expr)
    translated = translated.replace("^", "**")
    node = ast.parse(translated, mode="eval")

    def eval_node(current: ast.AST) -> float:
        if isinstance(current, ast.Expression):
            return eval_node(current.body)
        if isinstance(current, ast.Constant) and isinstance(current.value, (int, float)):
            return float(current.value)
        if isinstance(current, ast.Name):
            if current.id in context:
                return float(context[current.id])
            if current.id.endswith("_mc"):
                return 0.0
            raise KeyError(current.id)
        if isinstance(current, ast.BinOp):
            if isinstance(current.op, ast.Add):
                left = eval_node(current.left)
                right = eval_node(current.right)
                return left + right
            if isinstance(current.op, ast.Sub):
                left = eval_node(current.left)
                right = eval_node(current.right)
                return left - right
            if isinstance(current.op, ast.Mult):
                try:
                    left = eval_node(current.left)
                except KeyError:
                    right = eval_node(current.right)
                    if right == 0:
                        return 0.0
                    raise
                try:
                    right = eval_node(current.right)
                except KeyError:
                    if left == 0:
                        return 0.0
                    raise
                return left * right
            if isinstance(current.op, ast.Div):
                left = eval_node(current.left)
                right = eval_node(current.right)
                return left / right
            if isinstance(current.op, ast.Pow):
                left = eval_node(current.left)
                right = eval_node(current.right)
                return left**right
            raise ValueError(f"Unsupported operator: {ast.dump(current.op)}")
        if isinstance(current, ast.UnaryOp):
            operand = eval_node(current.operand)
            if isinstance(current.op, ast.USub):
                return -operand
            if isinstance(current.op, ast.UAdd):
                return operand
            raise ValueError(f"Unsupported unary operator: {ast.dump(current.op)}")
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Name) and current.func.id == "sqrt":
            if len(current.args) != 1:
                raise ValueError("sqrt expects one argument")
            return math.sqrt(eval_node(current.args[0]))
        raise ValueError(f"Unsupported expression: {ast.dump(current)}")

    try:
        return eval_node(node)
    except (SyntaxError, ValueError, KeyError, ZeroDivisionError):
        return None


def resolve_param_values(raw_values: dict[str, Any], base_context: dict[str, float]) -> tuple[dict[str, Any], dict[str, float]]:
    resolved: dict[str, Any] = {}
    numeric_context = dict(base_context)
    pending = dict(raw_values)
    progress = True
    while pending and progress:
        progress = False
        for key in list(pending.keys()):
            value = pending[key]
            if isinstance(value, (int, float, bool)) or value is None:
                resolved[key] = value
                if isinstance(value, (int, float)):
                    numeric_context[key] = float(value)
                pending.pop(key)
                progress = True
                continue
            if not isinstance(value, str) or not value.strip() or '"' in value or "iPar(" in value or "region" in value:
                resolved[key] = value
                pending.pop(key)
                progress = True
                continue
            clean_value = value.split("//", 1)[0].replace("\\", " ").strip()
            numeric_value = safe_eval_numeric(clean_value, numeric_context)
            if numeric_value is None:
                continue
            resolved[key] = numeric_value
            numeric_context[key] = numeric_value
            pending.pop(key)
            progress = True
    resolved.update(pending)
    return resolved, numeric_context


def maybe_numeric_scalar(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    clean_value = value.split("//", 1)[0].replace("\\", " ").strip()
    numeric_value = safe_eval_numeric(clean_value, {})
    return value if numeric_value is None else numeric_value


def parse_section_parameters(section_text: str) -> dict[str, str]:
    block_lines: list[str] = []
    capture = False
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("parameters"):
            capture = True
            block_lines.append(stripped[len("parameters") :].strip())
            continue
        if capture:
            if not stripped or stripped.startswith(("*", "//")):
                continue
            if stripped.startswith("+"):
                block_lines.append(stripped[1:].strip())
                continue
            break
    return parse_assignments(" ".join(block_lines))


def parse_includes(section_text: str) -> list[IncludeRef]:
    refs = []
    for file_name, section in re.findall(r'include\s+"([^"]+)"\s+section\s*=\s*([A-Za-z0-9_]+)', section_text):
        refs.append(IncludeRef(file_name=file_name, section=section))
    return refs


def parse_subckts(section_text: str) -> dict[str, dict[str, Any]]:
    lines = section_text.splitlines()
    subckts: dict[str, dict[str, Any]] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^\s*(?:inline\s+)?subckt\s+(\S+)\s*(?:\(([^)]*)\)|(.*))$", line)
        if not match:
            i += 1
            continue
        name = match.group(1)
        port_text = match.group(2) if match.group(2) is not None else (match.group(3) or "")
        ports = [port for port in port_text.split() if port]
        body_lines = [line]
        i += 1
        while i < len(lines):
            body_lines.append(lines[i])
            if re.match(rf"^\s*ends\s+{re.escape(name)}\b", lines[i]):
                break
            i += 1
        body_text = "\n".join(body_lines)
        params: dict[str, str] = {}
        param_match = re.search(r"\bparameters\b(.*?)(?:\n\s*[A-Za-z0-9_]+\s*\(|\n\s*[A-Za-z0-9_]+\s+\(|\n\s*model\b|\n\s*ends\b)", body_text, re.S)
        if param_match:
            params = parse_assignments(param_match.group(1))
        model_refs: list[str] = []
        for body_line in body_lines[1:]:
            stripped = body_line.strip()
            if not stripped or stripped.startswith(("//", "*", "+", "parameters", "model", "ends")):
                continue
            paren_match = re.match(r"^\S+\s*\([^)]*\)\s*(\S+)", stripped)
            if paren_match:
                model_ref = paren_match.group(1)
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", model_ref):
                    model_refs.append(model_ref)
        subckts[name] = {
            "ports": ports,
            "defaultParams": params,
            "modelRefs": sorted(set(model_refs)),
        }
        i += 1
    return subckts


def parse_models(section_text: str) -> dict[str, dict[str, Any]]:
    lines = section_text.splitlines()
    models: dict[str, dict[str, Any]] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^\s*model\s+(\S+)\s+(\S+)(.*)", line)
        if not match:
            i += 1
            continue
        name = match.group(1)
        kind = match.group(2)
        parts = [match.group(3).strip()]
        i += 1
        while i < len(lines) and lines[i].lstrip().startswith("+"):
            parts.append(lines[i].lstrip()[1:].strip())
            i += 1
        params = parse_assignments(" ".join(part for part in parts if part))
        models[name] = {"kind": kind, "params": params}
    return models


def classify_model(model_name: str) -> str:
    if "mos" in model_name:
        return "mos"
    if "dio" in model_name:
        return "diode"
    if "res" in model_name:
        return "resistor"
    if "mimcap" in model_name or "cap" in model_name:
        return "capacitor"
    if model_name in {"gpdk090_npn", "gpdk090_pnp", "gpdk090_vpnp", "gpdk090_vpnp2", "gpdk090_vpnp5", "gpdk090_vpnp10"}:
        return "bipolar"
    return "other"


def nominal_voltage_hint(model_name: str) -> str | None:
    if "1v" in model_name:
        return "1V"
    if "2v" in model_name:
        return "2V"
    return None


def collect_soa_hints(model_name: str, subckt: dict[str, Any], models: dict[str, dict[str, Any]]) -> dict[str, Any]:
    hints: dict[str, Any] = {}
    hints["deviceClass"] = classify_model(model_name)
    nominal = nominal_voltage_hint(model_name)
    if nominal:
        hints["nominalVoltageClass"] = nominal
    defaults = subckt.get("defaultParams", {})
    for key in ("l", "w", "area", "pj", "as", "ad", "ps", "pd"):
        if key in defaults:
            hints[f"default_{key}"] = maybe_numeric_scalar(defaults[key])
    for model_ref in subckt.get("modelRefs", []):
        model_info = models.get(model_ref)
        if not model_info:
            continue
        params = model_info["resolvedParams"]
        if model_info["kind"] == "diode":
            for key in ("bv", "ibv", "imax", "rs", "is", "cj", "cjsw"):
                if key in params:
                    hints[key] = maybe_numeric_scalar(params[key])
        elif model_info["kind"] == "bjt":
            for key in ("bf", "br", "va", "var", "ikf", "ikr", "rc", "rb", "re", "is", "ise"):
                if key in params:
                    hints[key] = maybe_numeric_scalar(params[key])
        elif model_info["kind"] == "bsim3v3":
            for key in ("tox", "vth0", "ijth", "bforward", "breverse", "cforward", "creverse", "u0", "vsat"):
                if key in params:
                    hints[key] = maybe_numeric_scalar(params[key])
        elif model_info["kind"] in {"phy_res", "rdiff", "resistor"}:
            for key in ("rsh", "tc1", "tc2", "mr"):
                if key in params:
                    hints[key] = maybe_numeric_scalar(params[key])
        elif model_info["kind"] == "capacitor":
            for key in ("cj", "cjsw", "tc1", "tc2"):
                if key in params:
                    hints[key] = maybe_numeric_scalar(params[key])
    return hints


def build_model_catalog(file_contents: dict[str, str]) -> dict[str, dict[str, Any]]:
    section_map = {name: extract_sections(text) for name, text in file_contents.items()}
    top_sections = section_map[TOP_FILE]
    typical_includes = parse_includes(top_sections[TYPICAL_TOP_SECTION])

    models: dict[str, dict[str, Any]] = {}
    for include_ref in typical_includes:
        source_sections = section_map[include_ref.file_name]
        corner_text = source_sections[include_ref.section]
        corner_params = parse_section_parameters(corner_text)
        nested_includes = parse_includes(corner_text)
        if not nested_includes:
            nested_includes = [include_ref]
        nested_parameter_context = dict(corner_params)
        for nested in nested_includes:
            nested_parameter_context.update(parse_section_parameters(source_sections[nested.section]))
        for nested in nested_includes:
            impl_text = source_sections[nested.section]
            subckts = parse_subckts(impl_text)
            model_defs = parse_models(impl_text)
            aggregate_params = dict(nested_parameter_context)
            resolved_corner_params, numeric_corner_context = resolve_param_values(aggregate_params, {})
            for subckt_name, subckt_info in subckts.items():
                resolved_defaults, numeric_subckt_context = resolve_param_values(subckt_info["defaultParams"], numeric_corner_context)
                resolved_model_defs = {}
                for model_ref in subckt_info["modelRefs"]:
                    if model_ref not in model_defs:
                        continue
                    resolved_params, _ = resolve_param_values(model_defs[model_ref]["params"], numeric_subckt_context)
                    resolved_model_defs[model_ref] = {
                        "kind": model_defs[model_ref]["kind"],
                        "params": model_defs[model_ref]["params"],
                        "resolvedParams": resolved_params,
                    }
                models[subckt_name] = {
                    "source": {
                        "file": include_ref.file_name,
                        "topSection": include_ref.section,
                        "implementationSection": nested.section,
                    },
                    "cornerParams": resolved_corner_params,
                    "subckt": {
                        **subckt_info,
                        "defaultParams": resolved_defaults,
                    },
                    "modelDefinitions": resolved_model_defs,
                }
                models[subckt_name]["soaHints"] = collect_soa_hints(
                    subckt_name,
                    subckt_info,
                    models[subckt_name]["modelDefinitions"],
                )
            for model_name, model_info in model_defs.items():
                if model_name in models:
                    continue
                resolved_params, _ = resolve_param_values(model_info["params"], numeric_corner_context)
                models[model_name] = {
                    "source": {
                        "file": include_ref.file_name,
                        "topSection": include_ref.section,
                        "implementationSection": nested.section,
                    },
                    "cornerParams": resolved_corner_params,
                    "subckt": {"ports": [], "defaultParams": {}, "modelRefs": [model_name]},
                    "modelDefinitions": {
                        model_name: {
                            "kind": model_info["kind"],
                            "params": model_info["params"],
                            "resolvedParams": resolved_params,
                        },
                    },
                }
                models[model_name]["soaHints"] = collect_soa_hints(
                    model_name,
                    models[model_name]["subckt"],
                    models[model_name]["modelDefinitions"],
                )
    return models


def build_output(cells: list[dict[str, Any]], model_catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mapped_cells = []
    unresolved_models = set()
    for cell in sorted(cells, key=lambda item: item["cell"]):
        preferred_model = cell["model"] or cell["simModel"]
        if preferred_model not in model_catalog and cell["simModel"] in model_catalog:
            preferred_model = cell["simModel"]
        entry = {
            "cell": cell["cell"],
            "model": preferred_model,
            "cdfModel": cell["model"],
            "cdfSimModel": cell["simModel"],
            "cdfDefaults": cell["cdfDefaults"],
            "cdfMeta": cell["cdfMeta"],
        }
        if preferred_model in model_catalog:
            entry["source"] = model_catalog[preferred_model]["source"]
            entry["soaHints"] = model_catalog[preferred_model]["soaHints"]
        elif preferred_model:
            unresolved_models.add(preferred_model)
        mapped_cells.append(entry)

    filtered_models = {
        model_name: model_catalog[model_name]
        for model_name in sorted({(cell["model"] or cell["simModel"]) for cell in cells if (cell["model"] or cell["simModel"])})
        if model_name in model_catalog
    }
    return {
        "pdk": "gpdk090",
        "corner": TYPICAL_TOP_SECTION,
        "sourceDir": str(SOURCE_DIR),
        "cells": mapped_cells,
        "models": filtered_models,
        "unresolvedModels": sorted(unresolved_models),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract gpdk090 Typical-corner SOA specs to JSON")
    parser.add_argument("--workspace-id", default="default")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/home/cloud/projects/skillbridge/build/gpdk090_typical_soa_specs.json"),
    )
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = Path("/tmp/gpdk090_spectre_extract")
    ws = Workspace.open(None if args.workspace_id == "default" else args.workspace_id)
    try:
        file_contents = fetch_required_files(ws, temp_dir)
        cells = get_gpdk090_cells(ws)
    finally:
        ws.close()

    model_catalog = build_model_catalog(file_contents)
    output = build_output(cells, model_catalog)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True))
    print(args.out)


if __name__ == "__main__":
    main()
