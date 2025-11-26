import base64
from PIL import Image
import io

# ----- your base64 string here -----
base64_str = ""  

# Decode the base64 string into bytes
image_bytes = base64.b64decode(base64_str)

# Convert bytes to an image using Pillow
image = Image.open(io.BytesIO(image_bytes))

# Ensure correct format and mode (RGB for JPG)
if image.mode != "RGB":
    image = image.convert("RGB")

# Save the image properly as JPG
output_path = "output_image.jpg"
image.save(output_path, format="JPEG", quality=95)

print("Saved:", output_path)
print("Format:", image.format)
print("Size:", image.size)
print("Mode:", image.mode)
