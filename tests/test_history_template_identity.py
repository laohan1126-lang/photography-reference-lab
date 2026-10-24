"""F1: a crop template must stay bound to the image it was cut from.

The matcher compares a candidate against every historical image. Its crop
templates are cached per query, so a cache key that does not name the image the
template was cut from lets one historical photo lend its template to the next
one. The result then depends on the order of the history, which is exactly what
this file pins down.

Synthetic pixels: these regressions protect the matching rules, not the
accuracy of a platform or of a model.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

from ref_lab.collection_history import ImageHistory


@pytest.fixture(autouse=True)
def _no_production_data(monkeypatch):
    """A synthetic fixture must never read the exported production library."""
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)


def _textured(size, seed, base):
    """A photo-like tile: smooth structure plus local detail."""
    width, height = size
    rng = np.random.default_rng(seed)
    noise = rng.integers(-40, 41, (height, width, 3), dtype=np.int16)
    ramp = np.linspace(-24, 24, width, dtype=np.int16)[None, :, None]
    array = np.clip(np.array(base, np.int16) + noise + ramp, 0, 255).astype(np.uint8)
    image = Image.fromarray(array, "RGB").filter(ImageFilter.GaussianBlur(0.8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((width // 5, height // 4, width * 3 // 5, height * 7 // 10),
                 fill=tuple(int(value) for value in base))
    draw.rectangle((width // 6, height // 2, width // 3, height * 4 // 5),
                   fill=tuple(min(255, int(value) + 60) for value in base))
    draw.line((0, height // 3, width, height // 3), fill=(250, 250, 250), width=3)
    return image


def _subject():
    """A full frame with a distinctive subject, and its vertical crop."""
    image = _textured((800, 600), 41, (70, 90, 120))
    draw = ImageDraw.Draw(image)
    draw.ellipse((310, 75, 460, 220), fill=(210, 170, 130))
    draw.line((380, 260, 650, 400), fill=(220, 40, 50), width=45)
    return image


def _match(history_paths, candidate):
    history = ImageHistory(list(history_paths))
    try:
        return history.match(candidate)
    finally:
        history.close(wait=True, timeout=5)


def test_crop_of_history_is_found_whatever_the_history_order(tmp_path):
    full = tmp_path / 'full.png'
    _subject().save(full)
    crop = tmp_path / 'crop.jpg'
    _subject().crop((240, 0, 560, 600)).resize((640, 1200)).save(crop, quality=91)
    unrelated = tmp_path / 'unrelated.png'
    _textured((640, 1200), 300, (40, 210, 30)).save(unrelated)

    alone = _match([crop], full)
    assert alone is not None, 'a crop of a historical photo is a repeat'
    assert alone['reason'] == 'crop_duplicate'

    # An unrelated photo of the same size in front must not hide the crop, and
    # the crop in front must not change the answer for the unrelated photo.
    after = _match([unrelated, crop], full)
    before = _match([crop, unrelated], full)
    assert after is not None, 'history order changed the crop verdict'
    assert before == after
    assert after['duplicate_of'] == alone['duplicate_of']


def test_same_size_unrelated_history_does_not_create_a_duplicate(tmp_path):
    candidate = tmp_path / 'candidate.png'
    _subject().save(candidate)
    others = []
    for index in range(4):
        path = tmp_path / f'other-{index}.png'
        _textured((800, 600), 500 + index, (30 + index * 20, 200, 60)).save(path)
        others.append(path)
    assert _match(others, candidate) is None, 'different photos are not duplicates'


def test_different_burst_frames_are_not_duplicates(tmp_path):
    """Two frames of one burst stay two photos: no false crop verdict."""
    first = tmp_path / 'burst-1.png'
    second = tmp_path / 'burst-2.png'
    base = _subject()
    base.save(first)
    moved = base.copy()
    draw = ImageDraw.Draw(moved)
    draw.rectangle((0, 0, 800, 40), fill=(15, 200, 90))
    moved.save(second)
    assert _match([first], second) is None
    assert _match([second], first) is None


def test_scaled_and_reencoded_copies_are_recognised(tmp_path):
    full = tmp_path / 'full.png'
    _subject().save(full)
    scaled = tmp_path / 'scaled.jpg'
    with Image.open(full) as image:
        image.resize((400, 300)).save(scaled, quality=88)
    reencoded = tmp_path / 'reencoded.jpg'
    with Image.open(full) as image:
        image.save(reencoded, quality=95)
    for path in (scaled, reencoded):
        hit = _match([full], path)
        assert hit is not None, f'{path.name} is the same photo and must not count as new'
        assert hit['reason'] in {'near_duplicate', 'crop_duplicate', 'possible_crop_duplicate'}


def test_parallel_stride_chunks_agree_with_the_serial_scan(tmp_path):
    """The parallel scan splits the history into stride chunks.

    A template reused inside a chunk would make the chunk's answer depend on
    which images happen to sit next to each other, so the parallel verdict has
    to equal the serial one.
    """
    candidate = tmp_path / 'candidate.png'
    _subject().save(candidate)
    crop = tmp_path / 'crop.jpg'
    _subject().crop((240, 0, 560, 600)).resize((640, 1200)).save(crop, quality=91)
    history = []
    for index in range(70):
        path = tmp_path / f'filler-{index:02d}.png'
        # Same size as the crop: the template sizes are derived from the aspect
        # ratio of the pair, so only a same-size neighbour can reuse a template.
        _textured((640, 1200), 900 + index, (25 + index, 60, 190)).save(path)
        history.append(path)
    # The crop sits in the middle of the history, behind other images, so no
    # stride chunk starts with it either.
    history.insert(8, crop)

    parallel = _match(history, candidate)
    assert parallel is not None, 'the parallel scan lost the crop duplicate'
    assert parallel['reason'] == 'crop_duplicate'

    serial = ImageHistory([crop])
    try:
        expected = serial.match(candidate)
    finally:
        serial.close(wait=True, timeout=5)
    assert expected is not None
    assert parallel['duplicate_of'] == expected['duplicate_of']


@pytest.mark.parametrize('order', ['first', 'last'])
def test_crop_duplicate_verdict_is_stable_for_a_single_historical_image(tmp_path, order):
    candidate = tmp_path / 'candidate.png'
    _subject().save(candidate)
    crop = tmp_path / 'crop.jpg'
    _subject().crop((240, 0, 560, 600)).resize((640, 1200)).save(crop, quality=91)
    other = tmp_path / 'other.png'
    _textured((640, 1200), 77, (200, 60, 200)).save(other)
    paths = [crop, other] if order == 'first' else [other, crop]
    hit = _match(paths, candidate)
    assert hit is not None
    assert hit['reason'] == 'crop_duplicate'
