"""The integration must carry its own brand images, inside the component folder.

Home Assistant 2026.3 replaced "submit your icon to home-assistant/brands" with
"ship a ``brand/`` folder": ``homeassistant/loader.py`` sets ``has_branding``
from ``"brand" in self._top_level_files``, and ``components/brands`` serves
``<integration>/brand/<image>`` BEFORE it falls back to the CDN. HACS's own
validation looks at the same path first (``hacs/validate/brands.py`` builds
``<remote path>/brand/icon.png``) and only then queries ``domains.json``.

This project has the artwork -- it has shipped ``icon.png`` and friends at the
repository root since long before the rename. The root is simply not a place
anything looks: HACS resolves the asset path relative to the integration
directory, and Home Assistant reads it from the loaded integration's own
``file_path``. So the images were present and the icon was still a placeholder,
on the integrations page and on every repair card this integration raises.

Pinned rather than left to a build step because the failure is silent in both
directions: nothing errors when the folder is missing, and nothing errors when
someone later tidies the duplicates away.
"""

import struct
from pathlib import Path

import pytest

_BRAND = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "irrigation_plus"
    / "brand"
)

# name -> (width, height) required by the Home Assistant brands specification.
# icon must be square; logo may be wider. The @2x variants are exactly double.
_EXPECTED = {
    "icon.png": (256, 256),
    "icon@2x.png": (512, 512),
    "logo.png": None,
    "logo@2x.png": None,
}


def _png_size(path):
    """(width, height) from the IHDR chunk, or None if this is not a PNG."""
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", raw[16:24])


@pytest.mark.parametrize("name", sorted(_EXPECTED))
def test_the_brand_image_is_shipped_inside_the_integration(name):
    """Not at the repository root -- nothing reads it there."""
    assert (_BRAND / name).is_file(), (
        f"{name} is missing from {_BRAND}. Home Assistant serves the integration "
        "icon from <integration>/brand/, and HACS validates that same path; "
        "a copy at the repository root is read by neither."
    )


@pytest.mark.parametrize("name", sorted(_EXPECTED))
def test_the_brand_image_is_a_png_of_the_required_size(name):
    size = _png_size(_BRAND / name)
    assert size is not None, f"{name} is not a PNG"
    expected = _EXPECTED[name]
    if expected is not None:
        assert size == expected, (
            f"{name} is {size[0]}x{size[1]}; the brands specification requires "
            f"{expected[0]}x{expected[1]}"
        )


def test_the_double_resolution_variants_are_exactly_double():
    """A mismatched @2x renders blurry on exactly the displays it exists for."""
    for base in ("icon", "logo"):
        one = _png_size(_BRAND / f"{base}.png")
        two = _png_size(_BRAND / f"{base}@2x.png")
        assert two == (one[0] * 2, one[1] * 2), (
            f"{base}@2x.png is {two[0]}x{two[1]}, expected "
            f"{one[0] * 2}x{one[1] * 2}"
        )
