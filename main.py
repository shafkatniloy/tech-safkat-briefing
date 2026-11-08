#!/usr/bin/env python3
"""
Tech-Safkat Daily Briefing Engine (GitHub Actions Cloud Edition)
Fetches top tech news, designs minimalist GTA-style 1080x1080 photocard,
uploads to public host, and publishes to Facebook Page.
"""

import os
import sys
import json
import math
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Path to fonts
FONT_BOLD = os.path.join(FONTS_DIR, "Arial-Bold.ttf")
FONT_REGULAR = os.path.join(FONTS_DIR, "Arial-Regular.ttf")
FONT_EMOJI = os.path.join(FONTS_DIR, "NotoEmoji-Regular.ttf")


def fetch_top_story():
    """
    Fetches the top tech news from high-quality RSS feeds (The Verge / 9to5Mac / Google News)
    to ensure we have a full story, title, and a high-resolution press image.
    """
    print("Fetching top tech story...")

    # Strategy 1: The Verge RSS (has high-res images in <content> <img> tags)
    try:
        req = urllib.request.Request("https://www.theverge.com/rss/index.xml", headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(content)
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:5]:
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            content_elem = entry.find("{http://www.w3.org/2005/Atom}content")
            link = entry.find("{http://www.w3.org/2005/Atom}link").attrib.get("href", "")
            if content_elem is not None and content_elem.text:
                img_match = re.search(r'<img[^>]+src="([^">]+)"', content_elem.text)
                if img_match:
                    raw_img = img_match.group(1).replace("&#038;", "&")
                    # Clean up Verge crop parameters if needed
                    clean_text = re.sub(r"<[^>]+>", " ", content_elem.text)
                    clean_text = re.sub(r"\s+", " ", clean_text).strip()
                    print(f"Selected story from The Verge: {title}")
                    return {
                        "title": title,
                        "link": link,
                        "image_url": raw_img,
                        "body": clean_text[:1200],
                        "source": "The Verge"
                    }
    except Exception as e:
        print(f"Notice: The Verge feed check skipped: {e}")

    # Strategy 2: 9to5Mac WP API (provides jetpack_featured_media_url)
    try:
        req = urllib.request.Request("https://9to5mac.com/wp-json/wp/v2/posts?per_page=5", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            for post in data:
                img = post.get("jetpack_featured_media_url")
                if img:
                    title = post["title"]["rendered"]
                    clean_text = re.sub(r"<[^>]+>", " ", post["content"]["rendered"])
                    clean_text = re.sub(r"\s+", " ", clean_text).strip()
                    print(f"Selected story from 9to5Mac: {title}")
                    return {
                        "title": title,
                        "link": post.get("link", ""),
                        "image_url": img,
                        "body": clean_text[:1200],
                        "source": "9to5Mac"
                    }
    except Exception as e:
        print(f"Notice: 9to5Mac feed check skipped: {e}")

    # Strategy 3: Google News Tech RSS (Fallback image)
    req = urllib.request.Request(
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    content = urllib.request.urlopen(req, timeout=10).read()
    root = ET.fromstring(content)
    item = root.findall(".//item")[0]
    title = item.find("title").text
    link = item.find("link").text
    
    return {
        "title": title,
        "link": link,
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1600&q=80",
        "body": title,
        "source": "Google News"
    }


def analyze_with_ai_or_heuristic(story):
    """
    Extracts short punchy headline (5-8 words max), standout hook,
    summary, and 3 key takeaways. Uses Gemini API if GEMINI_API_KEY is present,
    otherwise uses smart heuristic parsing.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        print("Analyzing story with Gemini API...")
        try:
            prompt = f"""
You are an editor for Tech-Safkat, a premier tech news media page.
Analyze this news story:
Title: {story['title']}
Body: {story['body']}

Return ONLY valid JSON matching this exact structure:
{{
  "headline_line1": "3-4 words (First line of massive bold poster title)",
  "headline_line2": "3-4 words (Second line of massive bold poster title)",
  "stat_hook": "STANDOUT STAT OR HOOK (2-4 words in all caps, e.g. $50B DEAL, AUTONOMOUS AI AGENT, 4.0 RELEASE)",
  "summary": "Crisp one-sentence subtitle below headline (under 80 characters)",
  "caption_intro": "One engaging sentence explaining why this matters to tech enthusiasts",
  "key_points": [
    "Key takeaway point 1",
    "Key takeaway point 2",
    "Key takeaway point 3"
  ],
  "topic_tags": "#TechNews #TechSafkat #Technology #AI"
}}
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }).encode("utf-8")
            
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode())
                text_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_content)
        except Exception as e:
            print(f"Gemini API analysis failed ({e}), falling back to heuristic...")

    # Heuristic fallback
    print("Using rule-based heuristic formatter...")
    words = story["title"].split(" - ")[0].split()
    half = len(words) // 2
    l1 = " ".join(words[:half]) if half > 0 else story["title"][:25]
    l2 = " ".join(words[half:]) if half > 0 else story["title"][25:50]
    
    return {
        "headline_line1": l1[:32],
        "headline_line2": l2[:32],
        "stat_hook": "BREAKING TECH UPDATE",
        "summary": "Latest major tech developments and industry implications.",
        "caption_intro": f"Major tech news from {story['source']}: {story['title']}",
        "key_points": [
            "Major industry shift announced with far-reaching ecosystem impacts.",
            "Key engineering and software roadmap milestones revealed.",
            "Expected to roll out to mainstream consumer devices in upcoming updates."
        ],
        "topic_tags": "#TechNews #TechSafkat #Technology"
    }


