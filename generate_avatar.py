#!/usr/bin/env python3
"""Generate avatar image via RunPod endpoint.

Usage:
  python generate_avatar.py "Your prompt here"

Reads RUNPOD_API_KEY from .env (key name: RUNPOD_API_KEY).
Sends request to the provided RunPod serverless endpoint.
Waits for response (can take ~2 minutes) and saves the first image
returned under avatar_images/ with a name derived from the prompt initials.

Filename pattern: <initials>_<shortId>.jpg
Where <initials> are the first letters of up to 4 words in the prompt.
shortId is first 8 hex chars of the task id for uniqueness.

If multiple images returned, they will be enumerated: <initials>_<shortId>_1.jpg etc.
"""
from __future__ import annotations
import os
import sys
import time
import json
import base64
from pathlib import Path
from typing import List

import requests

from dotenv import load_dotenv

load_dotenv()

RUNPOD_ENDPOINT = "https://api.runpod.ai/v2/6qtbu2qnofk4m6/run"
OUTPUT_DIR = Path(__file__).parent / "avatar_images"
ENV_FILE = Path(__file__).parent / ".env"
API_KEY_ENV = "RUNPOD_API_KEY"
TIMEOUT_SECS = 300  # generous timeout (> 2 min)


def load_api_key() -> str:
    """Load API key from environment / .env file."""
    if load_dotenv and ENV_FILE.exists():
        load_dotenv(ENV_FILE)  # populate environment
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        raise SystemExit(f"Missing {API_KEY_ENV} in environment/.env")
    return api_key


def prompt_initials(prompt: str, max_words: int = 4) -> str:
    words = [w for w in prompt.strip().split() if w]
    initials = ''.join(w[0].lower() for w in words[:max_words])
    return initials or "img"


def save_images(images: List[dict], initials: str, task_id: str) -> List[Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    short_id = task_id.split('-')[0][:8] if task_id else f"{int(time.time())}"  # fallback
    saved_paths: List[Path] = []
    for idx, img_entry in enumerate(images, start=1):
        b64_data = img_entry.get("image")
        if not b64_data:
            continue
        # Some APIs might return data URI; strip prefix if exists
        if b64_data.startswith("data:image"):
            b64_data = b64_data.split(",", 1)[-1]
        try:
            binary = base64.b64decode(b64_data)
        except Exception as e:
            print(f"Failed to decode image {idx}: {e}")
            continue
        suffix = f"_{idx}" if len(images) > 1 else ""
        filename = f"{initials}_{short_id}{suffix}.jpg"
        path = OUTPUT_DIR / filename
        with open(path, "wb") as f:
            f.write(binary)
        saved_paths.append(path)
    return saved_paths


def request_avatar(api_key: str, prompt: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {"input": {"prompt": prompt}}
    resp = requests.post(RUNPOD_ENDPOINT, headers=headers, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"Request failed {resp.status_code}: {resp.text}")
    data = resp.json()
    return data


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    prompt = argv[1]
    api_key = load_api_key()
    print(f"Sending request for prompt: {prompt}")
    start = time.time()
    try:
        data = request_avatar(api_key, prompt)
    except Exception as e:
        print(f"Error calling endpoint: {e}")
        return 1
    elapsed = time.time() - start
    print(f"Response received in {elapsed:.1f}s")

    # Expect 'output'->'images'
    output = data.get("output", {})
    images = output.get("images") or []
    if not images:
        print("No images in response:", json.dumps(data, indent=2)[:500])
        return 3

    initials = prompt_initials(prompt)
    saved_paths = save_images(images, initials, data.get("id", ""))
    for p in saved_paths:
        print(f"Saved: {p}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
