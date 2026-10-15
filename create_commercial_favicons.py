# -*- coding: utf-8 -*-
"""
生成全國商辦與企業地圖的專屬小圖示 (Favicons & Apple Touch Icon)
設計語彙：商辦大樓群天際線 (Commercial Skyscraper Skyline) + 科技弱電藍與金光
"""

import os
from PIL import Image, ImageDraw

def create_favicons():
    # 1. Generate SVG Favicon (Crisp vector for modern browsers)
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#1E293B"/>
    </linearGradient>
    <linearGradient id="bldGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
    <linearGradient id="bldGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#D97706"/>
    </linearGradient>
    <linearGradient id="bldGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#818CF8"/>
      <stop offset="100%" stop-color="#4F46E5"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Rounded App Background -->
  <rect x="6" y="6" width="116" height="116" rx="28" fill="url(#bgGrad)" stroke="#38BDF8" stroke-width="3" stroke-opacity="0.6"/>

  <!-- Left Skyscraper -->
  <rect x="22" y="44" width="22" height="64" rx="3" fill="url(#bldGrad3)"/>
  <!-- Windows -->
  <rect x="26" y="50" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="35" y="50" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="26" y="60" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="35" y="60" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="26" y="70" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="35" y="70" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="26" y="80" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="35" y="80" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>

  <!-- Center Landmark Skyscraper -->
  <polygon points="64,16 52,28 76,28" fill="#F59E0B"/>
  <rect x="50" y="28" width="28" height="80" rx="3" fill="url(#bldGrad1)" filter="url(#glow)"/>
  <!-- Center Windows -->
  <rect x="55" y="36" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="67" y="36" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="55" y="48" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="67" y="48" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="55" y="60" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="67" y="60" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="55" y="72" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="67" y="72" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="55" y="84" width="6" height="6" rx="1" fill="#FFFFFF"/>
  <rect x="67" y="84" width="6" height="6" rx="1" fill="#FFFFFF"/>

  <!-- Right Skyscraper -->
  <rect x="84" y="52" width="22" height="56" rx="3" fill="url(#bldGrad2)"/>
  <!-- Right Windows -->
  <rect x="88" y="58" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="97" y="58" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="88" y="68" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="97" y="68" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="88" y="78" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
  <rect x="97" y="78" width="5" height="5" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>

  <!-- Base Ground Line -->
  <line x1="16" y1="108" x2="112" y2="108" stroke="#38BDF8" stroke-width="3" stroke-linecap="round"/>
</svg>'''

    with open('favicon.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("[OK] 成功生成 favicon.svg")

    # 2. Render PNG & ICO with Pillow
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark background pill
    margin = 24
    draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=110, fill=(15, 23, 42, 255), outline=(56, 189, 248, 220), width=10)

    # Left building (Indigo)
    draw.rounded_rectangle([90, 180, 180, 440], radius=12, fill=(79, 70, 229, 255))
    # Windows
    for wy in range(210, 420, 45):
        draw.rounded_rectangle([108, wy, 128, wy + 22], radius=4, fill=(255, 255, 255, 240))
        draw.rounded_rectangle([142, wy, 162, wy + 22], radius=4, fill=(255, 255, 255, 240))

    # Right building (Amber)
    draw.rounded_rectangle([332, 210, 422, 440], radius=12, fill=(217, 119, 6, 255))
    for wy in range(235, 420, 45):
        draw.rounded_rectangle([350, wy, 370, wy + 22], radius=4, fill=(255, 255, 255, 240))
        draw.rounded_rectangle([384, wy, 404, wy + 22], radius=4, fill=(255, 255, 255, 240))

    # Center Main Tower (Sky Blue)
    draw.polygon([(256, 70), (200, 120), (312, 120)], fill=(245, 158, 11, 255))
    draw.rounded_rectangle([200, 120, 312, 440], radius=14, fill=(2, 132, 199, 255), outline=(56, 189, 248, 255), width=6)
    for wy in range(150, 420, 48):
        draw.rounded_rectangle([222, wy, 246, wy + 26], radius=5, fill=(255, 255, 255, 255))
        draw.rounded_rectangle([266, wy, 290, wy + 26], radius=5, fill=(255, 255, 255, 255))

    # Base line
    draw.line([(70, 440), (442, 440)], fill=(56, 189, 248, 255), width=12)

    # Save multiple PNG sizes
    img.save('icon-512.png', 'PNG')
    img.resize((192, 192), Image.Resampling.LANCZOS).save('icon-192.png', 'PNG')
    img.resize((180, 180), Image.Resampling.LANCZOS).save('apple-touch-icon.png', 'PNG')
    img.resize((32, 32), Image.Resampling.LANCZOS).save('favicon-32x32.png', 'PNG')
    img.resize((16, 16), Image.Resampling.LANCZOS).save('favicon-16x16.png', 'PNG')

    # Save multi-res ICO
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    img.save('favicon.ico', format='ICO', sizes=ico_sizes)
    print("[OK] 成功生成 favicon.ico, apple-touch-icon.png, 及各尺寸 PNG 圖示！")

if __name__ == '__main__':
    create_favicons()
