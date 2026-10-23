# Art generation (ComfyUI)

The game's art in `game/art/` is generated locally with [ComfyUI](https://github.com/comfyanonymous/ComfyUI) and SDXL. Every image can be reproduced: its prompt, seed, size and model are in `assets.json`, and each run records them in `game/art/provenance.json` for Steam's AI-content disclosure.

## One-time setup (outside the repo)

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI
cd ~/ComfyUI
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv/bin/python -r requirements.txt
curl -L -o models/checkpoints/sd_xl_base_1.0.safetensors \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

The model is SDXL base 1.0 by Stability AI, licensed under CreativeML Open RAIL++-M, which allows commercial use.

## Generate

```bash
cd ~/ComfyUI && CUDA_VISIBLE_DEVICES=0 .venv/bin/python main.py --listen 127.0.0.1 --port 8188 &   # GPU 0 = RTX 4090
python3 tools/comfyui/generate_assets.py                        # only images that don't exist yet
python3 tools/comfyui/generate_assets.py --only bram --force    # redo one image
```

To change an image, edit its prompt or seed in `assets.json` and regenerate it with `--force`. Then run `tools/run-tests.sh`; the scene tests check that the art loads.

## Tests

```bash
cd tools/comfyui && python3 -m pytest -q
```
