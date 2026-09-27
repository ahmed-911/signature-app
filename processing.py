"""Local PDF rendering and deterministic ink extraction; no external services."""
from io import BytesIO
import numpy as np
from PIL import Image
import pypdfium2 as pdfium


def page_count(data, password=None):
    with pdfium.PdfDocument(data, password=password or None) as doc:
        return len(doc)


def render_page(data, index, password=None):
    with pdfium.PdfDocument(data, password=password or None) as doc:
        page = doc[index]
        try:
            w, h = page.get_size()
            scale = min(4.0, 3600 / max(w, h))
            bitmap = page.render(scale=scale)
            try:
                return bitmap.to_pil().convert('RGB').copy()
            finally:
                bitmap.close()
        finally:
            page.close()


def extract_ink(image, cutoff=235, black=True, trim=True):
    """Unmatte dark ink from light paper, preserving antialiased edges.

    cutoff rejects paper noise. Black mode retains original stroke coverage;
    color mode mathematically removes a white matte from colored ink.
    """
    rgb = np.asarray(image.convert('RGB'), dtype=np.float32)
    light = rgb.min(axis=2)
    strength = 255.0 - light
    alpha = np.where(light < cutoff, strength, 0)
    if black:
        color = np.zeros_like(rgb)
    else:
        a = np.maximum(strength / 255.0, 1 / 255.0)[..., None]
        color = np.clip((rgb - 255 * (1 - a)) / a, 0, 255)
    result = Image.fromarray(np.dstack((color, alpha)).astype(np.uint8), 'RGBA')
    bbox = result.getchannel('A').getbbox()
    if bbox is None:
        raise ValueError('لم يظهر حبر داخل التحديد. وسّع المنطقة أو ارفع حساسية الاحتفاظ بالحبر.')
    if trim:
        ink = result.crop(bbox)
        result = Image.new('RGBA', (ink.width + 24, ink.height + 24))
        result.paste(ink, (12, 12))
    return result


def png_bytes(image):
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def checker_preview(image):
    preview = image.copy()
    preview.thumbnail((900, 400))
    y, x = np.indices((preview.height, preview.width))
    grey = np.where((x // 16 + y // 16) % 2, 224, 248).astype(np.uint8)
    bg = Image.fromarray(np.dstack((grey, grey, grey, np.full_like(grey, 255))), 'RGBA')
    return Image.alpha_composite(bg, preview).convert('RGB')
