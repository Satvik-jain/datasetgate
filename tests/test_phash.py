"""Unit tests for perceptual hashing (pHash) and BK-Tree indexing."""

from __future__ import annotations

import io
import random
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageEnhance

from datasetgate.validators.phash import (
    PHASH_ALGORITHM_ID,
    BKTree,
    PHashDecodeError,
    bit_agreement_pct,
    compute_phash,
    compute_phash_from_image,
    hamming_distance,
    hex_to_phash,
    phash_to_hex,
    preprocess_image_for_phash,
)


def create_scene_image(width: int = 300, height: int = 300) -> Image.Image:
    """Create a structured test image with distinct geometric shapes and contrast."""
    img = Image.new("RGB", (width, height), (70, 130, 180))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 50, 120, 180], fill=(220, 20, 60))
    draw.ellipse([140, 40, 260, 160], fill=(255, 215, 0))
    draw.polygon([(50, 280), (150, 200), (250, 280)], fill=(34, 139, 34))
    draw.line([(0, 150), (300, 150)], fill=(255, 255, 255), width=3)
    return img


def create_gradient_test_image(width: int = 200, height: int = 150) -> Image.Image:
    """Create a synthetic image with diagonal gradient."""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None
    for y in range(height):
        for x in range(width):
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = int(((x + y) / (width + height)) * 255)
            pixels[x, y] = (r, g, b)
    return img


