"""
Simple test script to verify the updated upload_image.py works correctly
"""
import os
from io import BytesIO
from PIL import Image

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

from upload_image import upload_image


def create_test_image() -> bytes:
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()


def test_upload():
    """Test the upload_image function"""
    print("Testing upload_image with latest Supabase API...")
    
    # Check environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_BUCKET"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        return False

    if not (os.environ.get("SUPABASE_S3_KEY")):
        print("❌ Missing SUPABASE_S3_KEY")
        return False
    
    print(f"✅ Environment variables configured")
    print(f"   URL: {os.environ.get('SUPABASE_URL')}")
    print(f"   Bucket: {os.environ.get('SUPABASE_BUCKET')}")
    
    # Create test image
    image_bytes = create_test_image()
    print(f"✅ Created test image ({len(image_bytes)} bytes)")
    
    # Upload
    result = upload_image(
        image_bytes=image_bytes,
        filename="test_image.jpg",
        content_type="image/jpeg",
        folder="test-uploads"
    )
    
    # Check result
    if result.get("success"):
        print(f"✅ Upload successful!")
        print(f"   Bucket: {result.get('bucket')}")
        print(f"   Path: {result.get('object_path')}")
        print(f"   Public URL: {result.get('public_url')}")
        print(f"   Method: {result.get('method')}")
        return True
    else:
        print(f"❌ Upload failed: {result.get('error')}")
        return False


if __name__ == "__main__":
    success = test_upload()
    exit(0 if success else 1)
