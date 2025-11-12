
import os
import sys
from pathlib import Path
import requests
import gdown
from tqdm import tqdm

COMFY_DIR = Path("/workspace/ComfyUI")

def download_file(url, destination, description="Downloading"):
    """Download file with progress bar"""
    destination = Path(destination)
    
    if destination.exists():
        print(f"✓ {destination.name} already exists")
        return True
    
    print(f"📥 {description}...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, 'wb') as f, tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=destination.name
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))
        
        print(f"✅ Downloaded {destination.name}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {destination.name}: {e}")
        return False

def download_all_models():
    """Download all required models"""
    
    models = {
        # SDXL Base Model
        "sdxl_base": {
            "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
            "path": COMFY_DIR / "models/checkpoints/sd_xl_base_1.0.safetensors",
            "desc": "SDXL Base Model (6.9GB)"
        },
        
        # SDXL VAE
        "sdxl_vae": {
            "url": "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors",
            "path": COMFY_DIR / "models/vae/sdxl_vae.safetensors",
            "desc": "SDXL VAE"
        },
        
        # ControlNet OpenPose
        "controlnet_openpose": {
            "url": "https://huggingface.co/thibaud/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors",
            "path": COMFY_DIR / "models/controlnet/controlnet-openpose-sdxl-1.0.safetensors",
            "desc": "ControlNet OpenPose"
        },
        
        # ControlNet Canny
        "controlnet_canny": {
            "url": "https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors",
            "path": COMFY_DIR / "models/controlnet/controlnet-canny-sdxl-1.0.safetensors",
            "desc": "ControlNet Canny"
        },
        
        # ControlNet Depth
        "controlnet_depth": {
            "url": "https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors",
            "path": COMFY_DIR / "models/controlnet/controlnet-depth-sdxl-1.0.safetensors",
            "desc": "ControlNet Depth"
        }
    }
    
    print("=" * 60)
    print("📦 DOWNLOADING MODELS")
    print("=" * 60)
    
    success_count = 0
    for name, info in models.items():
        if download_file(info["url"], info["path"], info["desc"]):
            success_count += 1
    
    # Download LoRA from Google Drive
    print("\n📥 Downloading custom LoRA...")
    lora_path = COMFY_DIR / "models/loras/avatar_lora.safetensors"
    
    if not lora_path.exists():
        try:
            GDRIVE_FILE_ID = "1rH5E5DxUx4AcSoL4sUC550oEsVG6xNDY"
            url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"
            gdown.download(url, str(lora_path), quiet=False)
            
            if lora_path.exists():
                file_size = lora_path.stat().st_size / (1024 * 1024)
                print(f"✅ LoRA downloaded ({file_size:.2f} MB)")
                success_count += 1
        except Exception as e:
            print(f"❌ Failed to download LoRA: {e}")
    else:
        print("✓ LoRA already exists")
        success_count += 1
    
    # Download workflow JSON
    print("\n📥 Downloading workflow...")
    workflow_url = "https://iykcyciztwpljrqjwxza.supabase.co/storage/v1/object/public/payments/avatar_ai.json"
    workflow_path = COMFY_DIR / "user/default/workflows/avatar_ai.json"
    
    if download_file(workflow_url, workflow_path, "Workflow JSON"):
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Downloaded {success_count}/{len(models) + 2} files successfully")
    print("=" * 60)
    
    return success_count == len(models) + 2

if __name__ == "__main__":
    success = download_all_models()
    sys.exit(0 if success else 1)