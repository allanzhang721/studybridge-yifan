from types import SimpleNamespace
from unittest.mock import Mock

import openai
import pytest

from studybridge import ai
from studybridge.worksheets import ASSETS, SAMPLES, image_input, prepare_images


def sample_bytes(name="equations"):
    return (ASSETS / f"{name}.png").read_bytes()


def test_sample_recognition_uses_content_not_filename():
    result = image_input("renamed.jpg", sample_bytes())
    assert result["mime"] == "image/png"
    assert result["method"] == "Bundled sample transcript · no AI"
    assert "Student line 1: 3x = 25." in result["text"]
    assert result["text"] == (ASSETS / "equations.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("data", [b"not an image", b"", b"x"*(5*1024*1024+1)], ids=["invalid", "empty", "oversized"])
def test_invalid_or_oversized_images_rejected(data):
    with pytest.raises(ValueError):
        image_input("fractions.png", data)


def test_duplicate_and_excessive_uploads_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        prepare_images([("one.png", sample_bytes()), ("two.png", sample_bytes())])
    with pytest.raises(ValueError, match="one to three"):
        prepare_images([("page.png", sample_bytes())]*4)
    assert len(prepare_images([(s["id"]+".png", sample_bytes(s["id"])) for s in SAMPLES])) == 3


def test_vision_request_preserves_page_mapping_and_student_error(monkeypatch):
    images = prepare_images([("one.png", sample_bytes()), ("two.png", sample_bytes("graphs"))])
    monkeypatch.setattr(ai, "configuration", lambda: ("test-key", "vision-model"))
    parsed = ai.ImageReading(pages=[ai.ImagePage(image_id=i["id"], text=i["text"], uncertainties=[]) for i in reversed(images)])
    parse = Mock(return_value=SimpleNamespace(status="completed", output_parsed=parsed))
    monkeypatch.setattr(openai, "OpenAI", Mock(return_value=SimpleNamespace(responses=SimpleNamespace(parse=parse))))
    result = ai.transcribe(images)
    assert "3x = 25" in result[images[0]["id"]]["text"]
    content = parse.call_args.kwargs["input"][1]["content"]
    photos = [c for c in content if c["type"] == "input_image"]
    assert len(photos) == 2
    assert all(p["image_url"].startswith("data:image/png;base64,") for p in photos)
    assert parse.call_args.kwargs["store"] is False


def test_unmatched_transcription_cannot_be_imported(monkeypatch):
    images = prepare_images([("one.png", sample_bytes())])
    monkeypatch.setattr(ai, "request", Mock(return_value={"pages": [{"image_id":"invented", "text":"fabricated", "uncertainties":[]}]}))
    with pytest.raises(ValueError, match="exactly one transcript"):
        ai.transcribe(images)
