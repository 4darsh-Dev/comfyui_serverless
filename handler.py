
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
    """Start ComfyUI server in background with detailed logging"""
    global comfy_process
    
    if comfy_process is not None:
        print("ℹ️ ComfyUI process already running, checking health...")
        try:
            response = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                print("✅ Existing ComfyUI server is healthy")
                return True
            else:
                print("⚠️ Existing server unhealthy, restarting...")
                comfy_process.terminate()
                comfy_process.wait(timeout=10)
                comfy_process = None
        except Exception as e:
            print(f"⚠️ Error checking existing server: {e}, restarting...")
            try:
                comfy_process.terminate()
                comfy_process.wait(timeout=10)
            except:
                pass
            comfy_process = None
    
    print("🚀 Starting ComfyUI server...")
    print(f"📂 Working directory: {COMFY_DIR}")
    print(f"🔧 Python executable: {sys.executable}")
    print(f"🌐 Server URL: {COMFY_URL}")
    
    # Check if ComfyUI directory exists
    if not COMFY_DIR.exists():
        print(f"❌ ComfyUI directory not found: {COMFY_DIR}")
        return False
    
    # Check if main.py exists
    main_py = COMFY_DIR / "main.py"
    if not main_py.exists():
        print(f"❌ ComfyUI main.py not found: {main_py}")
        return False
    
    print("✅ ComfyUI files verified")
    
    try:
        os.chdir(COMFY_DIR)
        print(f"✅ Changed directory to: {os.getcwd()}")
        
        # Start ComfyUI process; avoid piping large tqdm output to Python to prevent BrokenPipeError.
        # Use inherited stdout/stderr so progress bars can write directly.
        comfy_process = subprocess.Popen(
            [sys.executable, "-u", "main.py", "--listen", "0.0.0.0", "--port", str(COMFY_PORT)],
            stdout=None,
            stderr=None,
            bufsize=0
        )
        
        print(f"✅ ComfyUI process started (PID: {comfy_process.pid})")
        
        # Wait for server to start with detailed logging
        max_retries = 60  # Increased to 60 seconds
        print(f"⏳ Waiting for server to start (max {max_retries} seconds)...")
        
        for i in range(max_retries):
            # Check if process is still running
            if comfy_process.poll() is not None:
                print(f"❌ ComfyUI process terminated unexpectedly (exit code: {comfy_process.returncode})")
                print("📋 Process output:")
                try:
                    output, _ = comfy_process.communicate(timeout=1)
                    print(output)
                except:
                    pass
                return False
            
            try:
                response = requests.get(f"{COMFY_URL}/system_stats", timeout=2)
                if response.status_code == 200:
                    print(f"✅ ComfyUI server started successfully after {i+1} seconds")
                    return True
            except requests.exceptions.ConnectionError:
                # Expected while server is starting
                pass
            except Exception as e:
                if i % 10 == 0:  # Log every 10 seconds
                    print(f"⏳ Still waiting... ({i+1}/{max_retries}s) - {type(e).__name__}")
            
            time.sleep(1)
        
        print(f"❌ Failed to start ComfyUI server after {max_retries} seconds")
        
        # Try to get process output for debugging
        if comfy_process and comfy_process.poll() is None:
            print("📋 Attempting to retrieve process output...")
            try:
                comfy_process.terminate()
                output, _ = comfy_process.communicate(timeout=5)
                print("Process output:")
                print(output[:2000])  # Print first 2000 chars
            except Exception as e:
                print(f"⚠️ Could not retrieve process output: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ Exception starting ComfyUI: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
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

def save_image_to_disk(image_data, filename, output_dir="/workspace/outputs"):
    """
    Save image to disk for persistence
    
    Args:
        image_data: Raw image bytes
        filename: Output filename
        output_dir: Directory to save images
        
    Returns:
        Path to saved file or None on error
    """
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / filename
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        size_mb = len(image_data) / (1024 * 1024)
        print(f"💾 Saved image: {file_path} ({size_mb:.2f} MB)")
        return str(file_path)
    except Exception as e:
        print(f"❌ Error saving image: {type(e).__name__}: {e}")
        return None

def queue_prompt(workflow_json):
    """Queue a prompt in ComfyUI with detailed error logging"""
    try:
        print("📤 Queueing prompt to ComfyUI...")
        response = requests.post(
            f"{COMFY_URL}/prompt",
            json={"prompt": workflow_json},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prompt queued successfully: {result.get('prompt_id', 'unknown')}")
            return result
        else:
            error_msg = f"Failed to queue prompt (HTTP {response.status_code}): {response.text}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    except requests.exceptions.Timeout:
        error_msg = "Timeout queuing prompt (>30s)"
        print(f"❌ {error_msg}")
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Exception queuing prompt: {type(e).__name__}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(traceback.format_exc())
        return {"error": error_msg}

def get_image(filename, subfolder, folder_type):
    """Get generated image from ComfyUI with error logging"""
    try:
        print(f"📥 Fetching image: {filename} (subfolder: {subfolder}, type: {folder_type})")
        response = requests.get(
            f"{COMFY_URL}/view",
            params={
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            },
            timeout=30
        )
        
        if response.status_code == 200:
            size_mb = len(response.content) / (1024 * 1024)
            print(f"✅ Image fetched successfully ({size_mb:.2f} MB)")
            return response.content
        else:
            print(f"❌ Failed to fetch image (HTTP {response.status_code}): {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting image: {type(e).__name__}: {e}")
        return None

def wait_for_completion(prompt_id, timeout=300):
    """Wait for prompt to complete with detailed logging"""
    start_time = time.time()
    print(f"⏳ Waiting for prompt completion (ID: {prompt_id}, timeout: {timeout}s)...")
    
    last_status = None
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        
        try:
            response = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
            
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    # Check for outputs first
                    if "outputs" in prompt_history:
                        outputs = prompt_history["outputs"]
                        if outputs:  # Make sure outputs is not empty
                            print(f"✅ Prompt completed after {elapsed}s")
                            return outputs
                    
                    # Check status
                    if "status" in prompt_history:
                        status = prompt_history["status"]
                        status_str = status.get("status_str", "unknown")
                        
                        # Log status changes
                        if status_str != last_status:
                            print(f"📊 Status update: {status_str} (after {elapsed}s)")
                            last_status = status_str
                        
                        if status.get("completed", False):
                            outputs = prompt_history.get("outputs", {})
                            if outputs:
                                print(f"✅ Prompt completed after {elapsed}s")
                                return outputs
                            else:
                                print(f"⚠️ Prompt marked complete but no outputs found")
                        
                        if status_str == "error":
                            error_msgs = status.get("messages", ["Unknown error"])
                            print(f"❌ Prompt failed with error: {error_msgs}")
                            return {"error": error_msgs}
                else:
                    if check_count % 5 == 1:  # Log every 5 checks (~10 seconds)
                        print(f"⏳ Waiting for prompt to appear in history... ({elapsed}s)")
            else:
                print(f"⚠️ Failed to check history (HTTP {response.status_code})")
            
            time.sleep(2)
            
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout checking completion status at {elapsed}s")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error checking completion: {type(e).__name__}: {e}")
            time.sleep(2)
    
    print(f"❌ Timeout waiting for completion after {timeout}s")
    return {"error": f"Timeout waiting for completion after {timeout}s"}

def create_workflow(job_input):
    """
    Create optimized ComfyUI workflow from job input
    Optimized for quality and cost efficiency
    """
    
    print("🔨 Building workflow from input parameters...")
    
    # Load base workflow if exists
    workflow_path = COMFY_DIR / "user/default/workflows/avatar_ai.json"
    
    if workflow_path.exists():
        print(f"📂 Loading workflow from: {workflow_path}")
        try:
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
                print("✅ Workflow loaded successfully")
        except Exception as e:
            print(f"⚠️ Failed to load workflow: {e}, using default")
            workflow = create_basic_workflow()
    else:
        print("📝 Creating basic workflow (no custom workflow found)")
        workflow = create_basic_workflow()
    
    # Normalize workflow structure: some exported workflows use a top-level {"nodes": [...]} list
    # or include metadata keys whose values are simple strings/numbers. We only mutate node dicts.
    if isinstance(workflow, dict) and "nodes" in workflow and isinstance(workflow.get("nodes"), list):
        # Convert list of node dicts with an 'id' field into our expected mapping
        node_list = workflow.get("nodes", [])
        normalized = {}
        for n in node_list:
            if isinstance(n, dict):
                node_id = str(n.get("id", ""))
                if node_id:
                    normalized[node_id] = n
        if normalized:
            workflow = normalized
            print(f"ℹ️ Normalized workflow from nodes list to dict with {len(workflow)} entries")
    elif isinstance(workflow, list):
        # Unexpected list: attempt to build dict assuming each item has 'id'
        normalized = {}
        for n in workflow:
            if isinstance(n, dict):
                node_id = str(n.get("id", ""))
                if node_id:
                    normalized[node_id] = n
        if normalized:
            workflow = normalized
            print(f"ℹ️ Normalized workflow from list to dict with {len(workflow)} entries")
        else:
            print("⚠️ Workflow is a list without dict nodes; using basic workflow fallback")
            workflow = create_basic_workflow()

    # Detect UI-export (graph editor) format nodes lacking 'class_type'. If found, fallback to basic API workflow.
    raw_ui_nodes = sum(1 for n in workflow.values() if isinstance(n, dict) and 'type' in n and 'class_type' not in n)
    if raw_ui_nodes:
        print(f"ℹ️ Detected {raw_ui_nodes} UI layout node(s) without 'class_type'. Falling back to basic API workflow format.")
        workflow = create_basic_workflow()

    # Extract parameters with optimized defaults
    positive_prompt = job_input.get("positive_prompt", "avachar, professional photo, high quality, detailed face, 8k uhd")
    negative_prompt = job_input.get("negative_prompt", "ugly, deformed, blurry, low quality, noise, watermark, text")
    steps = job_input.get("steps", 25)  # Reduced from 30 for cost efficiency
    cfg = job_input.get("cfg_scale", 7.5)  # Optimized for quality/creativity balance
    width = job_input.get("width", 1024)
    height = job_input.get("height", 1024)
    seed = job_input.get("seed", -1)
    lora_strength = job_input.get("lora_strength", 0.85)  # Slightly increased for better avatar quality
    
    print(f"  - Positive prompt: {positive_prompt[:50]}...")
    print(f"  - Steps: {steps} (cost-optimized)")
    print(f"  - CFG Scale: {cfg}")
    print(f"  - Resolution: {width}x{height}")
    print(f"  - LoRA strength: {lora_strength}")
    
    # Update workflow nodes (customize based on your workflow structure)
    updated_nodes = 0
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            # Skip metadata/non-node entries
            continue
        class_type = node.get("class_type")
        if class_type == "CLIPTextEncode":
            title = node.get("_meta", {}).get("title", "").lower()
            if "positive" in title or node_id in ["6"]:  # Common positive prompt node IDs
                node["inputs"]["text"] = positive_prompt
                updated_nodes += 1
                print(f"  ✓ Updated positive prompt in node {node_id}")
            elif "negative" in title or node_id in ["7"]:  # Common negative prompt node IDs
                node["inputs"]["text"] = negative_prompt
                updated_nodes += 1
                print(f"  ✓ Updated negative prompt in node {node_id}")
        
        elif class_type == "KSampler":
            node["inputs"]["steps"] = steps
            node["inputs"]["cfg"] = cfg
            node["inputs"]["seed"] = seed if seed != -1 else int(time.time() * 1000)
            # Use efficient sampler for cost optimization
            if "sampler_name" in node["inputs"]:
                node["inputs"]["sampler_name"] = "dpmpp_2m_sde"  # Fast and high-quality
            if "scheduler" in node["inputs"]:
                node["inputs"]["scheduler"] = "karras"  # Good quality scheduler
            updated_nodes += 1
            print(f"  ✓ Updated sampler settings in node {node_id}")
        
        elif class_type == "EmptyLatentImage":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
            updated_nodes += 1
            print(f"  ✓ Updated dimensions in node {node_id}")
        
        elif class_type == "LoraLoader":
            node["inputs"]["strength_model"] = lora_strength
            node["inputs"]["strength_clip"] = lora_strength
            updated_nodes += 1
            print(f"  ✓ Updated LoRA strength in node {node_id}")
    
    print(f"✅ Updated {updated_nodes} workflow nodes")
    return workflow

def create_basic_workflow():
    """
    Create an optimized basic SDXL + LoRA workflow
    Optimized for quality and cost efficiency
    """
    
    return {
        "3": {
            "inputs": {
                "seed": 0,
                "steps": 25,  # Reduced for cost efficiency
                "cfg": 7.5,    # Balanced for quality
                "sampler_name": "dpmpp_2m_sde",  # Fast and high quality
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
                "text": "avachar, professional photo, high quality, detailed face, sharp focus, 8k uhd, dslr, studio lighting",
                "clip": ["10", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Positive)"}
        },
        "7": {
            "inputs": {
                "text": "ugly, deformed, blurry, low quality, noise, watermark, text, oversaturated, bad anatomy, disfigured",
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
                "strength_model": 0.85,  # Increased for better quality
                "strength_clip": 0.85,
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
    RunPod serverless handler with enhanced logging and JPG output
    
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
        
        # Image format options
        "output_format": "jpg",  # "jpg", "png", or "webp"
        "output_quality": 95,    # 1-100 (higher = better quality, larger file)
        "return_base64": true,   # Return base64 or URL
        "return_metadata": true, # Include file size, dimensions, etc.
        "save_to_disk": true     # Save images to /workspace/outputs
    }
    """
    
    print("\n" + "="*60)
    print("🎨 NEW JOB RECEIVED")
    print("="*60)
    
    job_input = job["input"]
    print(f"📋 Job input keys: {list(job_input.keys())}")
    
    # Ensure ComfyUI is running
    print("\n🔧 Checking ComfyUI server status...")
    if not start_comfyui():
        error_msg = "Failed to start ComfyUI server"
        print(f"❌ {error_msg}")
        return {"error": error_msg}
    
    try:
        # Get output format settings (default to JPG as requested)
        output_format = job_input.get("output_format", "jpg").lower()
        output_quality = job_input.get("output_quality", 95)
        return_base64 = job_input.get("return_base64", True)
        return_metadata = job_input.get("return_metadata", True)
        # Accept legacy/misspelled key 'save_to_dsk'
        save_to_disk = job_input.get("save_to_disk", job_input.get("save_to_dsk", True))
        
        print(f"\n📸 Output settings:")
        print(f"  - Format: {output_format.upper()}")
        print(f"  - Quality: {output_quality}")
        print(f"  - Return base64: {return_base64}")
        print(f"  - Save to disk: {save_to_disk}")
        
        # Validate format
        if output_format not in ["jpg", "jpeg", "png", "webp"]:
            error_msg = f"Invalid output_format: {output_format}. Use 'jpg', 'png', or 'webp'"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
        
        # Validate quality
        if not 1 <= output_quality <= 100:
            error_msg = f"Invalid output_quality: {output_quality}. Use 1-100"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
        
        # Create workflow
        print("\n🔨 Creating workflow...")
        workflow = create_workflow(job_input)
        print("✅ Workflow created")
        
        # Queue prompt
        print("\n📤 Queueing prompt...")
        queue_result = queue_prompt(workflow)
        
        if "error" in queue_result:
            return queue_result
        
        prompt_id = queue_result.get("prompt_id")
        
        if not prompt_id:
            error_msg = "No prompt_id returned from queue"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
        
        print(f"✅ Prompt queued with ID: {prompt_id}")
        
        # Wait for completion
        print("\n⏳ Waiting for generation to complete...")
        outputs = wait_for_completion(prompt_id)
        
        if "error" in outputs:
            return outputs
        
        # Process generated images
        print("\n🖼️ Processing generated images...")
        images = []
        saved_paths = []
        
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                print(f"📦 Found {len(node_output['images'])} image(s) in node {node_id}")
                
                for idx, image_info in enumerate(node_output["images"]):
                    print(f"\n  Processing image {idx + 1}...")
                    
                    # Get original image
                    original_data = get_image(
                        image_info["filename"],
                        image_info.get("subfolder", ""),
                        image_info.get("type", "output")
                    )
                    
                    if not original_data:
                        print(f"  ⚠️ Failed to fetch image, skipping...")
                        continue
                    
                    # Convert to desired format (ensure JPG)
                    print(f"  🔄 Converting to {output_format.upper()}...")
                    converted_data = convert_image_format(
                        original_data,
                        output_format,
                        output_quality
                    )
                    
                    # Get metadata
                    img = Image.open(BytesIO(converted_data))
                    
                    # Create filename with proper extension
                    original_name = Path(image_info['filename']).stem
                    new_filename = f"{original_name}.{output_format}"
                    
                    image_result = {
                        "filename": new_filename
                    }
                    
                    # Save to disk if requested
                    if save_to_disk:
                        saved_path = save_image_to_disk(converted_data, new_filename)
                        if saved_path:
                            saved_paths.append(saved_path)
                            image_result["saved_path"] = saved_path
                    
                    # Return base64 encoded image
                    if return_base64:
                        b64_image = base64.b64encode(converted_data).decode('utf-8')
                        image_result["image"] = b64_image
                        image_result["image_data_url"] = f"data:image/{output_format};base64,{b64_image}"
                        print(f"  ✅ Image encoded to base64 ({len(b64_image)} chars)")
                    
                    # Add metadata
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
                        print(f"  📊 Dimensions: {img.width}x{img.height}")
                        print(f"  📊 Size: {image_result['metadata']['size_mb']} MB")
                    
                    images.append(image_result)
        
        print(f"\n✅ Successfully processed {len(images)} image(s)")
        if saved_paths:
            print(f"💾 Saved to: {saved_paths}")
        
        result = {
            "status": "success",
            "images": images,
            "prompt_id": prompt_id,
            "settings": {
                "format": output_format,
                "quality": output_quality,
                "total_images": len(images)
            }
        }
        
        if saved_paths:
            result["saved_paths"] = saved_paths
        
        print("\n" + "="*60)
        print("✅ JOB COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
        
        return result
        
    except Exception as e:
        error_msg = f"Handler exception: {type(e).__name__}: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        print(traceback.format_exc())
        return {"error": error_msg}

# Initialize on container start
print("=" * 60)
print("🤖 RunPod Avatar Generation Handler v2.1")
print("📸 Supports: JPG, PNG, WebP with quality control")
print("💾 Auto-saves images to /workspace/outputs")
print("🔍 Enhanced debugging and error logging")
print("=" * 60)

# Verify Python and environment
print(f"🐍 Python: {sys.version}")
print(f"📂 Working directory: {os.getcwd()}")
print(f"🔧 ComfyUI path: {COMFY_DIR}")

# Check model directory
print("\n📦 Checking models...")
model_checks = [
    ("SDXL Base", COMFY_DIR / "models/checkpoints/sd_xl_base_1.0.safetensors"),
    ("SDXL VAE", COMFY_DIR / "models/vae/sdxl_vae.safetensors"),
    ("Avatar LoRA", COMFY_DIR / "models/loras/avatar_lora.safetensors"),
]

models_missing = []
for name, path in model_checks:
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  ✓ {name}: {size_mb:.1f} MB")
    else:
        print(f"  ✗ {name}: NOT FOUND")
        models_missing.append(name)

# Download models if needed
if models_missing or not (COMFY_DIR / "models/checkpoints/sd_xl_base_1.0.safetensors").exists():
    print("\n📥 Models missing, downloading...")
    try:
        import download_models
        if download_models.download_all_models():
            print("✅ All models downloaded successfully")
        else:
            print("⚠️ Some models may have failed to download")
    except Exception as e:
        print(f"❌ Error downloading models: {e}")
else:
    print("✅ All required models present")

print("\n" + "=" * 60)
print("🚀 Handler ready for jobs!")
print("=" * 60 + "\n")

# Start RunPod serverless
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})