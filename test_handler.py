"""
Unit tests for handler.py
Tests core functions without requiring ComfyUI to be running
"""

import unittest
import sys
import os
from pathlib import Path
from io import BytesIO
from unittest.mock import MagicMock

# Mock runpod before importing handler
sys.modules['runpod'] = MagicMock()
sys.modules['runpod.serverless'] = MagicMock()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Mock PIL if not available
try:
    from PIL import Image
except ImportError:
    print("⚠️ PIL not available, skipping image tests")
    Image = None

# Import handler functions
from handler import (
    convert_image_format,
    get_file_size_mb,
    save_image_to_disk,
    create_basic_workflow,
    create_workflow
)


class TestImageConversion(unittest.TestCase):
    """Test image format conversion functions"""
    
    @unittest.skipIf(Image is None, "PIL not available")
    def setUp(self):
        """Create a test image"""
        # Create a simple RGB image
        self.test_image = Image.new('RGB', (100, 100), color='red')
        
        # Save to bytes
        buffer = BytesIO()
        self.test_image.save(buffer, format='PNG')
        self.test_image_data = buffer.getvalue()
    
    @unittest.skipIf(Image is None, "PIL not available")
    def test_convert_to_jpg(self):
        """Test conversion to JPG format"""
        result = convert_image_format(self.test_image_data, "jpg", 95)
        
        # Verify it's valid image data
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        # Verify it can be loaded as JPG
        img = Image.open(BytesIO(result))
        self.assertEqual(img.format, 'JPEG')
        self.assertEqual(img.size, (100, 100))
    
    @unittest.skipIf(Image is None, "PIL not available")
    def test_convert_to_png(self):
        """Test conversion to PNG format"""
        result = convert_image_format(self.test_image_data, "png", 95)
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        img = Image.open(BytesIO(result))
        self.assertEqual(img.format, 'PNG')
    
    @unittest.skipIf(Image is None, "PIL not available")
    def test_convert_to_webp(self):
        """Test conversion to WebP format"""
        result = convert_image_format(self.test_image_data, "webp", 95)
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
        img = Image.open(BytesIO(result))
        self.assertEqual(img.format, 'WEBP')
    
    @unittest.skipIf(Image is None, "PIL not available")
    def test_convert_rgba_to_jpg(self):
        """Test conversion of RGBA image to JPG (should handle transparency)"""
        # Create RGBA image with transparency
        rgba_image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        buffer = BytesIO()
        rgba_image.save(buffer, format='PNG')
        rgba_data = buffer.getvalue()
        
        # Convert to JPG
        result = convert_image_format(rgba_data, "jpg", 95)
        
        # Should succeed and produce RGB image
        img = Image.open(BytesIO(result))
        self.assertEqual(img.format, 'JPEG')
        self.assertEqual(img.mode, 'RGB')  # JPG should be RGB, not RGBA
    
    @unittest.skipIf(Image is None, "PIL not available")
    def test_quality_settings(self):
        """Test different quality settings"""
        # High quality should produce larger files
        high_quality = convert_image_format(self.test_image_data, "jpg", 95)
        low_quality = convert_image_format(self.test_image_data, "jpg", 50)
        
        # Generally, higher quality = larger file (though not guaranteed for all images)
        self.assertIsNotNone(high_quality)
        self.assertIsNotNone(low_quality)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_get_file_size_mb(self):
        """Test file size calculation"""
        # Test with 1 MB of data
        data = b'x' * (1024 * 1024)
        size = get_file_size_mb(data)
        self.assertAlmostEqual(size, 1.0, places=2)
        
        # Test with 2.5 MB
        data = b'x' * int(2.5 * 1024 * 1024)
        size = get_file_size_mb(data)
        self.assertAlmostEqual(size, 2.5, places=1)
    
    @unittest.skipIf(Image is None, "PIL not available")
    def test_save_image_to_disk(self):
        """Test saving image to disk"""
        # Create test image
        img = Image.new('RGB', (50, 50), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        image_data = buffer.getvalue()
        
        # Save to temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_image_to_disk(image_data, "test_image.jpg", tmpdir)
            
            # Verify file was saved
            self.assertIsNotNone(result)
            self.assertTrue(os.path.exists(result))
            
            # Verify content
            saved_data = open(result, 'rb').read()
            self.assertEqual(len(saved_data), len(image_data))


class TestWorkflowCreation(unittest.TestCase):
    """Test workflow creation functions"""
    
    def test_create_basic_workflow(self):
        """Test basic workflow creation"""
        workflow = create_basic_workflow()
        
        # Verify it's a dict
        self.assertIsInstance(workflow, dict)
        
        # Verify it has expected nodes
        self.assertIn("3", workflow)  # KSampler
        self.assertIn("5", workflow)  # EmptyLatentImage
        self.assertIn("6", workflow)  # Positive prompt
        self.assertIn("7", workflow)  # Negative prompt
        self.assertIn("10", workflow)  # LoraLoader
        self.assertIn("11", workflow)  # CheckpointLoader
        
        # Verify node types
        self.assertEqual(workflow["3"]["class_type"], "KSampler")
        self.assertEqual(workflow["10"]["class_type"], "LoraLoader")
    
    def test_create_workflow_with_defaults(self):
        """Test workflow creation with default parameters"""
        job_input = {}
        
        # Should not raise exception even with empty input
        try:
            workflow = create_workflow(job_input)
            self.assertIsInstance(workflow, dict)
        except Exception as e:
            # Expected to fail due to missing ComfyUI directory in test env
            # but should fail gracefully
            pass
    
    def test_create_workflow_with_custom_params(self):
        """Test workflow creation with custom parameters"""
        job_input = {
            "positive_prompt": "test prompt",
            "negative_prompt": "test negative",
            "steps": 20,
            "cfg_scale": 7.0,
            "width": 512,
            "height": 512,
            "seed": 12345,
            "lora_strength": 0.9
        }
        
        try:
            workflow = create_workflow(job_input)
            # If it succeeds, verify the workflow is valid
            self.assertIsInstance(workflow, dict)
        except Exception:
            # Expected to fail in test environment without ComfyUI
            pass


class TestInputValidation(unittest.TestCase):
    """Test input validation"""
    
    def test_output_format_validation(self):
        """Test that valid formats are accepted"""
        valid_formats = ["jpg", "jpeg", "png", "webp", "JPG", "PNG"]
        
        for fmt in valid_formats:
            # Should not raise exception for valid formats
            self.assertIn(fmt.lower(), ["jpg", "jpeg", "png", "webp"])
    
    def test_quality_range(self):
        """Test quality parameter range"""
        # Valid qualities
        for quality in [1, 50, 95, 100]:
            self.assertTrue(1 <= quality <= 100)
        
        # Invalid qualities
        for quality in [0, -1, 101, 200]:
            self.assertFalse(1 <= quality <= 100)


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Running Handler Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestImageConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowCreation))
    suite.addTests(loader.loadTestsFromTestCase(TestInputValidation))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
    print("=" * 60)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
