"""Generate the game's art from assets.json through a running ComfyUI.

Every image is reproducible: its prompt, seed, size and model are in assets.json, and the
generator writes provenance.json next to the images (used for Steam's AI-content disclosure).

Usage (ComfyUI running on the default port):
    python3 tools/comfyui/generate_assets.py                # only images that don't exist yet
    python3 tools/comfyui/generate_assets.py --force        # regenerate everything
    python3 tools/comfyui/generate_assets.py --only merchant,bram --force
"""
import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from comfy_client import ComfyError, build_workflow, generate

HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Asset:
    id: str
    prompt: str
    negative: str
    seed: int
    width: int
    height: int
    steps: int
    cfg: float
    checkpoint: str


def load_assets(path: Path) -> list[Asset]:
    data = json.loads(path.read_text())
    d = data["defaults"]
    return [Asset(a["id"], f"{a['prompt']}, {data['style']}", data["negative"], a["seed"], a["width"], a["height"],
                  a.get("steps", d["steps"]), a.get("cfg", d["cfg"]), data["checkpoint"])
            for a in data["assets"]]


def plan(assets: list[Asset], out_dir: Path, force: bool, only: set[str] | None) -> list[Asset]:
    chosen = [a for a in assets if only is None or a.id in only]
    return [a for a in chosen if force or not (out_dir / f"{a.id}.png").exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--assets", default=str(HERE / "assets.json"))
    parser.add_argument("--out", default=str(HERE.parents[1] / "game" / "art"))
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--force", action="store_true", help="regenerate images that already exist")
    parser.add_argument("--only", help="comma-separated asset ids")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = load_assets(Path(args.assets))
    only = set(args.only.split(",")) if args.only else None
    provenance_path = out_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {}

    for asset in plan(assets, out_dir, args.force, only):
        print(f"generating {asset.id} ({asset.width}x{asset.height}, seed {asset.seed})...", flush=True)
        workflow = build_workflow(asset.prompt, asset.negative, asset.seed, asset.width, asset.height,
                                  asset.steps, asset.cfg, asset.checkpoint, prefix=f"crossroads_{asset.id}")
        try:
            png = generate(args.server, workflow)
        except (ComfyError, OSError) as e:
            print(f"error: {asset.id}: {e}", file=sys.stderr)
            return 1
        (out_dir / f"{asset.id}.png").write_bytes(png)
        provenance[asset.id] = {**asdict(asset), "generated": date.today().isoformat(), "tool": "ComfyUI"}
        provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
