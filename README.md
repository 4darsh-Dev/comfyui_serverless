# ComfyUI Serverless on RunPod

A production-ready serverless deployment of ComfyUI for AI image generation, optimized for RunPod's GPU infrastructure.

## 🚀 Features

- **Serverless Architecture**: Pay-per-second GPU usage with automatic scaling
- **ComfyUI Integration**: Full ComfyUI workflow support with custom nodes
- **Multi-Format Support**: Generate images in JPG, PNG, or WebP with quality control
- **ControlNet Support**: Advanced pose and composition control
- **Custom LoRA Support**: Load and use custom models
- **Docker-Based**: Consistent environment across deployments
- **Optimized Build**: ~12GB Docker image with CUDA 11.8 + PyTorch 2.1.0

## 📋 Prerequisites

- Docker installed locally (for building)
- Docker Hub account (for hosting images)
- RunPod account (for deployment)
- GPU with CUDA support (for local testing)

## 🏗️ Project Structure

```
comfyui_serverless/
├── Dockerfile              # Docker image configuration
├── handler.py              # RunPod serverless handler
├── download_models.py      # Model download script
├── deploy.sh              # Deployment automation script
├── start.sh               # Local startup script
├── test_endpoint.py       # API endpoint testing
├── comfy_setup.py         # ComfyUI setup utilities
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
    "steps": 30,
    "cfg_scale": 8.0,
    "width": 1024,
    "height": 1024,
    "seed": -1,
    "lora_strength": 0.8,
    "output_format": "jpg",
    "quality": 95
  }
}
```

### Response Format

```json
{
  "output": {
    "images": [
      "base64_encoded_image_data..."
    ],
    "metadata": {
      "seed": 12345,
      "format": "jpg",
      "size_mb": 1.2
    }
  }
}
```

## 🔍 Optimization Tips

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

**Remove unused packages**:
- `mediapipe` - Only if not using face detection (~100 MB)
- `svglib` - Only if processing SVG files (~50 MB)

### Build Time Optimization

- **Layer Caching**: Place frequently changing files (handler.py) last
- **Multi-stage Builds**: Separate build and runtime stages
- **Parallel Installs**: Combine RUN commands when possible

## 🧪 Testing

### Local Testing

```bash
# Run container locally
docker run --rm -it --gpus all -p 8188:8188 4darsh/comfyui-serverless:latest

# Access ComfyUI interface
open http://localhost:8188
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

**Out of memory errors**
- Reduce image resolution
- Use lower batch sizes
- Choose GPU with more VRAM

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

*Last Updated: November 12, 2025*