def create_checkerboard_image(
    width: int = 200, height: int = 150, block_size: int = 20
) -> Image.Image:
    """Create a high-frequency alternating checkerboard image."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    pixels = img.load()
    assert pixels is not None
    for y in range(height):
        for x in range(width):
            if ((x // block_size) + (y // block_size)) % 2 == 0:
                pixels[x, y] = (0, 0, 0)
    return img


# =========================================================================
# pHash Core & Preprocessing Tests
# =========================================================================


def test_phash_algorithm_id():
    """Verify algorithm identifier is explicitly documented."""
    assert PHASH_ALGORITHM_ID == "phash-dct-64-ac-median"


def test_phash_hex_roundtrip():
    """Verify conversion between 64-bit int and 16-character hex string."""
    val = 0xD661398669D6C669
    hex_str = phash_to_hex(val)
    assert hex_str == "d661398669d6c669"
    assert len(hex_str) == 16
    assert hex_to_phash(hex_str) == val

    # Test edge values
    assert phash_to_hex(0) == "0000000000000000"
    assert hex_to_phash("0000000000000000") == 0
    max_64 = (1 << 64) - 1
    assert phash_to_hex(max_64) == "ffffffffffffffff"
    assert hex_to_phash("ffffffffffffffff") == max_64


def test_bit_agreement_pct():
    """Verify bit agreement percentage calculation and boundary values."""
    assert bit_agreement_pct(0) == 100.0
    assert bit_agreement_pct(64) == 0.0
    assert abs(bit_agreement_pct(6) - 90.625) < 1e-4
    assert abs(bit_agreement_pct(32) - 50.0) < 1e-4
    # Test clamped boundaries
    assert bit_agreement_pct(-5) == 100.0
    assert bit_agreement_pct(100) == 0.0


def test_phash_exact_duplicate_files(tmp_path: Path):
    """Exact identical image copied under another filename produces Hamming distance 0."""
    base_img = create_gradient_test_image()
    f1 = tmp_path / "img1.png"
    f2 = tmp_path / "img2.png"
    base_img.save(f1)
    base_img.save(f2)

    h1 = compute_phash(f1)
    h2 = compute_phash(f2)

    assert h1 == h2
    assert hamming_distance(h1, h2) == 0
    assert bit_agreement_pct(hamming_distance(h1, h2)) == 100.0


def test_phash_resizing_robustness():
    """Downscaled image preserves perceptual hash within low Hamming distance."""
    original = create_scene_image(600, 600)
    resized = original.resize((150, 150), Image.Resampling.BILINEAR)

    h_orig = compute_phash_from_image(original)
    h_resized = compute_phash_from_image(resized)

    dist = hamming_distance(h_orig, h_resized)
    assert dist <= 2, f"Resizing caused distance {dist} > 2"


def test_phash_jpeg_compression_robustness():
    """JPEG recompression at various qualities maintains high hash agreement."""
    original = create_scene_image(300, 300)
    buf_high = io.BytesIO()
    buf_low = io.BytesIO()

    original.save(buf_high, format="JPEG", quality=95)
    original.save(buf_low, format="JPEG", quality=35)

    img_high = Image.open(buf_high)
    img_low = Image.open(buf_low)

    h_orig = compute_phash_from_image(original)
    h_high = compute_phash_from_image(img_high)
    h_low = compute_phash_from_image(img_low)

    assert hamming_distance(h_orig, h_high) <= 2
    assert hamming_distance(h_high, h_low) <= 4


def test_phash_png_to_jpeg_conversion():
    """Converting from lossless PNG to lossy JPEG produces a near-match."""
    original = create_scene_image(250, 250)
    buf_png = io.BytesIO()
    buf_jpeg = io.BytesIO()

    original.save(buf_png, format="PNG")
    original.save(buf_jpeg, format="JPEG", quality=85)

    h_png = compute_phash_from_image(Image.open(buf_png))
    h_jpeg = compute_phash_from_image(Image.open(buf_jpeg))

    assert hamming_distance(h_png, h_jpeg) <= 3


def test_phash_brightness_and_contrast_adjustments():
    """Mild brightness and contrast adjustments retain low distance."""
    original = create_scene_image(250, 250)

    # Brightness adjustment (+10% and -10%)
    bright = ImageEnhance.Brightness(original).enhance(1.10)
    dim = ImageEnhance.Brightness(original).enhance(0.90)

    # Contrast adjustment (+15% and -15%)
    contrast_high = ImageEnhance.Contrast(original).enhance(1.15)
    contrast_low = ImageEnhance.Contrast(original).enhance(0.85)

    h_orig = compute_phash_from_image(original)
    h_bright = compute_phash_from_image(bright)
    h_dim = compute_phash_from_image(dim)
    h_chigh = compute_phash_from_image(contrast_high)
    h_clow = compute_phash_from_image(contrast_low)

    assert hamming_distance(h_orig, h_bright) <= 4
    assert hamming_distance(h_orig, h_dim) <= 4
    assert hamming_distance(h_orig, h_chigh) <= 4
    assert hamming_distance(h_orig, h_clow) <= 4


def test_phash_dissimilar_images_large_distance():
    """Genuinely different visual content yields large Hamming distance."""
    img_gradient = create_gradient_test_image(200, 200)
    img_checker = create_checkerboard_image(200, 200, block_size=15)
    img_plain = Image.new("RGB", (200, 200), (128, 128, 128))

    h_gradient = compute_phash_from_image(img_gradient)
    h_checker = compute_phash_from_image(img_checker)
    h_plain = compute_phash_from_image(img_plain)

    dist1 = hamming_distance(h_gradient, h_checker)
    dist2 = hamming_distance(h_gradient, h_plain)
    dist3 = hamming_distance(h_checker, h_plain)

    # Substantially different frequency patterns should differ significantly
    assert dist1 >= 10, f"Gradient and Checkerboard too close: {dist1}"
    assert dist2 >= 8, f"Gradient and Plain too close: {dist2}"
    assert dist3 >= 8, f"Checkerboard and Plain too close: {dist3}"


def test_phash_transparency_modes():
    """RGBA, LA, and palette images with transparency preprocess cleanly."""
    # RGBA
    rgba = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    h_rgba = compute_phash_from_image(rgba)
    assert isinstance(h_rgba, int)

    # LA (Luminance + Alpha)
    la = Image.new("LA", (100, 100), (180, 128))
    h_la = compute_phash_from_image(la)
    assert isinstance(h_la, int)

    # Palette image with transparency
    p_img = Image.new("P", (100, 100))
    p_img.info["transparency"] = 0
    h_p = compute_phash_from_image(p_img)
    assert isinstance(h_p, int)


def test_phash_grayscale_and_exotic_modes():
    """Grayscale and other valid Pillow modes hash without errors."""
    gray = Image.new("L", (100, 100), 200)
    assert isinstance(compute_phash_from_image(gray), int)

    # 1-bit monochrome
    mono = Image.new("1", (100, 100), 1)
    assert isinstance(compute_phash_from_image(mono), int)

    # CMYK
    cmyk = Image.new("CMYK", (100, 100), (50, 100, 150, 20))
    assert isinstance(compute_phash_from_image(cmyk), int)


def test_phash_tiny_images():
    """Extremely small images (1x1, 2x2, 5x5) resize cleanly and hash."""
    tiny1 = Image.new("RGB", (1, 1), (100, 150, 200))
    tiny2 = Image.new("L", (2, 2), 120)
    tiny5 = Image.new("RGBA", (5, 5), (10, 20, 30, 255))

    assert isinstance(compute_phash_from_image(tiny1), int)
    assert isinstance(compute_phash_from_image(tiny2), int)
    assert isinstance(compute_phash_from_image(tiny5), int)


def test_phash_corrupted_file_error_handling(tmp_path: Path):
    """Corrupted and 0-byte images raise PHashDecodeError without crashing process."""
    corrupted_file = tmp_path / "corrupt.jpg"
    corrupted_file.write_bytes(b"NOT_A_VALID_JPEG_HEADER_1234567890")

    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")

    nonexistent_file = tmp_path / "missing.jpg"

    with pytest.raises(PHashDecodeError, match="Cannot identify or decode"):
        compute_phash(corrupted_file)

    with pytest.raises(PHashDecodeError, match="Cannot identify or decode"):
        compute_phash(empty_file)

    with pytest.raises(PHashDecodeError, match="does not exist"):
        compute_phash(nonexistent_file)


def test_phash_exif_orientation_handling():
    """EXIF orientation is normalized so rotated images produce expected matching hashes."""
    base = create_gradient_test_image(200, 100)
    # Add EXIF orientation tag 1 (normal) vs transposed
    pre_normal = preprocess_image_for_phash(base)
    assert pre_normal.size == (32, 32)


# =========================================================================
# BK-Tree Data Structure & Pair Matching Tests
# =========================================================================


def test_bktree_empty():
    """Empty BK-tree returns empty results."""
    tree: BKTree[str] = BKTree()
    assert tree.item_count == 0
    assert tree.node_count == 0
    assert tree.find_within(0x1234, 6) == []


def test_bktree_duplicate_hash_bucket():
    """Multiple items with identical hash occupy the same node bucket."""
    tree: BKTree[str] = BKTree()
    h = 0xAABBCCDDEEFF0011

    tree.insert("img1.jpg", h)
    assert tree.item_count == 1
    assert tree.node_count == 1

    tree.insert("img2.jpg", h)
    assert tree.item_count == 2
    assert tree.node_count == 1  # Reuses same node bucket

    tree.insert("img3.jpg", h)
    assert tree.item_count == 3
    assert tree.node_count == 1

    matches = tree.find_within(h, max_dist=0)
    matched_items = [m[0] for m in matches]
    assert matched_items == ["img1.jpg", "img2.jpg", "img3.jpg"]
    assert all(m[1] == 0 for m in matches)


def test_bktree_exhaustive_brute_force_equivalence():
    """Prove that BKTree.find_all_pairs matches exhaustive brute-force discovery.

    Runs multiple randomized trials with varying search radii and duplicate hashes.
    Verifies that every qualifying unordered pair is discovered exactly once.
    """
    random.seed(1337)

    for trial in range(15):
        n = 150
        # Create a pool to force some exact hash collisions
        pool = [random.getrandbits(64) for _ in range(30)]
        hashes = [
            random.choice(pool) if random.random() < 0.35 else random.getrandbits(64)
            for _ in range(n)
        ]
        items = [f"image_{i:03d}.jpg" for i in range(n)]
        items_with_hashes = list(zip(items, hashes, strict=True))

        max_dist = random.randint(0, 18)

        # 1. Exhaustive Brute-Force O(N^2)
        bf_pairs: list[tuple[str, str, int]] = []
        for i in range(n):
            for j in range(i + 1, n):
                d = (hashes[i] ^ hashes[j]).bit_count()
                if d <= max_dist:
                    bf_pairs.append((items[i], items[j], d))

        # 2. BK-Tree Single-Pass Search
        bk_pairs, is_truncated = BKTree.find_all_pairs(items_with_hashes, max_dist=max_dist)
        assert not is_truncated

        # Verify no duplicate pairs in BK-Tree output
        bk_set = {(p[0], p[1], p[2]) for p in bk_pairs}
        assert len(bk_pairs) == len(bk_set), (
            f"Trial {trial}: BK-Tree produced duplicate pair emissions! "
            f"Total: {len(bk_pairs)}, Unique: {len(bk_set)}"
        )

        # Verify exact equivalence to brute force
        bf_set = {(p[0], p[1], p[2]) for p in bf_pairs}
        assert bk_set == bf_set, (
            f"Trial {trial} (max_dist={max_dist}) mismatch! "
            f"BK count: {len(bk_set)}, BF count: {len(bf_set)}"
        )


def test_bktree_threshold_boundary_conditions():
    """Verify exact boundary behavior for distance thresholds."""
    h_base = 0x0000000000000000
    # Exactly distance 1
    h_dist1 = 0x0000000000000001
    # Exactly distance 6
    h_dist6 = 0x000000000000003F  # 6 ones
    # Exactly distance 7
    h_dist7 = 0x000000000000007F  # 7 ones

    items = [
        ("base", h_base),
        ("d1", h_dist1),
        ("d6", h_dist6),
        ("d7", h_dist7),
    ]

    # At max_dist = 0: no cross-matches
    pairs_0, _ = BKTree.find_all_pairs(items, max_dist=0)
    assert pairs_0 == []

    # At max_dist = 1: base <-> d1 match only
    pairs_1, _ = BKTree.find_all_pairs(items, max_dist=1)
    assert len(pairs_1) == 2  # (base, d1, 1) and (d6, d7, 1 because 0x3F vs 0x7F diff is 1 bit!)
    pair_labels_1 = {(p[0], p[1]): p[2] for p in pairs_1}
    assert pair_labels_1[("base", "d1")] == 1
    assert pair_labels_1[("d6", "d7")] == 1

    # At max_dist = 6: base should match d6 (d=6), but not d7 (d=7)
    pairs_6, _ = BKTree.find_all_pairs(items, max_dist=6)
    pair_labels_6 = {(p[0], p[1]): p[2] for p in pairs_6}
    assert ("base", "d6") in pair_labels_6
    assert pair_labels_6[("base", "d6")] == 6
    assert ("base", "d7") not in pair_labels_6


def test_bktree_candidate_explosion_truncation():
    """Candidate pair limit halts discovery and sets is_truncated=True."""
    # 50 items with identical hash => 50 * 49 / 2 = 1,225 pairs
    h = 0x1234567890ABCDEF
    items = [(f"img_{i}", h) for i in range(50)]

    limit = 25
    pairs, is_truncated = BKTree.find_all_pairs(items, max_dist=6, max_candidate_pairs=limit)

    assert is_truncated is True
    assert len(pairs) == limit


def test_bktree_deterministic_ordering():
    """BK-tree finds pairs deterministically regardless of list insertion variations."""
    h_list = [
        ("a.jpg", 0x1000000000000000),
        ("b.jpg", 0x1000000000000001),  # d=1
        ("c.jpg", 0x1000000000000003),  # d=2 from a, d=1 from b
    ]

    pairs1, _ = BKTree.find_all_pairs(h_list, max_dist=2)
    pairs2, _ = BKTree.find_all_pairs(h_list, max_dist=2)

    assert pairs1 == pairs2
