
"""
Test the RunPod serverless endpoint
"""

import requests
import json
import base64
from pathlib import Path

# Your RunPod endpoint URL
RUNPOD_ENDPOINT = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
RUNPOD_API_KEY = "YOUR_API_KEY"

def test_generation():
    """Test avatar generation"""
    
    payload = {
        "input": {
            "positive_prompt": "avachar, professional businessman, suit and tie, office background, confident smile, high quality, 8k uhd, dslr",
            "negative_prompt": "ugly, deformed, noisy, blurry, low contrast, disfigured, bad anatomy",
            "steps": 30,
            "cfg_scale": 8.0,
            "width": 1024,
            "height": 1024,
            "seed": 42,
            "lora_strength": 0.8,
            "num_images": 1
        }
    }
    
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Sending request to RunPod...")
    response = requests.post(RUNPOD_ENDPOINT, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        
        if "output" in result and "images" in result["output"]:
            # Save images
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            
            for i, img_data in enumerate(result["output"]["images"]):
                img_bytes = base64.b64decode(img_data["image"])
                output_path = output_dir / f"avatar_{i}.png"
                
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                
                print(f"✅ Saved: {output_path}")
            
            return True
        else:
            print(f"❌ Error: {result}")
            return False
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")
        return False

if __name__ == "__main__":
    test_generation()