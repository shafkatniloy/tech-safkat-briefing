#!/usr/bin/env python3
import math
import os
from PIL import Image, ImageDraw, ImageFont

def generate_photocard(source_img_path, output_jpg_path):
    # 1. Load and square-crop high-res photo (center crop)
    base = Image.open(source_img_path).convert("RGB")
    bw, bh = base.size
    min_dim = min(bw, bh)
    left = (bw - min_dim) // 2
    top = (bh - min_dim) // 2
    square = base.crop((left, top, left + min_dim, top + min_dim)).resize((1080, 1080), Image.Resampling.LANCZOS)

    # 2. Build layered gradients
    overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Top subtle shadow (y: 0 to 160)
    for y in range(160):
        t = y / 160.0
        alpha = int(140 * ((1.0 - t) ** 1.8))
        draw_overlay.line([(0, y), (1080, y)], fill=(5, 5, 8, alpha))

    # Bottom gradient fade (deep #050508 on bottom 42%, starting y=560)
    grad_start = 560
    grad_end = 900
    for y in range(grad_start, 1080):
        if y < grad_end:
            t = (y - grad_start) / (grad_end - grad_start)
            # Apple-style smooth cubic ease
            ease = 3 * (t ** 2) - 2 * (t ** 3)
            alpha = int(255 * ease)
        else:
            alpha = 255
        draw_overlay.line([(0, y), (1080, y)], fill=(5, 5, 8, alpha))

    # Composite base image and gradient overlay
    canvas = Image.alpha_composite(square.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    # 3. Fonts
    font_watermark = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 22)
    font_emoji = ImageFont.truetype("/usr/share/fonts/google-noto-emoji-fonts/NotoEmoji-Regular.ttf", 21)
    font_pill_text = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 19)
    font_headline = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 54)
    font_summary = ImageFont.truetype("/usr/share/fonts/msttcore/arial.ttf", 23)
    font_tag = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 17)
    font_brand = ImageFont.truetype("/usr/share/fonts/msttcore/arialbd.ttf", 18)

    # Margin constants
    left_margin = 64
    right_margin = 1016

    # 4. Top-left Watermark
    watermark_text = "TECH-SAFKAT • TECH NEWS"
    draw.text((left_margin, 54), watermark_text, font=font_watermark, fill=(255, 255, 255, 235))

    # 5. Highlight Pill
    pill_text = "AUTONOMOUS AI AGENT"
    bbox_e = font_emoji.getbbox("🔥")
    bbox_t = font_pill_text.getbbox(pill_text)

    ew, eh = bbox_e[2] - bbox_e[0], bbox_e[3] - bbox_e[1]
    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]

    gap = 8
    pad_x = 18
    pad_y = 9
    pill_w = pad_x * 2 + ew + gap + tw
    pill_h = pad_y * 2 + max(eh, th)

    pill_x = left_margin
    pill_y = 662
    pill_box = [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h]

    # Pill background with vibrant rose-red (#E11D48) and subtle polished border
    draw.rounded_rectangle(pill_box, radius=pill_h // 2, fill=(225, 29, 72, 255))
    draw.rounded_rectangle(pill_box, radius=pill_h // 2, outline=(255, 255, 255, 75), width=1)

    # Pill contents
    draw.text((pill_x + pad_x, pill_y + pad_y - 2), "🔥", font=font_emoji, fill=(255, 255, 255, 255))
    draw.text((pill_x + pad_x + ew + gap, pill_y + pad_y), pill_text, font=font_pill_text, fill=(255, 255, 255, 255))

    # 6. Main Headline (massive, bold white, 2 lines)
    hl_line1 = "Apple Races to Turn Siri"
    hl_line2 = "Into Autonomous Agent"
    draw.text((left_margin, 728), hl_line1, font=font_headline, fill=(255, 255, 255, 255))
    draw.text((left_margin, 794), hl_line2, font=font_headline, fill=(255, 255, 255, 255))

    # 7. Single-line summary
    summary_text = "CEO John Ternus pushes software chief to accelerate next-gen AI roadmap."
    draw.text((left_margin, 874), summary_text, font=font_summary, fill=(203, 213, 225, 255))

    # 8. Clean bottom divider line
    draw.line([(left_margin, 946), (right_margin, 946)], fill=(203, 213, 225, 45), width=1)

    # 9. Bottom Footer
    topic_tag = "ARTIFICIAL INTELLIGENCE"
    brand_text = "fb.com/Tech-Safkat"
    brand_bbox = font_brand.getbbox(brand_text)
    brand_w = brand_bbox[2] - brand_bbox[0]

    draw.text((left_margin, 974), topic_tag, font=font_tag, fill=(148, 163, 184, 255))
    draw.text((right_margin - brand_w, 974), brand_text, font=font_brand, fill=(203, 213, 225, 255))

    # 10. Export optimized JPEG (< 400 KB)
    final = canvas.convert("RGB")
    final.save(output_jpg_path, "JPEG", quality=88, optimize=True)
    size_kb = os.path.getsize(output_jpg_path) / 1024
    print(f"Generated {output_jpg_path} successfully ({size_kb:.1f} KB)")
    return output_jpg_path

if __name__ == "__main__":
    generate_photocard("/tmp/verge_siri.jpg", "/home/safkatniloy/.gemini/antigravity/scratch/tech-safkat-briefing/tech_safkat_card.jpg")
