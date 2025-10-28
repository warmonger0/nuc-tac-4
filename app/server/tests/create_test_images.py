#!/usr/bin/env python3
"""
Script to create simple test images for testing the image upload functionality.
"""
import os
from pathlib import Path

# Create test images directory
test_images_dir = Path(__file__).parent / "test_images"
test_images_dir.mkdir(exist_ok=True)

# PNG file (1x1 red pixel)
png_data = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c49444154089963f8cfc00000030001fa27a7b20000000049454e"
    "44ae426082"
)

with open(test_images_dir / "sample.png", "wb") as f:
    f.write(png_data)

# JPEG file (minimal valid JPEG - 1x1 white pixel)
jpeg_data = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605"
    "08070707090909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c2028"
    "2224221c1c2832292c2e2f2e2d1d252938333d3c33373c2e30ffdb00430109"
    "09090c0a0c180d0d18322"
    "11c21323232323232323232323232323232323232323232323232323232323"
    "232323232323232323232323232323232323232ffc00011080001000103012"
    "200021101031101ffc4001500010100000000000000000000000000000000"
    "ffc4001401000000000000000000000000000000ffda000c030100021103110"
    "03f0063800f00ffd9"
)

with open(test_images_dir / "sample.jpg", "wb") as f:
    f.write(jpeg_data)

# GIF file (1x1 transparent pixel)
gif_data = bytes.fromhex(
    "47494638396101000100f00000000000ffffff21f90401000000002c00000"
    "0000100010000020144003b"
)

with open(test_images_dir / "sample.gif", "wb") as f:
    f.write(gif_data)

# WebP file (minimal valid WebP - 1x1 white pixel)
webp_data = bytes.fromhex(
    "524946462600000057454250565038204c0000002f0000001007001125ff"
    "fff700009d012a010001004175030003eb2a1100000000"
)

with open(test_images_dir / "sample.webp", "wb") as f:
    f.write(webp_data)

# BMP file (1x1 red pixel)
bmp_data = bytes.fromhex(
    "424d3a0000000000000036000000280000000100000001000000010018000"
    "00000000400000000000000000000000000000000000000000000ff0000"
)

with open(test_images_dir / "sample.bmp", "wb") as f:
    f.write(bmp_data)

print("Test images created successfully:")
for file in test_images_dir.iterdir():
    if file.is_file():
        print(f"  - {file.name} ({file.stat().st_size} bytes)")