def generate_poster(image_url, analyzed_data, output_path):
    print(f"Downloading high-res artwork from {image_url}...")
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    temp_img = os.path.join(OUTPUT_DIR, "source_temp.jpg")
    with urllib.request.urlopen(req, timeout=15) as resp, open(temp_img, "wb") as f:
        f.write(resp.read())

    base = Image.open(temp_img).convert("RGB")
    bw, bh = base.size
    min_dim = min(bw, bh)
    left = (bw - min_dim) // 2
    top = (bh - min_dim) // 2
    square = base.crop((left, top, left + min_dim, top + min_dim)).resize((1080, 1080), Image.Resampling.LANCZOS)

    overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Top shadow
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

    font_watermark = ImageFont.truetype(FONT_BOLD, 22)
    font_emoji = ImageFont.truetype(FONT_EMOJI, 21)
    font_pill_text = ImageFont.truetype(FONT_BOLD, 19)
    font_headline = ImageFont.truetype(FONT_BOLD, 54)
    font_summary = ImageFont.truetype(FONT_REGULAR, 23)
    font_tag = ImageFont.truetype(FONT_BOLD, 17)
    font_brand = ImageFont.truetype(FONT_BOLD, 18)

    left_margin = 64
    right_margin = 1016

    # 1. Watermark
    draw.text((left_margin, 54), "TECH-SAFKAT • TECH NEWS", font=font_watermark, fill=(255, 255, 255, 235))

    # 2. Highlight Pill
    pill_text = analyzed_data.get("stat_hook", "BREAKING TECH UPDATE").upper()
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

    # 3. Headline
    hl1 = analyzed_data.get("headline_line1", "")
    hl2 = analyzed_data.get("headline_line2", "")
    draw.text((left_margin, 728), hl1, font=font_headline, fill=(255, 255, 255, 255))
    draw.text((left_margin, 794), hl2, font=font_headline, fill=(255, 255, 255, 255))

    # 4. Summary
    draw.text((left_margin, 874), analyzed_data.get("summary", ""), font=font_summary, fill=(203, 213, 225, 255))

    # 5. Divider
    draw.line([(left_margin, 946), (right_margin, 946)], fill=(203, 213, 225, 45), width=1)

    # 6. Footer
    brand_text = "fb.com/Tech-Safkat"
    brand_bbox = font_brand.getbbox(brand_text)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text((left_margin, 974), "TECHNOLOGY & INNOVATION", font=font_tag, fill=(148, 163, 184, 255))
    draw.text((right_margin - brand_w, 974), brand_text, font=font_brand, fill=(203, 213, 225, 255))

    final = canvas.convert("RGB")
    final.save(output_path, "JPEG", quality=88, optimize=True)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Photocard saved to {output_path} ({size_kb:.1f} KB)")
    return output_path


