"""Load and validate the data files in data/ (YAML catalogues and simulated demand CSVs)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SCHEMA_DIR = DATA_DIR / "schemas"

CATALOGUES = {
    "network": "network.yaml",
    "policy": "policy.yaml",
    "scenarios": "scenarios.yaml",
}

DEMAND_COLUMNS = [
    "slot",
    "time",
    "workload_id",
    "org",
    "tier",
    "data_class",
    "task",
    "requests",
    "tokens_in",
    "tokens_out",
    "ref_gpu_seconds",
    "description",
]
_INT_COLUMNS = {"slot", "requests", "tokens_in", "tokens_out"}
_FLOAT_COLUMNS = {"ref_gpu_seconds"}


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_schema(name: str) -> dict:
    with (SCHEMA_DIR / f"{name}.schema.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def validate(name: str, data: Any) -> list[str]:
    """Return a list of readable schema errors (empty when valid)."""
    validator = Draft202012Validator(load_schema(name))
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors]


def load(name: str, path: Path | None = None) -> Any:
    """Load a catalogue by name and raise ValueError if it does not match its schema."""
    data = load_yaml(path or DATA_DIR / CATALOGUES[name])
    errors = validate(name, data)
    if errors:
        raise ValueError(f"{name} is invalid:\n  " + "\n  ".join(errors))
    return data


def read_demand(path: Path) -> list[dict]:
    """Read a demand CSV, convert types and validate every row against demand-row.schema.json."""
    if not path.is_absolute() and not path.exists():
        path = DATA_DIR / path
    validator = Draft202012Validator(load_schema("demand-row"))
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != DEMAND_COLUMNS:
            raise ValueError(f"{path.name}: expected columns {DEMAND_COLUMNS}, got {reader.fieldnames}")
        for line_no, raw in enumerate(reader, start=2):
            row: dict[str, Any] = {}
            for key, value in raw.items():
                if key in _INT_COLUMNS:
                    row[key] = int(value)
                elif key in _FLOAT_COLUMNS:
                    row[key] = float(value)
                else:
                    row[key] = value
            errors = list(validator.iter_errors(row))
            if errors:
                raise ValueError(f"{path.name} line {line_no}: {errors[0].message}")
            rows.append(row)
    return rows


def write_demand(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=DEMAND_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
