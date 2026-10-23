"""Original worksheet fixtures and bounded image input validation."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import warnings

from PIL import Image, UnidentifiedImageError

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "worksheets"
from .sample_cases import SAMPLES


def image_input(name: str, data: bytes) -> dict:
    if not data or len(data) > 5 * 1024 * 1024:
        raise ValueError("Use an image smaller than 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in ("PNG", "JPEG") or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Use a single-page PNG or JPEG image.")
                if image.width * image.height > 12_000_000 or max(image.size) > 6000:
                    raise ValueError("Use an image up to 12 megapixels and 6,000 pixels per side.")
                mime = Image.MIME[image.format]
                image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("This image could not be read. Export a clear PNG or JPEG and try again.") from None
    fingerprint = sha256(data).hexdigest()
    sample = next((s for s in SAMPLES if (ASSETS / f"{s['id']}.png").is_file()
                   and sha256((ASSETS / f"{s['id']}.png").read_bytes()).hexdigest() == fingerprint), None)
    return {"id": fingerprint, "name": name[:160], "bytes": data, "mime": mime,
            "text": sample["text"] if sample else "", "method": "Bundled sample transcript · no AI" if sample else "Manual transcription",
            "uncertainties": []}


def prepare_images(files: list[tuple[str, bytes]]) -> list[dict]:
    if not 1 <= len(files) <= 3:
        raise ValueError("Choose one to three worksheet images.")
    result = [image_input(name, data) for name, data in files]
    if len({i["id"] for i in result}) != len(result):
        raise ValueError("Remove duplicate images before continuing.")
    return result

