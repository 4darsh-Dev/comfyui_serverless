# ComfyUI Serverless Debugging Guide

## Common Issues and Solutions

### 1. ComfyUI Server Fails to Start

**Symptoms:**
- "❌ Failed to start ComfyUI server" error
- Container starts but server doesn't respond

**Troubleshooting Steps:**

1. **Check logs for process output:**
   ```python
   # The handler now captures stdout/stderr from ComfyUI process
   # Look for error messages in the container logs
   ```

2. **Verify ComfyUI installation:**
   ```bash
   # Inside container
   ls -la /workspace/ComfyUI/main.py
   python3 /workspace/ComfyUI/main.py --help
   ```

3. **Test server manually:**
   ```bash
   cd /workspace/ComfyUI
   python3 main.py --listen 0.0.0.0 --port 8188
   # Wait for "Starting server" message
   ```

4. **Common causes:**
   - Missing dependencies (xformers, torch)
   - GPU not available (check nvidia-smi)
   - Port already in use
   - Missing model files

**Solutions:**
- Increase startup timeout (currently 60 seconds)
- Check GPU availability
- Verify all Python dependencies installed
- Check disk space for models

### 2. Model Download Failures

**Symptoms:**
- "Models missing, downloading..." followed by errors
- "Failed to download" messages for specific models

**Troubleshooting Steps:**

1. **Check network connectivity:**
   ```bash
   curl -I https://huggingface.co
   ping google.com
   ```

2. **Verify download URLs:**
   - HuggingFace URLs may change
   - Google Drive links may expire
   - Check for rate limiting

3. **Manual download:**
   ```bash
   cd /workspace/ComfyUI/models/checkpoints
   wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
   ```

**Solutions:**
- Use RunPod Network Volumes for persistent models
- Pre-download models into Docker image
- Use alternative mirror URLs
- Implement retry logic (now included in download_models.py)

### 3. Out of Memory (OOM) Errors

**Symptoms:**
- "CUDA out of memory" errors
- Container crashes during generation
- Slow generation times

**Troubleshooting Steps:**

1. **Check GPU memory:**
   ```bash
   nvidia-smi
   ```

2. **Reduce memory usage:**
   - Lower resolution (1024x1024 → 768x768)
   - Reduce batch size
   - Use xformers for memory efficiency

**Solutions:**
```python
# In job input
{
    "width": 768,
    "height": 768,
    "steps": 20  # Reduced from 25
}
```

### 4. Image Generation Failures

**Symptoms:**
- "Timeout waiting for completion" error
- No images in output
- Error status in history

**Troubleshooting Steps:**

1. **Check workflow validity:**
   ```python
   # Test workflow locally
   import json
   workflow = create_workflow({})
   print(json.dumps(workflow, indent=2))
   ```

2. **Verify model files:**
   ```bash
   ls -lh /workspace/ComfyUI/models/checkpoints/
   ls -lh /workspace/ComfyUI/models/loras/
   ```

3. **Check ComfyUI logs:**
   - Look for node errors
   - Verify all nodes can execute

**Solutions:**
- Increase timeout (default 300s)
- Simplify workflow
- Test with basic workflow first
- Verify LoRA compatibility

### 5. Image Format/Quality Issues

**Symptoms:**
- Large file sizes
- Poor image quality
- Wrong format output

**Troubleshooting Steps:**

1. **Check output settings:**
   ```python
   {
       "output_format": "jpg",  # jpg, png, webp
       "output_quality": 95,     # 1-100
   }
   ```

2. **Test different settings:**
   - JPG: Quality 85-95 (good balance)
   - PNG: Quality 90-100 (lossless)
   - WebP: Quality 80-90 (best compression)

**Solutions:**
- Use JPG for photos (smaller files)
- Use PNG for images with transparency
- Adjust quality based on use case

## Logging and Monitoring

### Enable Detailed Logging

The handler now includes comprehensive logging:

```
🚀 Starting ComfyUI server...
📂 Working directory: /workspace/ComfyUI
🔧 Python executable: /usr/bin/python3
🌐 Server URL: http://127.0.0.1:8188
✅ ComfyUI files verified
✅ ComfyUI process started (PID: 12345)
⏳ Waiting for server to start (max 60 seconds)...
✅ ComfyUI server started successfully after 15 seconds
```

### Key Log Indicators

- ✅ Success indicators
- ❌ Error indicators
- ⏳ Progress indicators
- 📊 Status updates
- 💾 File operations
- 🔄 Processing steps

### Debugging Individual Functions

Each function now has detailed logging:

```python
# Queue prompt
📤 Queueing prompt to ComfyUI...
✅ Prompt queued successfully: abc123

# Wait for completion
⏳ Waiting for prompt completion (ID: abc123, timeout: 300s)...
📊 Status update: running (after 10s)
✅ Prompt completed after 45s

# Process images
🖼️ Processing generated images...
📦 Found 1 image(s) in node 9
  Processing image 1...
📥 Fetching image: avatar_00001_.png
✅ Image fetched successfully (2.5 MB)
🔄 Converting to JPG...
💾 Saved image: /workspace/outputs/avatar_00001_.jpg (1.8 MB)
```

## Performance Optimization

### Cost-Efficient Settings

```python
{
    "steps": 25,              # Down from 30 (17% faster)
    "cfg_scale": 7.5,         # Balanced quality/creativity
    "sampler_name": "dpmpp_2m_sde",  # Fast and high quality
    "scheduler": "karras",    # Good quality
    "width": 1024,            # Standard SDXL
    "height": 1024,
    "lora_strength": 0.85,    # Optimal for avatars
    "output_format": "jpg",   # Smaller files
    "output_quality": 95      # High quality, reasonable size
}
```

### Batch Processing

For multiple images:
```python
{
    "num_images": 4,  # Generate 4 images in one run
    "save_to_disk": true  # Save all to /workspace/outputs
}
```

### Model Caching

Use RunPod Network Volumes:
```yaml
# RunPod Template Settings
Volume Mount Path: /workspace/ComfyUI/models
Volume Size: 50 GB
```

Models persist across deployments, avoiding repeated downloads.

## Testing Guide

### Local Testing (Without GPU)

```bash
# Run unit tests
python3 test_handler.py
```

### Testing with RunPod Endpoint

```python
# test_endpoint.py
import requests

ENDPOINT = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
API_KEY = "YOUR_API_KEY"

payload = {
    "input": {
        "positive_prompt": "professional portrait",
        "steps": 20,
        "output_format": "jpg",
        "save_to_disk": true
    }
}

response = requests.post(
    ENDPOINT,
    json=payload,
    headers={"Authorization": f"Bearer {API_KEY}"}
)

print(response.json())
```

### Testing Workflow Changes

```python
# Test workflow creation
from handler import create_workflow

job_input = {
    "positive_prompt": "test",
    "steps": 15
}

workflow = create_workflow(job_input)
print(json.dumps(workflow, indent=2))
```

## Deployment Checklist

- [ ] Docker image builds successfully
- [ ] All dependencies installed
- [ ] Models downloaded or volume mounted
- [ ] ComfyUI starts within timeout
- [ ] Test job completes successfully
- [ ] Images saved in correct format
- [ ] Logs are clear and helpful
- [ ] Error handling works correctly
- [ ] Unit tests pass
- [ ] Cost per generation is acceptable

## Support Resources

- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [RunPod Documentation](https://docs.runpod.io/serverless/overview)
- [SDXL Documentation](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)

## Version History

- **v2.1** (Current)
  - Enhanced logging and debugging
  - Improved error handling
  - Optimized workflow settings
  - Added comprehensive tests
  - JPG output by default
  - Auto-save to disk

- **v2.0**
  - Multi-format support (JPG, PNG, WebP)
  - Quality control
  - Base64 encoding

- **v1.0**
  - Initial release
  - Basic SDXL + LoRA workflow
