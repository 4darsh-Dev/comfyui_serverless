# ComfyUI Serverless on RunPod

A production-ready serverless deployment of ComfyUI for AI image generation, optimized for RunPod's GPU infrastructure with enhanced debugging and error handling.

## 🚀 Features

- **Serverless Architecture**: Pay-per-second GPU usage with automatic scaling
- **ComfyUI Integration**: Full ComfyUI workflow support with custom nodes
- **Multi-Format Support**: Generate images in JPG, PNG, or WebP with quality control
- **Auto-Save to Disk**: Images automatically saved to `/workspace/outputs`
- **Enhanced Debugging**: Comprehensive logging at every step for easy troubleshooting
- **Cost-Optimized**: Reduced steps and optimized sampler settings for efficiency
- **Robust Error Handling**: Detailed error messages and retry logic
- **Custom LoRA Support**: Load and use custom models
- **Docker-Based**: Consistent environment across deployments
- **Optimized Build**: ~12GB Docker image with CUDA 11.8 + PyTorch 2.1.0
- **Unit Tests**: Comprehensive test suite for validation

## 📋 Prerequisites

- Docker installed locally (for building)
- Docker Hub account (for hosting images)
- RunPod account (for deployment)
- GPU with CUDA support (for local testing)

## 🏗️ Project Structure

```
comfyui_serverless/
├── Dockerfile              # Docker image configuration
├── handler.py              # RunPod serverless handler (v2.1)
├── download_models.py      # Model download script with retry logic
├── deploy.sh              # Deployment automation script
├── test_endpoint.py       # API endpoint testing
├── test_handler.py        # Unit tests for handler functions
├── local_test.py          # Local testing without ComfyUI
├── comfy_setup.py         # ComfyUI setup utilities
├── DEBUGGING.md           # Comprehensive debugging guide
├── .gitignore             # Git ignore patterns
├── LICENSE                # MIT License
└── README.md              # This file
```

## 🐳 Docker Image

### Build Locally

```bash
# Build the Docker image
docker build -t 4darsh/comfyui-serverless:latest .

# Check image size
docker images 4darsh/comfyui-serverless

# View layer details
docker history 4darsh/comfyui-serverless:latest --human=true
```

### Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Push the image
docker push 4darsh/comfyui-serverless:latest

# Optional: Tag with version
docker tag 4darsh/comfyui-serverless:latest 4darsh/comfyui-serverless:v1.0
docker push 4darsh/comfyui-serverless:v1.0
```

### Pull and Use

```bash
# Pull from Docker Hub
docker pull 4darsh/comfyui-serverless:latest

