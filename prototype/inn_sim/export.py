"""Export the tuned numbers and dealt test runs for the Godot game."""
import json
from pathlib import Path

from inn_sim.params import DEFAULT_PARAMS
from inn_sim.report import WHOLE_PARAMS

_ALSO_WHOLE = {"days", "travelers_min", "travelers_max"}


def params_for_export(params: dict[str, float]) -> dict[str, int | float]:
    """Params in DEFAULT_PARAMS order; whole-number params as ints so GDScript gets clean values."""
    out: dict[str, int | float] = {}
    for name in DEFAULT_PARAMS:
        value = params[name]
        out[name] = int(value) if name in WHOLE_PARAMS | _ALSO_WHOLE else float(value)
    return out


def export_params(params: dict[str, float], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(params_for_export(params), indent=2) + "\n")
