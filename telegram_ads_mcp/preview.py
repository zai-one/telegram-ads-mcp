"""Render a Telegram-style sponsored-message card as PNG."""

from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("telegram_ads_mcp.preview")

DEFAULT_DIR = Path(os.environ.get("TG_ADS_PREVIEW_DIR", "previews")).resolve()


def preview_dir() -> Path:
    path = DEFAULT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_card(
    *,
    ad_id: str,
    title: str,
    text: str,
    promote_url: str,
    image_bytes: bytes | None = None,
    cpm: str | None = None,
    status: str | None = None,
) -> tuple[bytes, Path]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required to render preview PNGs") from exc

    width, height = 720, 420
    bg = (24, 37, 51)
    card = (33, 51, 69)
    accent = (110, 166, 232)
    text_color = (255, 255, 255)
    muted = (170, 186, 201)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 18)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        font_title = font_body = font_small = ImageFont.load_default()

    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=18, fill=card)
    draw.text((48, 40), "Sponsored message · Telegram Ads", fill=accent, font=font_small)
    draw.text((48, 68), (title or f"Ad {ad_id}")[:60], fill=text_color, font=font_title)

    y = 110
    thumb_w = 0
    if image_bytes:
        try:
            thumb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            thumb.thumbnail((200, 112))
            img.paste(thumb, (48, y))
            thumb_w = thumb.size[0] + 16
        except Exception as exc:  # noqa: BLE001
            log.debug("could not paste creative: %s", exc)

    body = (text or "").strip() or "(no text)"
    wrapped = _wrap(body, 42)
    tx = 48 + thumb_w
    for i, line in enumerate(wrapped[:5]):
        draw.text((tx, y + i * 24), line, fill=text_color, font=font_body)

    btn_y = 280
    btn_label = "OPEN"
    if promote_url:
        btn_label = promote_url.replace("https://", "").replace("http://", "")[:40]
    draw.rounded_rectangle((48, btn_y, width - 48, btn_y + 44), radius=10, fill=accent)
    draw.text((64, btn_y + 12), btn_label, fill=(24, 37, 51), font=font_body)

    meta = []
    if cpm:
        meta.append(f"CPM {cpm}")
    if status is not None:
        meta.append(f"status {status}")
    meta.append(f"id {ad_id}")
    draw.text((48, 344), " · ".join(meta), fill=muted, font=font_small)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png = buf.getvalue()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = preview_dir() / f"ad-{ad_id}-{stamp}.png"
    path.write_bytes(png)
    return png, path


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
