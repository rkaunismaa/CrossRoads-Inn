"""Minimal ComfyUI API client: build an SDXL text-to-image job, queue it, and fetch the image.

Standard library only. ComfyUI must be running (see README in this folder).
"""
import json
import time
import urllib.parse
import urllib.request
import uuid


class ComfyError(RuntimeError):
    """ComfyUI rejected a job or reported an error while running it."""


def build_workflow(prompt: str, negative: str, seed: int, width: int, height: int, steps: int, cfg: float,
                   checkpoint: str, prefix: str) -> dict:
    """A ComfyUI API-format graph: checkpoint -> text encodes -> sampler -> decode -> save."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": prefix}},
    }


def image_from_history(history: dict, prompt_id: str) -> dict:
    """The first saved image of a finished job, or ComfyError with ComfyUI's message."""
    entry = history[prompt_id]
    for output in entry.get("outputs", {}).values():
        for image in output.get("images", []):
            return image
    messages = entry.get("status", {}).get("messages", [])
    detail = "; ".join(str(m[1].get("exception_message", m[0])) for m in messages if m[0] == "execution_error")
    raise ComfyError(f"job {prompt_id} produced no image" + (f": {detail}" if detail else ""))


def _get(server: str, path: str) -> bytes:
    with urllib.request.urlopen(server + path, timeout=30) as response:
        return response.read()


def queue(server: str, workflow: dict) -> str:
    body = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode()
    request = urllib.request.Request(server + "/prompt", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())["prompt_id"]
    except urllib.error.HTTPError as e:
        raise ComfyError(f"ComfyUI rejected the job: {e.read().decode(errors='replace')}") from None


def generate(server: str, workflow: dict, timeout: float = 600.0) -> bytes:
    """Queue a job, wait for it, and return the PNG bytes."""
    prompt_id = queue(server, workflow)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = json.loads(_get(server, f"/history/{prompt_id}"))
        if prompt_id in history:
            image = image_from_history(history, prompt_id)
            return _get(server, "/view?" + urllib.parse.urlencode(image))
        time.sleep(1.0)
    raise ComfyError(f"job {prompt_id} did not finish within {timeout:.0f}s")