def upload_to_freeimage(image_path):
    print("Uploading photocard to public host...")
    try:
        cmd = f'curl -s -F "source=@{image_path}" -F "action=upload" -F "key=6d207e02198a847aa98d0a2a901485a5" https://freeimage.host/api/1/upload'
        res = os.popen(cmd).read()
        data = json.loads(res)
        url = data["image"]["url"]
        print(f"Public image URL: {url}")
        return url
    except Exception as e:
        print(f"Notice: freeimage.host upload failed ({e}), trying catbox fallback...")
        cmd2 = f'curl -s -F "fileToUpload=@{image_path}" -F "reqtype=fileupload" https://catbox.moe/user/api.php'
        url = os.popen(cmd2).read().strip()
        print(f"Public image URL (catbox): {url}")
        return url


def publish_post(image_url, analyzed_data, full_headline):
    points = analyzed_data.get("key_points", [])
    p1 = points[0] if len(points) > 0 else "Exciting strategic roadmap shift announced."
    p2 = points[1] if len(points) > 1 else "Direct implications for consumer tech products."
    p3 = points[2] if len(points) > 2 else "Expected to roll out to global users in upcoming releases."

    message = f"""🚨 BREAKING: {full_headline}

{analyzed_data.get('caption_intro', '')}

⚡ Key Takeaways:
🔹 {p1}
🔹 {p2}
🔹 {p3}

What are your thoughts on this? Drop a comment below! 👇

{analyzed_data.get('topic_tags', '#TechNews #TechSafkat #Technology')}"""

    # Check for Zapier Webhook URL first (Easiest & most reliable)
    zapier_hook = os.environ.get("ZAPIER_WEBHOOK_URL")
    if zapier_hook:
        print(f"Triggering Zapier Webhook to post to Facebook...")
        payload = json.dumps({
            "image_url": image_url,
            "message": message,
            "headline": full_headline,
            "page_id": "1228167307048422"
        }).encode("utf-8")
        req = urllib.request.Request(zapier_hook, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("Zapier webhook response status:", resp.status)
        return True

    # Check for Direct Facebook Graph API Token
    fb_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID", "1228167307048422")
    if fb_token:
        print(f"Publishing via Facebook Graph API to Page {fb_page_id}...")
        api_url = f"https://graph.facebook.com/v20.0/{fb_page_id}/photos"
        post_data = urllib.parse.urlencode({
            "url": image_url,
            "message": message,
            "access_token": fb_token
        }).encode("utf-8")
        req = urllib.request.Request(api_url, data=post_data)
        with urllib.request.urlopen(req, timeout=20) as resp:
            res = json.loads(resp.read().decode())
            print(f"Published successfully! Post ID: {res.get('post_id')}, Photo ID: {res.get('id')}")
        return True

    print("⚠️ No ZAPIER_WEBHOOK_URL or FB_PAGE_ACCESS_TOKEN found.")
    print("Photocard generated and uploaded, but Facebook publish was skipped (dry run).")
    return False


def main():
    story = fetch_top_story()
    analyzed = analyze_with_ai_or_heuristic(story)
    
    full_headline = f"{analyzed.get('headline_line1', '')} {analyzed.get('headline_line2', '')}".strip()
    if not full_headline:
        full_headline = story["title"]

    card_path = os.path.join(OUTPUT_DIR, "tech_safkat_card.jpg")
    generate_poster(story["image_url"], analyzed, card_path)
    
    public_url = upload_to_freeimage(card_path)
    publish_post(public_url, analyzed, full_headline)
    print("Daily Tech-Safkat Briefing completed successfully!")


if __name__ == "__main__":
    main()
