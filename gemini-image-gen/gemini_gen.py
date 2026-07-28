r"""Generate (and edit) images via the Gemini API image models.

Portable single-file tool. Import it or run it from the command line.

  from gemini_gen import generate
  generate("a red bicycle on a white background", "out.png")
  generate("put this logo on a coffee mug", "mug.png", images=["logo.png"])

  python gemini_gen.py "a red bicycle on a white background" -o out.png
  python gemini_gen.py "PROMPT" -o out.png --size 4K --model gemini-3.1-flash-image
  python gemini_gen.py "make the sky purple" -o edited.png -i original.png

API KEY (checked in this order):
  1. env GEMINI_API_KEY
  2. env GEMINI_API_KEY_FILE (path to a one-line file)
  3. gemini_api_key.txt next to this script
  4. gemini_api_key.txt in the current directory
  5. secrets/gemini_api_key.txt in the current directory
Get a key at https://aistudio.google.com/apikey
"""
import argparse
import base64
import os
import sys
import time

import requests

API = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.1-flash-image"

# Only requests is required. Pillow is optional and used purely to print the
# output dimensions after a CLI run; the library never depends on it.
try:
    from PIL import Image
except ImportError:
    Image = None


def api_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("GEMINI_API_KEY_FILE"),
        os.path.join(here, "gemini_api_key.txt"),
        os.path.join(os.getcwd(), "gemini_api_key.txt"),
        os.path.join(os.getcwd(), "secrets", "gemini_api_key.txt"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            with open(path, encoding="utf-8-sig") as f:  # utf-8-sig strips a BOM
                key = f.read().strip()
            if key:
                return key
    sys.exit(
        "No Gemini API key found. Set GEMINI_API_KEY, or put the key in a file "
        "named gemini_api_key.txt next to this script. Get one at "
        "https://aistudio.google.com/apikey"
    )


def image_part(path):
    """Inline an existing image so the model can edit or composite it."""
    ext = os.path.splitext(path)[1].lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp"}.get(ext)
    if not mime:
        sys.exit(f"Unsupported input image type: {path}")
    with open(path, "rb") as f:
        return {"inlineData": {"mimeType": mime,
                               "data": base64.b64encode(f.read()).decode()}}


def generate(prompt, out_path, model=DEFAULT_MODEL, size="2K", aspect="1:1",
             retries=5, images=()):
    """Generate one image to out_path and return the path.

    prompt   the text instruction
    images   optional paths to input images; they come first so the model
             treats them as the subject and the prompt as the edit instruction
    size     "1K" | "2K" | "4K"
    aspect   e.g. "1:1", "16:9", "4:5"
    """
    parts = [image_part(p) for p in images] + [{"text": prompt}]
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect, "imageSize": size},
        },
    }
    delay = 5
    for attempt in range(retries):
        r = requests.post(f"{API}/models/{model}:generateContent",
                          headers={"x-goog-api-key": api_key()},
                          json=body, timeout=300)
        if r.status_code in (429, 500, 502, 503):
            print(f"  {r.status_code}, retry in {delay}s ({attempt + 1}/{retries})")
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        if not r.ok:
            sys.exit(f"Gemini {r.status_code}: {r.text[:1500]}")
        parts = r.json()["candidates"][0]["content"]["parts"]
        blobs = [p["inlineData"] for p in parts if "inlineData" in p]
        if not blobs:
            texts = " ".join(p.get("text", "") for p in parts)[:300]
            sys.exit(f"No image in response; model said: {texts}")
        data = base64.b64decode(blobs[0]["data"])
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(data)
        return out_path
    sys.exit("Gemini: retries exhausted (rate limited).")


def main():
    ap = argparse.ArgumentParser(description="Generate images via the Gemini API.")
    ap.add_argument("prompt")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--size", default="2K", help="1K | 2K | 4K")
    ap.add_argument("--aspect", default="1:1", help="e.g. 1:1, 16:9, 4:5")
    ap.add_argument("-i", "--image", action="append", default=[],
                    help="input image to edit or composite; repeatable")
    args = ap.parse_args()

    generate(args.prompt, args.output, args.model, args.size, args.aspect,
             images=args.image)
    if Image is not None:
        with Image.open(args.output) as im:
            print(f"OK {args.output}  {im.size[0]}x{im.size[1]}  "
                  f"{os.path.getsize(args.output) // 1024} KB")
    else:
        print(f"OK {args.output}  {os.path.getsize(args.output) // 1024} KB")


if __name__ == "__main__":
    main()
