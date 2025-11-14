
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
# Note: PyTorch 2.1.0 is already installed in the base image
# We're upgrading to PyTorch 2.4.0 for better stability and float8 support
RUN pip install --no-cache-dir \
    torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu118 && \
    pip install --no-cache-dir \
    xformers==0.0.27.post2 \
    einops \
    opencv-python \
    pillow \
    requests \
    tqdm \
    gdown \
    mediapipe \
    controlnet-aux \
    "numpy<2.0" \
    "scipy<1.13" \
    runpod

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI /workspace/ComfyUI

# Install ComfyUI requirements
WORKDIR /workspace/ComfyUI
RUN pip install --no-cache-dir -r requirements.txt

# Install custom nodes
RUN cd custom_nodes && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git && \
    cd comfyui_controlnet_aux && \
    pip install --no-cache-dir -r requirements.txt

# Copy handler script
COPY handler.py /workspace/handler.py
COPY download_models.py /workspace/download_models.py

# Create model directories
RUN mkdir -p \
    /workspace/ComfyUI/models/checkpoints \
    /workspace/ComfyUI/models/loras \
    /workspace/ComfyUI/models/controlnet \
    /workspace/ComfyUI/models/vae \
    /workspace/ComfyUI/user/default/workflows

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV COMFY_DIR=/workspace/ComfyUI

WORKDIR /workspace

# Start handler
CMD ["python", "-u", "handler.py"]