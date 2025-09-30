#!/usr/bin/env python3
"""
创建最终测试logo
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_final_test_logo():
    """创建一个最终测试logo"""
    # 创建250x100的图片
    img = Image.new('RGB', (250, 100), (255, 255, 255))  # 白色背景
    draw = ImageDraw.Draw(img)
    
    # 绘制背景渐变
    for y in range(100):
        color = int(240 - (y * 40 / 100))
        draw.line([(0, y), (250, y)], fill=(color, color + 10, 255))
    
    # 绘制logo元素
    # 左侧图标
    draw.ellipse([20, 20, 70, 70], fill=(52, 152, 219), outline=(255, 255, 255), width=3)
    draw.ellipse([35, 35, 55, 55], fill=(255, 255, 255))
    
    # 中间文字
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((90, 30), "FINAL TEST", fill=(255, 255, 255), font=font_large)
    draw.text((90, 60), "Logo Upload", fill=(255, 255, 255), font=font_small)
    
    # 右侧装饰
    for i in range(3):
        x = 200 + i * 12
        draw.rectangle([x, 25, x+8, 75], fill=(255, 255, 255))
    
    # 保存为PNG文件
    img.save('final-test-logo.png', 'PNG')
    print("最终测试logo已创建: final-test-logo.png")
    print(f"尺寸: {img.size}")

if __name__ == "__main__":
    create_final_test_logo()
