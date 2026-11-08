#!/usr/bin/env python3
"""
Daily Tech-Safkat Facebook Briefing Generator
Automates fetching the top tech story, designing the minimalist photocard,
uploading to a public host, and publishing via Facebook Pages API.
"""

import os
import sys
import json
import math
import urllib.request
import xml.etree.ElementTree as ET
import re
from PIL import Image, ImageDraw, ImageFont

SCRATCH_DIR = "/home/safkatniloy/.gemini/antigravity/scratch/tech-safkat-briefing"
os.makedirs(SCRATCH_DIR, exist_ok=True)

def fetch_top_tech_story():
    url = "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    content = urllib.request.urlopen(req, timeout=10).read()
    root = ET.fromstring(content)
    items = root.findall(".//item")
    if not items:
        raise RuntimeError("No items found in Google News RSS feed")
    
    # Extract first item
    first_item = items[0]
    title = first_item.find("title").text if first_item.find("title") is not None else ""
    link = first_item.find("link").text if first_item.find("link") is not None else ""
    pubDate = first_item.find("pubDate").text if first_item.find("pubDate") is not None else ""
    source = first_item.find("source").text if first_item.find("source") is not None else ""
    
    return {
        "title": title,
        "link": link,
        "pubDate": pubDate,
        "source": source
    }

def create_photocard(source_img_path, output_jpg_path, headline_l1, headline_l2, pill_text, summary_text, topic_tag="ARTIFICIAL INTELLIGENCE"):
    base = Image.open(source_img_path).convert("RGB")
    bw, bh = base.size
    min_dim = min(bw, bh)
    left = (bw - min_dim) // 2
    top = (bh - min_dim) // 2
    square = base.crop((left, top, left + min_dim, top + min_dim)).resize((1080, 1080), Image.Resampling.LANCZOS)

    overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Top subtle shadow
    for y in range(160):
        t = y / 160.0
        alpha = int(140 * ((1.0 - t) ** 1.8))
        draw_overlay.line([(0, y), (1080, y)], fill=(5, 5, 8, alpha))

    # Bottom gradient fade (deep #050508 on bottom 42%)
    grad_start = 560
    grad_end = 900
    for y in range(grad_start, 1080):
        if y < grad_end:
            t = (y - grad_start) / (grad_end - grad_start)
            ease = 3 * (t ** 2) - 2 * (t ** 3)
            alpha = int(255 * ease)
        else:
            alpha = 255
        draw_overlay.line([(0, y), (1080, y)], fill=(5, 5, 8, alpha))

    canvas = Image.alpha_composite(square.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    font_watermark = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 22)
    font_emoji = ImageFont.truetype("/usr/share/fonts/google-noto-emoji-fonts/NotoEmoji-Regular.ttf", 21)
    font_pill_text = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 19)
    font_headline = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 54)
    font_summary = ImageFont.truetype("/usr/share/fonts/msttcore/arial.ttf", 23)
    font_tag = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 17)
    font_brand = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 18)

    left_margin = 64
    right_margin = 1016

    # Watermark
    draw.text((left_margin, 54), "TECH-SAFKAT • TECH NEWS", font=font_watermark, fill=(255, 255, 255, 235))

    # Pill
    bbox_e = font_emoji.getbbox("🔥")
    bbox_t = font_pill_text.getbbox(pill_text)
    ew, eh = bbox_e[2] - bbox_e[0], bbox_e[3] - bbox_e[1]
    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]

    gap = 8
    pad_x, pad_y = 18, 9
    pill_w = pad_x * 2 + ew + gap + tw
    pill_h = pad_y * 2 + max(eh, th)
    pill_x, pill_y = left_margin, 662
    pill_box = [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h]

    draw.rounded_rectangle(pill_box, radius=pill_h // 2, fill=(225, 29, 72, 255))
    draw.rounded_rectangle(pill_box, radius=pill_h // 2, outline=(255, 255, 255, 75), width=1)
    draw.text((pill_x + pad_x, pill_y + pad_y - 2), "🔥", font=font_emoji, fill=(255, 255, 255, 255))
    draw.text((pill_x + pad_x + ew + gap, pill_y + pad_y), pill_text, font=font_pill_text, fill=(255, 255, 255, 255))

    # Headline
    draw.text((left_margin, 728), headline_l1, font=font_headline, fill=(255, 255, 255, 255))
    draw.text((left_margin, 794), headline_l2, font=font_headline, fill=(255, 255, 255, 255))

    # Summary
    draw.text((left_margin, 874), summary_text, font=font_summary, fill=(203, 213, 225, 255))

    # Divider
    draw.line([(left_margin, 946), (right_margin, 946)], fill=(203, 213, 225, 45), width=1)

    # Footer
    brand_text = "fb.com/Tech-Safkat"
    brand_bbox = font_brand.getbbox(brand_text)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text((left_margin, 974), topic_tag, font=font_tag, fill=(148, 163, 184, 255))
    draw.text((right_margin - brand_w, 974), brand_text, font=font_brand, fill=(203, 213, 225, 255))

    final = canvas.convert("RGB")
    final.save(output_jpg_path, "JPEG", quality=88, optimize=True)
    return output_jpg_path

def upload_image(jpg_path):
    cmd = f'curl -s -F "source=@{jpg_path}" -F "action=upload" -F "key=6d207e02198a847aa98d0a2a901485a5" https://freeimage.host/api/1/upload'
    res = os.popen(cmd).read()
    data = json.loads(res)
    return data["image"]["url"]

if __name__ == "__main__":
    source_img = os.path.join(SCRATCH_DIR, "verge_siri.jpg")
    if not os.path.exists(source_img):
        source_img = "/tmp/verge_siri.jpg"
    
    card_path = os.path.join(SCRATCH_DIR, "tech_safkat_card.jpg")
    create_photocard(
        source_img_path=source_img,
        output_jpg_path=card_path,
        headline_l1="Apple Races to Turn Siri",
        headline_l2="Into Autonomous Agent",
        pill_text="AUTONOMOUS AI AGENT",
        summary_text="CEO John Ternus pushes software chief to accelerate next-gen AI roadmap.",
        topic_tag="ARTIFICIAL INTELLIGENCE"
    )
    size_kb = os.path.getsize(card_path) / 1024
    print(f"Photocard rendered successfully: {card_path} ({size_kb:.1f} KB)")