# Run locally (requires GPU)
docker run --rm -it --gpus all -p 8188:8188 4darsh/comfyui-serverless:latest
```

## 🔧 Configuration

### Docker Image Details

- **Base Image**: `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`
- **Python Version**: 3.10
- **CUDA Version**: 11.8
- **PyTorch Version**: 2.1.0
- **Size**: ~12GB (optimizable to ~8GB)

### Key Components

| Component | Version | Purpose |
|-----------|---------|---------|
| ComfyUI | Latest | Core workflow engine |
| xformers | 0.0.22 | Optimized transformers |
| ControlNet Aux | Latest | Pose/composition control |
| ComfyUI Manager | Latest | Node management |
| opencv-python | Latest | Image processing |
| RunPod SDK | Latest | Serverless integration |

## 🎯 How It Works

### Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│  RunPod Serverless Container                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Container Starts                              │  │
│  │     - Download models if needed                   │  │
│  │     - Start ComfyUI subprocess                    │  │
│  │     - Wait for server ready (30s timeout)         │  │
│  └───────────────────────────────────────────────────┘  │
│                        │                                 │
│                        ▼                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  2. Job Request Received                          │  │
│  │     - Parse input parameters                      │  │
│  │     - Create ComfyUI workflow                     │  │
│  │     - Queue prompt via HTTP API                   │  │
│  └───────────────────────────────────────────────────┘  │
│                        │                                 │
│                        ▼                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  3. ComfyUI Processing                            │  │
│  │     - Run workflow (5min timeout)                 │  │
│  │     - Generate images                             │  │
│  │     - Save to output directory                    │  │
│  └───────────────────────────────────────────────────┘  │
│                        │                                 │
│                        ▼                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  4. Post-Processing                               │  │
│  │     - Fetch generated images                      │  │
│  │     - Convert format (JPG/PNG/WebP)               │  │
│  │     - Apply quality settings                      │  │
│  │     - Return base64-encoded results               │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Subprocess Explanation

The handler uses Python's `subprocess.Popen()` to run ComfyUI as a background process:

```python
comfy_process = subprocess.Popen(
    [sys.executable, "main.py", "--listen", "0.0.0.0", "--port", str(COMFY_PORT)],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
```

**Why subprocesses?**
- ComfyUI runs as an independent server
- Handler communicates via HTTP API
- Non-blocking execution allows concurrent request handling
- Process isolation for stability

## 🚀 Deployment to RunPod

### 1. Create RunPod Template

1. Go to [RunPod Templates](https://www.runpod.io/console/serverless)
2. Click **New Template**
3. Configure:
   - **Template Name**: ComfyUI Serverless
   - **Container Image**: `4darsh/comfyui-serverless:latest`
   - **Container Disk**: 20 GB
   - **Volume Mount Path**: `/workspace/models` (optional for persistent models)
   - **Expose HTTP Ports**: 8188
   - **Environment Variables**: None required

### 2. Create Endpoint

1. Go to **Serverless** → **Endpoints**
2. Click **New Endpoint**
3. Select your template
4. Configure:
   - **GPU Type**: RTX 3090 / RTX 4090 / A100 (recommended)
   - **Max Workers**: 3-5
   - **Idle Timeout**: 5 seconds
   - **Flash Boot**: Enabled (if available)

### 3. Test Endpoint

```bash
# Test with endpoint URL
python test_endpoint.py
```

## 📝 API Usage

### Request Format

```json
{
  "input": {
    "positive_prompt": "professional portrait, high quality, detailed",
    "negative_prompt": "ugly, deformed, blurry, low quality",
    "steps": 25,
    "cfg_scale": 7.5,
    "width": 1024,
    "height": 1024,
    "seed": -1,
    "lora_strength": 0.85,
    "output_format": "jpg",
    "output_quality": 95,
    "save_to_disk": true,
    "return_base64": true,
    "return_metadata": true
  }
}
```

### Response Format

```json
{
  "status": "success",
  "images": [
    {
      "filename": "avatar_00001_.jpg",
      "image": "base64_encoded_image_data...",
      "image_data_url": "data:image/jpg;base64,...",
      "saved_path": "/workspace/outputs/avatar_00001_.jpg",
      "metadata": {
        "width": 1024,
        "height": 1024,
        "format": "JPG",
        "mode": "RGB",
        "size_bytes": 1887654,
        "size_mb": 1.8,
        "quality": 95
      }
    }
  ],
  "prompt_id": "abc123",
  "settings": {
    "format": "jpg",
    "quality": 95,
    "total_images": 1
  },
  "saved_paths": ["/workspace/outputs/avatar_00001_.jpg"]
}
```

## 🧪 Testing

### Run Unit Tests

```bash
# Test handler functions locally
python3 test_handler.py

# Run all local tests
python3 local_test.py
```

### Test with RunPod Endpoint

```bash
# Update endpoint URL and API key in test_endpoint.py
python3 test_endpoint.py
```

## 🔍 Optimization Tips

### Cost-Efficient Settings (Recommended)

```python
{
    "steps": 25,              # Reduced from 30 (20% faster)
    "cfg_scale": 7.5,         # Balanced quality/creativity
    "width": 1024,            # Standard SDXL resolution
    "height": 1024,
    "lora_strength": 0.85,    # Optimized for avatar quality
    "output_format": "jpg",   # Smaller file size
    "output_quality": 95      # High quality, reasonable size
}
```

### What's Been Optimized

- **Sampler**: `dpmpp_2m_sde` (fast and high quality)
- **Scheduler**: `karras` (good quality)
- **Steps**: Reduced to 25 (from 30) for 20% speed improvement
- **CFG Scale**: 7.5 (from 8.0) for better balance
- **Output**: JPG format by default (smaller files than PNG)

### Reduce Docker Image Size

Current size: **~12 GB** → Optimized: **~8 GB**

**Remove duplicate PyTorch** (already in base image):
```dockerfile
# ❌ Don't do this (adds 2.5 GB)
RUN pip install torch torchvision torchaudio

# ✅ Base image already has PyTorch 2.1.0
```

**Use headless OpenCV** (saves 200 MB):
```dockerfile
# ❌ Full OpenCV with GUI
RUN pip install opencv-python

# ✅ Headless version (no GUI needed in Docker)
RUN pip install opencv-python-headless
```

### Build Time Optimization

- **Layer Caching**: Place frequently changing files (handler.py) last
- **Multi-stage Builds**: Separate build and runtime stages
- **Parallel Installs**: Combine RUN commands when possible

## 🐛 Troubleshooting

For detailed debugging information, see [DEBUGGING.md](DEBUGGING.md)

### Common Issues

1. **ComfyUI server fails to start**
   - Check logs for detailed error messages
   - Verify GPU availability with `nvidia-smi`
   - Increase startup timeout (currently 60 seconds)

2. **Model download failures**
   - Network issues or rate limiting
   - Use RunPod Network Volumes for persistence
   - Check DEBUGGING.md for manual download steps

3. **Out of memory errors**
   - Reduce resolution (1024 → 768)
   - Lower batch size
   - Use xformers for memory efficiency

4. **Image generation timeout**
   - Increase timeout (default 300s)
   - Simplify workflow
   - Check ComfyUI logs for node errors

### Logging Output

The handler provides detailed logging at every step:

```
🚀 Starting ComfyUI server...
📂 Working directory: /workspace/ComfyUI
✅ ComfyUI files verified
✅ ComfyUI process started (PID: 12345)
⏳ Waiting for server to start (max 60 seconds)...
✅ ComfyUI server started successfully after 15 seconds

🎨 NEW JOB RECEIVED
📋 Job input keys: ['positive_prompt', 'steps', 'output_format']
🔧 Checking ComfyUI server status...
✅ Existing ComfyUI server is healthy

📸 Output settings:
  - Format: JPG
  - Quality: 95
  - Return base64: True
  - Save to disk: True

🔨 Creating workflow...
✅ Workflow created

📤 Queueing prompt...
✅ Prompt queued successfully: abc123

⏳ Waiting for prompt completion (ID: abc123, timeout: 300s)...
📊 Status update: running (after 10s)
✅ Prompt completed after 45s

🖼️ Processing generated images...
📦 Found 1 image(s) in node 9
  Processing image 1...
📥 Fetching image: avatar_00001_.png
✅ Image fetched successfully (2.5 MB)
🔄 Converting to JPG...
💾 Saved image: /workspace/outputs/avatar_00001_.jpg (1.8 MB)

✅ JOB COMPLETED SUCCESSFULLY
```

## 🧪 Testing

### Local Testing

```bash
# Run container locally
docker run --rm -it --gpus all -p 8188:8188 4darsh/comfyui-serverless:latest

# Access ComfyUI interface
open http://localhost:8188
```

### Unit Tests

```bash
# Test handler functions
python3 test_handler.py

# Run local test suite
python3 local_test.py
```

### Endpoint Testing

```bash
# Test serverless endpoint
python test_endpoint.py --endpoint YOUR_RUNPOD_ENDPOINT_ID
```

## 📊 Performance Metrics

| GPU Model | Cold Start | Warm Start | Generation Time (1024x1024, 30 steps) |
|-----------|------------|------------|----------------------------------------|
| RTX 3090  | ~45s       | ~2s        | ~8-12s                                 |
| RTX 4090  | ~40s       | ~1.5s      | ~5-8s                                  |
| A100      | ~35s       | ~1s        | ~4-6s                                  |

## 🛠️ Troubleshooting

### Image Build Failures

**Error: `pycairo` build failed**
```bash
# Missing system dependencies
# Solution: Install pkg-config and libcairo2-dev
RUN apt-get install -y pkg-config libcairo2-dev
```

**Error: Out of disk space**
```bash
# Clean Docker cache
docker system prune -a --volumes
```

### Runtime Issues

**ComfyUI server not starting**
- Check logs: `docker logs <container_id>`
- Increase startup timeout in `handler.py`
- Verify GPU availability: `nvidia-smi`
- See detailed troubleshooting in [DEBUGGING.md](DEBUGGING.md)

**Out of memory errors**
- Reduce image resolution
- Use lower batch sizes
- Choose GPU with more VRAM

**For comprehensive debugging guide, see [DEBUGGING.md](DEBUGGING.md)**

## 📦 Models

Models are downloaded at runtime using `download_models.py`:

```python
# Configure model URLs
MODELS = {
    "checkpoints": [
        "https://huggingface.co/your-model.safetensors"
    ],
    "loras": [
        "https://civitai.com/api/download/models/your-lora"
    ]
}
```

**Persistent Storage** (recommended):
- Use RunPod Network Volumes
- Mount to `/workspace/ComfyUI/models`
- Models persist across deployments

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🔗 Resources

- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [RunPod Documentation](https://docs.runpod.io/)
- [Docker Hub Image](https://hub.docker.com/r/4darsh/comfyui-serverless)
- [PyTorch Documentation](https://pytorch.org/docs/)

## 🙏 Acknowledgments

- ComfyUI team for the amazing workflow engine
- RunPod for serverless GPU infrastructure
- Open-source community for custom nodes and models

---

**Built with ❤️ for the AI community**

## 📚 Additional Resources

- [DEBUGGING.md](DEBUGGING.md) - Comprehensive debugging and troubleshooting guide
- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [RunPod Documentation](https://docs.runpod.io/)
- [Docker Hub Image](https://hub.docker.com/r/4darsh/comfyui-serverless)

## 📊 Version History

- **v2.1** (Current)
  - ✅ Enhanced logging and debugging
  - ✅ Improved error handling with retry logic
  - ✅ Optimized workflow settings (25 steps, dpmpp_2m_sde sampler)
  - ✅ Added comprehensive tests (12 unit tests)
  - ✅ JPG output by default
  - ✅ Auto-save to /workspace/outputs
  - ✅ Better server startup detection
  - ✅ Detailed progress logging

- **v2.0**
  - Multi-format support (JPG, PNG, WebP)
  - Quality control
  - Base64 encoding

- **v1.0**
  - Initial release
  - Basic SDXL + LoRA workflow

*Last Updated: November 14, 2025**

## 🖼️ Generating Avatars Locally

A helper script `generate_avatar.py` is provided to call the deployed RunPod endpoint and save returned base64 images to `avatar_images/` as JPG files.

Usage:

```bash
python generate_avatar.py "a majestic cyberpunk cat"
```

It will:
- Load `RUNPOD_API_KEY` from `.env` (place the file next to the script) using `python-dotenv` if installed.
- POST your prompt to the endpoint: `https://api.runpod.ai/v2/6qtbu2qnofk4m6/run`.
- Wait for the JSON response (can take ~2 minutes).
- Decode each returned image's base64 data and save as JPG.
- Name files using the first letters of up to 4 words of the prompt plus a shortened response id, e.g. `amcc_ab12cd34.jpg`.

If multiple images are returned they will be suffixed `_1`, `_2`, etc.

Ensure you have `requests` (and optionally `python-dotenv`) installed:

```bash
pip install requests python-dotenv
```

Troubleshooting:
- Missing API key: add `RUNPOD_API_KEY=your_key_here` to `.env`.
- Empty images array: inspect printed JSON snippet; verify the endpoint and prompt.
- Slow responses (>2m): network or GPU queue delay; script waits up to 5 minutes.