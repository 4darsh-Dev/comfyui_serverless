
#!/bin/bash

# RunPod deployment script

echo "🚀 Building and deploying to RunPod..."

# 1. Build Docker image
echo "📦 Building Docker image..."
docker build -t your-dockerhub-username/avatar-generation:latest .

# 2. Push to Docker Hub
echo "📤 Pushing to Docker Hub..."
docker push your-dockerhub-username/avatar-generation:latest

echo "✅ Done! Now:"
echo "1. Go to RunPod dashboard"
echo "2. Create new Serverless Endpoint"
echo "3. Use image: your-dockerhub-username/avatar-generation:latest"
echo "4. Set GPU: RTX 4090 or A100"
echo "5. Configure network volume (optional, for model persistence)"