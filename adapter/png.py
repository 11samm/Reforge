"""PNG integrity and exact decoded comparisons; no candidate evaluator."""
import hashlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "development"
EVIDENCE = ROOT / "evidence"


def within(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path must stay inside {root.name}")
    return path


def fixture_path(recorded_path):
    parts = Path(recorded_path).parts
    if not parts or parts[0] != "development" or ".." in parts:
        raise ValueError("Only development fixture paths are accepted")
    return within(FIXTURES.joinpath(*parts[1:]), FIXTURES)


def png_info(path):
    path = Path(path)
    with Image.open(path) as image:
        if image.format != "PNG":
            raise ValueError("Expected a PNG export")
        image.load()
        rgba = image.convert("RGBA")
        pixels = rgba.tobytes()
        return {"width": image.width, "height": image.height, "mode": image.mode,
                "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rgba_sha256": hashlib.sha256(pixels).hexdigest(),
                "alpha_extrema": list(rgba.getchannel("A").getextrema())}


def compare_pngs(actual_path, expected_path):
    with Image.open(actual_path) as a, Image.open(expected_path) as b:
        a.load(); b.load()
        if a.size != b.size:
            return {"dimensions_equal": False, "rgba_equal": False,
                    "different_pixels": None, "max_channel_delta": None}
        actual, expected = a.convert("RGBA").tobytes(), b.convert("RGBA").tobytes()
        different = sum(actual[i:i+4] != expected[i:i+4] for i in range(0, len(actual), 4))
        return {"dimensions_equal": True, "rgba_equal": actual == expected,
                "different_pixels": different,
                "max_channel_delta": max((abs(x-y) for x,y in zip(actual,expected)), default=0)}
