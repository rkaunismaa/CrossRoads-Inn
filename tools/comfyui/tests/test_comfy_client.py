import json

import pytest

from comfy_client import ComfyError, build_workflow, image_from_history
from generate_assets import Asset, load_assets, plan


def test_workflow_carries_prompt_seed_and_size():
    wf = build_workflow("a merchant", "blurry", seed=42, width=832, height=1216, steps=30, cfg=6.5,
                        checkpoint="sd_xl_base_1.0.safetensors", prefix="merchant")
    by_type = {node["class_type"]: node for node in wf.values()}
    assert by_type["CheckpointLoaderSimple"]["inputs"]["ckpt_name"] == "sd_xl_base_1.0.safetensors"
    assert by_type["KSampler"]["inputs"]["seed"] == 42
    assert by_type["KSampler"]["inputs"]["steps"] == 30
    assert by_type["EmptyLatentImage"]["inputs"]["width"] == 832
    assert by_type["EmptyLatentImage"]["inputs"]["height"] == 1216
    assert by_type["SaveImage"]["inputs"]["filename_prefix"] == "merchant"
    texts = [n["inputs"]["text"] for n in wf.values() if n["class_type"] == "CLIPTextEncode"]
    assert texts == ["a merchant", "blurry"]


def test_workflow_links_point_at_real_nodes():
    wf = build_workflow("p", "n", 1, 64, 64, 1, 1.0, "x.safetensors", "t")
    for node in wf.values():
        for value in node["inputs"].values():
            if isinstance(value, list):
                assert value[0] in wf
    json.dumps(wf)  # must be plain JSON for the API


def test_image_from_history_finds_the_output():
    history = {"abc": {"outputs": {"9": {"images": [{"filename": "m_00001_.png", "subfolder": "", "type": "output"}]}}}}
    assert image_from_history(history, "abc") == {"filename": "m_00001_.png", "subfolder": "", "type": "output"}


def test_image_from_history_reports_errors():
    history = {"abc": {"outputs": {}, "status": {"status_str": "error", "messages": [["execution_error", {"exception_message": "OOM"}]]}}}
    with pytest.raises(ComfyError, match="OOM"):
        image_from_history(history, "abc")


def test_load_assets_combines_style(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({
        "checkpoint": "sd_xl_base_1.0.safetensors", "style": "painterly", "negative": "text",
        "defaults": {"steps": 30, "cfg": 6.5},
        "assets": [{"id": "merchant", "prompt": "a merchant", "seed": 7, "width": 832, "height": 1216}],
    }))
    [a] = load_assets(tmp_path / "a.json")
    assert a == Asset("merchant", "a merchant, painterly", "text", 7, 832, 1216, 30, 6.5, "sd_xl_base_1.0.safetensors")


def test_plan_skips_existing_unless_forced(tmp_path):
    assets = [Asset("a", "p", "n", 1, 64, 64, 1, 1.0, "x"), Asset("b", "p", "n", 2, 64, 64, 1, 1.0, "x")]
    (tmp_path / "a.png").write_bytes(b"x")
    assert [a.id for a in plan(assets, tmp_path, force=False, only=None)] == ["b"]
    assert [a.id for a in plan(assets, tmp_path, force=True, only=None)] == ["a", "b"]
    assert [a.id for a in plan(assets, tmp_path, force=True, only={"b"})] == ["b"]
