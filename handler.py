
"""
RunPod Serverless Handler for Avatar Generation
Supports multiple image formats with quality control
"""

import runpod
import os
import sys
import json
import base64
import requests
import subprocess
import time
import signal
from pathlib import Path
from io import BytesIO
from PIL import Image

# Configuration
COMFY_DIR = Path("/workspace/ComfyUI")
COMFY_PORT = 8188
COMFY_URL = f"http://127.0.0.1:{COMFY_PORT}"

# Global ComfyUI process
comfy_process = None

def start_comfyui():
    """Start ComfyUI server in background"""
    global comfy_process
    
    if comfy_process is not None:
        return True
    
    print("🚀 Starting ComfyUI server...")
    os.chdir(COMFY_DIR)
    
    comfy_process = subprocess.Popen(
        [sys.executable, "main.py", "--listen", "0.0.0.0", "--port", str(COMFY_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{COMFY_URL}/system_stats")
            if response.status_code == 200:
                print("✅ ComfyUI server started successfully")
                return True
        except:
            time.sleep(1)
    
    print("❌ Failed to start ComfyUI server")
    return False

def convert_image_format(image_data, output_format="jpg", quality=95):
    """
    Convert image to specified format with quality control
    
    Args:
        image_data: Raw image bytes
        output_format: "jpg", "png", or "webp"
        quality: Quality setting (1-100 for JPG/WebP, PNG uses compression level)
    
    Returns:
        Converted image bytes
    """
    try:
        # Load image
        img = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB for JPG (if needed)
        if output_format.lower() in ["jpg", "jpeg"] and img.mode in ["RGBA", "LA", "P"]:
            # Create white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        
        # Save to BytesIO with specified format
        output = BytesIO()
        
        if output_format.lower() in ["jpg", "jpeg"]:
            img.save(
                output,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True  # Progressive JPG for better loading
            )
        elif output_format.lower() == "png":
            # PNG compression level (0-9, lower = larger file but faster)
            compress_level = int((100 - quality) / 11)  # Map quality to compression
            img.save(
                output,
                format="PNG",
                compress_level=min(9, max(0, compress_level)),
                optimize=True
            )
        elif output_format.lower() == "webp":
            img.save(
                output,
                format="WEBP",
                quality=quality,
                method=6  # Max compression effort
            )
        else:
            # Default to PNG
            img.save(output, format="PNG", optimize=True)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        print(f"❌ Error converting image: {e}")
        return image_data  # Return original if conversion fails

def get_file_size_mb(data):
    """Get size of data in MB"""
    return len(data) / (1024 * 1024)

def queue_prompt(workflow_json):
    """Queue a prompt in ComfyUI"""
    try:
        response = requests.post(
            f"{COMFY_URL}/prompt",
            json={"prompt": workflow_json}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to queue prompt: {response.text}"}
    except Exception as e:
        return {"error": f"Exception queuing prompt: {str(e)}"}

def get_image(filename, subfolder, folder_type):
    """Get generated image from ComfyUI"""
    try:
        response = requests.get(
            f"{COMFY_URL}/view",
            params={
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
        )
        
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        print(f"Error getting image: {e}")
        return None

def wait_for_completion(prompt_id, timeout=300):
    """Wait for prompt to complete"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    if "outputs" in prompt_history:
                        return prompt_history["outputs"]
                    
                    if "status" in prompt_history:
                        status = prompt_history["status"]
                        if status.get("completed", False):
                            return prompt_history.get("outputs", {})
                        if status.get("status_str") == "error":
                            return {"error": status.get("messages", ["Unknown error"])}
            
            time.sleep(2)
        except Exception as e:
            print(f"Error checking completion: {e}")
            time.sleep(2)
    
    return {"error": "Timeout waiting for completion"}

def create_workflow(job_input):
    """Create ComfyUI workflow from job input"""
    
    # Load base workflow if exists
    workflow_path = COMFY_DIR / "user/default/workflows/avatar_ai.json"
    
    if workflow_path.exists():
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
    else:
        workflow = create_basic_workflow()
    
    # Extract parameters
    positive_prompt = job_input.get("positive_prompt", "avachar, professional photo, high quality")
    negative_prompt = job_input.get("negative_prompt", "ugly, deformed, blurry, low quality")
    steps = job_input.get("steps", 30)
    cfg = job_input.get("cfg_scale", 8.0)
    width = job_input.get("width", 1024)
    height = job_input.get("height", 1024)
    seed = job_input.get("seed", -1)
    lora_strength = job_input.get("lora_strength", 0.8)
    
    # Update workflow nodes (customize based on your workflow structure)
    # This is a simplified example - adapt to your actual workflow
    for node_id, node in workflow.items():
        if node.get("class_type") == "CLIPTextEncode":
            if "positive" in node.get("_meta", {}).get("title", "").lower():
                node["inputs"]["text"] = positive_prompt
            elif "negative" in node.get("_meta", {}).get("title", "").lower():
                node["inputs"]["text"] = negative_prompt
        
        elif node.get("class_type") == "KSampler":
            node["inputs"]["steps"] = steps
            node["inputs"]["cfg"] = cfg
            node["inputs"]["seed"] = seed if seed != -1 else int(time.time())
        
        elif node.get("class_type") == "EmptyLatentImage":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
        
        elif node.get("class_type") == "LoraLoader":
            node["inputs"]["strength_model"] = lora_strength
            node["inputs"]["strength_clip"] = lora_strength
    
    return workflow

def create_basic_workflow():
    """Create a basic SDXL + LoRA workflow"""
    
    return {
        "3": {
            "inputs": {
                "seed": 0,
                "steps": 30,
                "cfg": 8.0,
                "sampler_name": "dpmpp_2m_karras",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["10", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "5": {
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": "avachar, professional photo, high quality, detailed face",
                "clip": ["10", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Positive)"}
        },
        "7": {
            "inputs": {
                "text": "ugly, deformed, blurry, low quality",
                "clip": ["10", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Negative)"}
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 0]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "avatar",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        },
        "10": {
            "inputs": {
                "lora_name": "avatar_lora.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.8,
                "model": ["11", 0],
                "clip": ["11", 1]
            },
            "class_type": "LoraLoader"
        },
        "11": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "4": {
            "inputs": {
                "vae_name": "sdxl_vae.safetensors"
            },
            "class_type": "VAELoader"
        }
    }

def handler(job):
    """
    RunPod serverless handler with image format control
    
    Expected input:
    {
        "positive_prompt": "avachar, professional photo...",
        "negative_prompt": "ugly, deformed...",
        "steps": 30,
        "cfg_scale": 8.0,
        "width": 1024,
        "height": 1024,
        "seed": -1,
        "lora_strength": 0.8,
        "num_images": 1,
        
        # NEW: Image format options
        "output_format": "jpg",  # "jpg", "png", or "webp"
        "output_quality": 95,    # 1-100 (higher = better quality, larger file)
        "return_base64": true,   # Return base64 or URL
        "return_metadata": true  # Include file size, dimensions, etc.
    }
    """
    
    job_input = job["input"]
    
    # Ensure ComfyUI is running
    if not start_comfyui():
        return {"error": "Failed to start ComfyUI server"}
    
    try:
        # Get output format settings
        output_format = job_input.get("output_format", "jpg").lower()
        output_quality = job_input.get("output_quality", 95)
        return_base64 = job_input.get("return_base64", True)
        return_metadata = job_input.get("return_metadata", True)
        
        # Validate format
        if output_format not in ["jpg", "jpeg", "png", "webp"]:
            return {"error": f"Invalid output_format: {output_format}. Use 'jpg', 'png', or 'webp'"}
        
        # Validate quality
        if not 1 <= output_quality <= 100:
            return {"error": f"Invalid output_quality: {output_quality}. Use 1-100"}
        
        # Create workflow
        workflow = create_workflow(job_input)
        
        # Queue prompt
        queue_result = queue_prompt(workflow)
        
        if "error" in queue_result:
            return queue_result
        
        prompt_id = queue_result.get("prompt_id")
        
        if not prompt_id:
            return {"error": "No prompt_id returned"}
        
        # Wait for completion
        outputs = wait_for_completion(prompt_id)
        
        if "error" in outputs:
            return outputs
        
        # Process generated images
        images = []
        
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for image_info in node_output["images"]:
                    # Get original image
                    original_data = get_image(
                        image_info["filename"],
                        image_info.get("subfolder", ""),
                        image_info.get("type", "output")
                    )
                    
                    if original_data:
                        # Convert to desired format
                        converted_data = convert_image_format(
                            original_data,
                            output_format,
                            output_quality
                        )
                        
                        # Get metadata
                        img = Image.open(BytesIO(converted_data))
                        
                        image_result = {
                            "filename": f"{Path(image_info['filename']).stem}.{output_format}"
                        }
                        
                        if return_base64:
                            # Return base64 encoded image
                            b64_image = base64.b64encode(converted_data).decode('utf-8')
                            image_result["image"] = b64_image
                            image_result["image_data_url"] = f"data:image/{output_format};base64,{b64_image}"
                        
                        if return_metadata:
                            image_result["metadata"] = {
                                "width": img.width,
                                "height": img.height,
                                "format": output_format.upper(),
                                "mode": img.mode,
                                "size_bytes": len(converted_data),
                                "size_mb": round(get_file_size_mb(converted_data), 2),
                                "quality": output_quality
                            }
                        
                        images.append(image_result)
        
        return {
            "status": "success",
            "images": images,
            "prompt_id": prompt_id,
            "settings": {
                "format": output_format,
                "quality": output_quality,
                "total_images": len(images)
            }
        }
        
    except Exception as e:
        return {"error": f"Handler exception: {str(e)}"}

# Initialize on container start
print("=" * 60)
print("🤖 RunPod Avatar Generation Handler v2.0")
print("📸 Supports: JPG, PNG, WebP with quality control")
print("=" * 60)

# Download models if needed
if not (COMFY_DIR / "models/checkpoints/sd_xl_base_1.0.safetensors").exists():
    print("📥 Models not found, downloading...")
    import download_models
    download_models.download_all_models()

# Start RunPod serverless
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})