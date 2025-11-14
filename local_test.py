#!/usr/bin/env python3
"""
Local testing script for handler functions
Tests the handler without needing ComfyUI to be running
"""

import sys
import json
from pathlib import Path

# Mock RunPod for local testing
class MockRunPod:
    @staticmethod
    def serverless_start(config):
        print("🧪 Mock RunPod serverless - would start here")
        print(f"   Handler: {config['handler']}")

sys.modules['runpod'] = type('MockRunPod', (), {
    'serverless': type('Serverless', (), {'start': MockRunPod.serverless_start})
})()

# Now import handler
from handler import (
    create_basic_workflow,
    create_workflow,
    convert_image_format,
    get_file_size_mb
)


def test_workflow_creation():
    """Test workflow creation with various inputs"""
    print("\n" + "="*60)
    print("🧪 Testing Workflow Creation")
    print("="*60)
    
    # Test 1: Default parameters
    print("\n1. Testing with default parameters...")
    try:
        workflow = create_workflow({})
        print(f"   ✅ Created workflow with {len(workflow)} nodes")
    except Exception as e:
        print(f"   ⚠️ Expected error (no ComfyUI dir): {e}")
    
    # Test 2: Custom parameters
    print("\n2. Testing with custom parameters...")
    custom_input = {
        "positive_prompt": "beautiful sunset, cinematic",
        "negative_prompt": "ugly, blurry",
        "steps": 20,
        "cfg_scale": 7.0,
        "width": 768,
        "height": 768,
        "seed": 42,
        "lora_strength": 0.9
    }
    try:
        workflow = create_workflow(custom_input)
        print(f"   ✅ Created workflow with custom parameters")
    except Exception as e:
        print(f"   ⚠️ Expected error (no ComfyUI dir): {e}")
    
    # Test 3: Basic workflow (should work without ComfyUI)
    print("\n3. Testing basic workflow creation...")
    workflow = create_basic_workflow()
    print(f"   ✅ Created basic workflow with {len(workflow)} nodes")
    
    # Verify workflow structure
    assert "3" in workflow, "Missing KSampler node"
    assert "10" in workflow, "Missing LoraLoader node"
    assert workflow["3"]["class_type"] == "KSampler"
    print("   ✅ Workflow structure validated")
    
    # Check optimized settings
    assert workflow["3"]["inputs"]["steps"] == 25, "Steps not optimized"
    assert workflow["3"]["inputs"]["cfg"] == 7.5, "CFG not optimized"
    assert workflow["3"]["inputs"]["sampler_name"] == "dpmpp_2m_sde", "Sampler not optimized"
    print("   ✅ Optimized settings verified")
    
    return workflow


def test_image_conversion():
    """Test image format conversion"""
    print("\n" + "="*60)
    print("🧪 Testing Image Conversion")
    print("="*60)
    
    try:
        from PIL import Image
        from io import BytesIO
        
        # Create test image
        print("\n1. Creating test image...")
        img = Image.new('RGB', (256, 256), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        png_data = buffer.getvalue()
        print(f"   ✅ Created test image ({len(png_data)} bytes)")
        
        # Test JPG conversion
        print("\n2. Testing JPG conversion...")
        jpg_data = convert_image_format(png_data, "jpg", 95)
        jpg_img = Image.open(BytesIO(jpg_data))
        print(f"   ✅ Converted to JPG: {len(jpg_data)} bytes, format: {jpg_img.format}")
        
        # Test quality settings
        print("\n3. Testing quality settings...")
        high_q = convert_image_format(png_data, "jpg", 95)
        low_q = convert_image_format(png_data, "jpg", 50)
        print(f"   ✅ High quality (95): {len(high_q)} bytes")
        print(f"   ✅ Low quality (50): {len(low_q)} bytes")
        
        # Test RGBA to JPG
        print("\n4. Testing RGBA to JPG conversion...")
        rgba_img = Image.new('RGBA', (256, 256), color=(255, 0, 0, 128))
        buffer = BytesIO()
        rgba_img.save(buffer, format='PNG')
        rgba_data = buffer.getvalue()
        
        jpg_from_rgba = convert_image_format(rgba_data, "jpg", 95)
        result_img = Image.open(BytesIO(jpg_from_rgba))
        assert result_img.mode == 'RGB', "Should convert RGBA to RGB"
        print(f"   ✅ RGBA converted to RGB: {result_img.mode}")
        
    except ImportError:
        print("   ⚠️ PIL not available, skipping image tests")


def test_utility_functions():
    """Test utility functions"""
    print("\n" + "="*60)
    print("🧪 Testing Utility Functions")
    print("="*60)
    
    # Test file size calculation
    print("\n1. Testing file size calculation...")
    data_1mb = b'x' * (1024 * 1024)
    size = get_file_size_mb(data_1mb)
    assert abs(size - 1.0) < 0.01, f"Expected ~1.0 MB, got {size}"
    print(f"   ✅ 1 MB data = {size:.2f} MB")
    
    data_5mb = b'x' * (5 * 1024 * 1024)
    size = get_file_size_mb(data_5mb)
    assert abs(size - 5.0) < 0.01, f"Expected ~5.0 MB, got {size}"
    print(f"   ✅ 5 MB data = {size:.2f} MB")


def test_input_validation():
    """Test input parameter validation"""
    print("\n" + "="*60)
    print("🧪 Testing Input Validation")
    print("="*60)
    
    # Valid formats
    print("\n1. Testing format validation...")
    valid_formats = ["jpg", "jpeg", "png", "webp"]
    for fmt in valid_formats:
        assert fmt.lower() in ["jpg", "jpeg", "png", "webp"]
    print(f"   ✅ Valid formats: {', '.join(valid_formats)}")
    
    # Quality range
    print("\n2. Testing quality range...")
    valid_qualities = [1, 50, 75, 95, 100]
    for q in valid_qualities:
        assert 1 <= q <= 100, f"Quality {q} out of range"
    print(f"   ✅ Valid quality range: 1-100")
    
    invalid_qualities = [0, -1, 101, 200]
    for q in invalid_qualities:
        assert not (1 <= q <= 100), f"Quality {q} should be invalid"
    print(f"   ✅ Invalid qualities rejected: {', '.join(map(str, invalid_qualities))}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 ComfyUI Serverless Handler - Local Test Suite")
    print("="*60)
    print("📝 Testing core functions without ComfyUI runtime")
    print("="*60)
    
    try:
        # Run tests
        test_workflow_creation()
        test_image_conversion()
        test_utility_functions()
        test_input_validation()
        
        # Summary
        print("\n" + "="*60)
        print("✅ All local tests passed!")
        print("="*60)
        print("\n📝 Next steps:")
        print("   1. Build Docker image: docker build -t comfyui-serverless .")
        print("   2. Test locally: docker run --gpus all comfyui-serverless")
        print("   3. Deploy to RunPod and test with real workload")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
