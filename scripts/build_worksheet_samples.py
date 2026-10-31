"""Render the original text worksheets to PNG. Dev dependency: Playwright + Edge."""
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from studybridge.worksheets import ASSETS, SAMPLES

ASSETS.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width":1000,"height":1400}, device_scale_factor=1)
    for sample in SAMPLES:
        blocks = sample["text"].split("\n\n")
        sections = "".join(f'<section>{escape(block).replace(chr(10), "<br>")}</section>' for block in blocks)
        page.set_content(f'''<!doctype html><html><head><meta charset="utf-8"><style>
        *{{box-sizing:border-box}}body{{margin:0;background:#fff;font-family:Arial,sans-serif;color:#183831}}
        article{{width:1000px;min-height:1400px;padding:48px 60px;position:relative}}
        header{{font-size:16px;letter-spacing:2px;color:#087f6b;border-bottom:3px solid #087f6b;padding-bottom:16px;margin-bottom:24px}}
        section{{font-size:21px;line-height:1.55;margin:0 0 22px;white-space:normal}}
        section:first-of-type{{font-size:25px;font-weight:bold}}
        section:nth-of-type(2){{background:#edf3e7;border-left:5px solid #6b9876;border-radius:12px;padding:18px 22px}}
        section:nth-of-type(3){{background:#fff4e5;border-left:5px solid #ce9351;border-radius:12px;padding:18px 22px;color:#614223}}
        footer{{position:absolute;bottom:40px;left:70px;right:70px;border-top:1px solid #cbd9d1;padding-top:17px;font-size:16px;color:#65796f}}
        </style></head><body><article><header>PRACTILUME / SAMPLE LEARNING MATERIAL</header>{sections}
        <footer>Created by Yifan Yan · Original fictional worksheet · For testing, not an official exam</footer></article></body></html>''')
        assert page.locator('section').last.bounding_box()['y'] + page.locator('section').last.bounding_box()['height'] < 1320
        page.locator('article').screenshot(path=str(ASSETS / f"{sample['id']}.png"))
        (ASSETS / f"{sample['id']}.txt").write_text(sample["text"], encoding="utf-8")
    browser.close()
print("Rendered three original worksheet PNGs and matching transcripts.")
