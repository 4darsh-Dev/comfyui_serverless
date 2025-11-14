
import os
import sys
from pathlib import Path
import requests
import gdown
from tqdm import tqdm

COMFY_DIR = Path("/workspace/ComfyUI")

def download_file(url, destination, description="Downloading"):
    """Download file with progress bar and retry logic"""
    destination = Path(destination)
    
    if destination.exists():
        size_mb = destination.stat().st_size / (1024 * 1024)
        print(f"✓ {destination.name} already exists ({size_mb:.1f} MB)")
        return True
    
    print(f"📥 {description}...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()  # Raise exception for bad status codes
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(destination, 'wb') as f, tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=destination.name
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            # Verify file was written
            if destination.exists() and destination.stat().st_size > 0:
                size_mb = destination.stat().st_size / (1024 * 1024)
                print(f"✅ Downloaded {destination.name} ({size_mb:.1f} MB)")
                return True
            else:
                print(f"⚠️ File appears to be empty or missing after download")
                if destination.exists():
                    destination.unlink()
                    
        except requests.exceptions.Timeout:
            print(f"⚠️ Download timeout on attempt {attempt + 1}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Download error on attempt {attempt + 1}: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {type(e).__name__}: {e}")
            
        if attempt < max_retries - 1:
            print("  Retrying in 5 seconds...")
            import time
            time.sleep(5)
    
    print(f"❌ Failed to download {destination.name} after {max_retries} attempts")
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
            print(f"  Downloading from Google Drive (ID: {GDRIVE_FILE_ID})...")
            gdown.download(url, str(lora_path), quiet=False)
            
            if lora_path.exists() and lora_path.stat().st_size > 0:
                file_size = lora_path.stat().st_size / (1024 * 1024)
                print(f"✅ LoRA downloaded ({file_size:.2f} MB)")
                success_count += 1
            else:
                print(f"❌ LoRA download failed or file is empty")
                if lora_path.exists():
                    lora_path.unlink()
        except Exception as e:
            print(f"❌ Failed to download LoRA: {type(e).__name__}: {e}")
    else:
        file_size = lora_path.stat().st_size / (1024 * 1024)
        print(f"✓ LoRA already exists ({file_size:.2f} MB)")
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