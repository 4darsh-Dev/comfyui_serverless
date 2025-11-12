import os, requests, gdown
from pathlib import Path

COMFY_DIR = Path("/workspace/ComfyUI")
MODEL_DIR = COMFY_DIR / "models"

os.makedirs(MODEL_DIR / "checkpoints", exist_ok=True)
os.makedirs(MODEL_DIR / "loras", exist_ok=True)
os.makedirs(MODEL_DIR / "vae", exist_ok=True)

# Example: Download SDXL
os.system("wget -q https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors -O models/checkpoints/sd_xl_base_1.0.safetensors")

# Example: Download VAE
os.system("wget -q https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -O models/vae/sdxl_vae.safetensors")

# Example: Download your LoRA
gdown.download("https://drive.google.com/uc?id=1rH5E5DxUx4AcSoL4sUC550oEsVG6xNDY", "models/loras/avatar_lora.safetensors", quiet=False)

print("✅ All models ready!")
