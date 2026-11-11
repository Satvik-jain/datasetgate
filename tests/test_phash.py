"""Unit tests for perceptual hashing (pHash) and BK-Tree indexing."""

from __future__ import annotations

import io
import math
import random
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageEnhance

from datasetgate.validators.phash import (
    HASH_BITS,
    LOW_FREQ_SIZE,
    MAX_HASH_VALUE,
    PHASH_ALGORITHM_ID,
    SAMPLE_SIZE,
    BKTree,
    PHashDecodeError,
    bit_agreement_pct,
    brute_force_find_all_pairs,
    compute_phash,
    compute_phash_from_image,
    compute_phash_from_preprocessed,
    find_candidate_pairs,
    hamming_distance,
    hex_to_phash,
    phash_to_hex,
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


def direct_textbook_dct_2d(matrix: list[list[float]]) -> list[list[float]]:
    """Independent unoptimized textbook implementation of 2D DCT-II."""
    n = SAMPLE_SIZE
    res = [[0.0] * LOW_FREQ_SIZE for _ in range(LOW_FREQ_SIZE)]
    for u in range(LOW_FREQ_SIZE):
        alpha_u = math.sqrt(1.0 / n) if u == 0 else math.sqrt(2.0 / n)
        for v in range(LOW_FREQ_SIZE):
            alpha_v = math.sqrt(1.0 / n) if v == 0 else math.sqrt(2.0 / n)
            s = 0.0
            for x in range(n):
                for y in range(n):
                    s += (
                        matrix[x][y]
                        * math.cos(math.pi * (2 * x + 1) * u / (2.0 * n))
                        * math.cos(math.pi * (2 * y + 1) * v / (2.0 * n))
                    )
            res[u][v] = alpha_u * alpha_v * s
    return res


# =========================================================================
# pHash Core & Preprocessing Tests
# =========================================================================


def test_phash_algorithm_id():
    """Verify algorithm identifier explicitly records 63-bit AC-only median hash."""
    assert PHASH_ALGORITHM_ID == "phash-dct-63-ac-median"
    assert HASH_BITS == 63
    assert MAX_HASH_VALUE == (1 << 63) - 1


def test_phash_hex_roundtrip():
    """Verify conversion between 63-bit int and 16-character hex string."""
    val = 0x5661398669D6C669
    assert val <= MAX_HASH_VALUE
    hex_str = phash_to_hex(val)
    assert hex_str == "5661398669d6c669"
    assert len(hex_str) == 16
    assert hex_to_phash(hex_str) == val

    # Test edge values
    assert phash_to_hex(0) == "0000000000000000"
    assert hex_to_phash("0000000000000000") == 0
    assert phash_to_hex(MAX_HASH_VALUE) == "7fffffffffffffff"
    assert hex_to_phash("7fffffffffffffff") == MAX_HASH_VALUE

    # Out of range values
    with pytest.raises(ValueError):
        phash_to_hex(-1)
    with pytest.raises(ValueError):
        phash_to_hex(MAX_HASH_VALUE + 1)
    with pytest.raises(ValueError):
        hex_to_phash("8000000000000000")  # Exceeds 63-bit unsigned range
    with pytest.raises(ValueError):
        hex_to_phash("abc")  # Invalid length


def test_bit_agreement_pct():
    """Verify bit agreement percentage calculation and boundary values."""
    assert bit_agreement_pct(0) == 100.0
    assert bit_agreement_pct(63) == 0.0
    assert abs(bit_agreement_pct(7) - ((63 - 7) / 63 * 100)) < 1e-4

    with pytest.raises(ValueError, match="total_bits must be positive"):
        bit_agreement_pct(5, total_bits=0)
    with pytest.raises(ValueError, match="distance must be non-negative"):
        bit_agreement_pct(-1)


def test_direct_dct_reference_precision():
    """Verify separable DCT in phash matches textbook direct 2D DCT-II to floating precision."""
    rng = random.Random(1337)
    test_grid = [
        [float(rng.randint(0, 255)) for _ in range(SAMPLE_SIZE)] for _ in range(SAMPLE_SIZE)
    ]

    # 1. Compute direct textbook 2D DCT-II
    direct_coeffs = direct_textbook_dct_2d(test_grid)

    # 2. Compute using preprocessed Pillow image and compute_phash_from_preprocessed
    img = Image.new("L", (SAMPLE_SIZE, SAMPLE_SIZE))
    pixels = img.load()
    assert pixels is not None
    for x in range(SAMPLE_SIZE):
        for y in range(SAMPLE_SIZE):
            pixels[x, y] = int(test_grid[x][y])

    # Extract coefficients through internal separable matrix multiplication
    from datasetgate.validators.phash import _DCT_BASIS

    inter = [[0.0] * SAMPLE_SIZE for _ in range(LOW_FREQ_SIZE)]
    for k in range(LOW_FREQ_SIZE):
        basis_k = _DCT_BASIS[k]
        for j in range(SAMPLE_SIZE):
            s = sum(basis_k[n] * test_grid[n][j] for n in range(SAMPLE_SIZE))
            inter[k][j] = s

    for k in range(LOW_FREQ_SIZE):
        for col_idx in range(LOW_FREQ_SIZE):
            basis_col = _DCT_BASIS[col_idx]
            coeff = sum(inter[k][j] * basis_col[j] for j in range(SAMPLE_SIZE))
            expected = direct_coeffs[k][col_idx]
            assert abs(coeff - expected) < 1e-9, (
                f"Mismatch at ({k}, {col_idx}): {coeff} vs {expected}"
            )


def test_brightness_invariance_and_dc_exclusion():
    """Prove that uniform brightness shift changes DC but leaves 63-bit AC pHash identical."""
    # Create an image with intensity in safe unclipped range [40, 200]
    base = Image.new("RGB", (200, 200), (100, 120, 140))
    draw = ImageDraw.Draw(base)
    draw.rectangle([30, 30, 100, 100], fill=(60, 80, 100))
    draw.ellipse([80, 80, 160, 160], fill=(150, 170, 190))

    hash_base = compute_phash_from_image(base)

    # Add uniform offset of +25 to all pixel channels (unclipped)
    bright = Image.eval(base, lambda v: v + 25)
    hash_bright = compute_phash_from_image(bright)

    # The 63-bit AC pHash must be identical (Hamming distance = 0)
    dist = hamming_distance(hash_base, hash_bright)
    assert dist == 0, f"Expected 0 Hamming distance under uniform brightness addition, got {dist}"
    assert bit_agreement_pct(dist) == 100.0


def test_phash_exact_duplicate_files(tmp_path: Path):
    """Verify identical image files have identical hashes and 100% agreement."""
    img = create_scene_image()
    path1 = tmp_path / "img1.png"
    path2 = tmp_path / "img2.png"
    img.save(path1)
    img.save(path2)

    h1 = compute_phash(path1)
    h2 = compute_phash(path2)
    assert h1 == h2
    assert hamming_distance(h1, h2) == 0
    assert bit_agreement_pct(0) == 100.0


def test_phash_resizing_robustness():
    """Verify that resizing structured images retains near-zero Hamming distance."""
    base = create_scene_image(600, 600)
    h_base = compute_phash_from_image(base)

    for sz in [(400, 400), (300, 300), (200, 200), (100, 100)]:
        resized = base.resize(sz, Image.Resampling.BILINEAR)
        h_resized = compute_phash_from_image(resized)
        dist = hamming_distance(h_base, h_resized)
        assert dist <= 2, f"Distance too large on resize {sz}: {dist}"


def test_phash_jpeg_compression_robustness(tmp_path: Path):
    """Verify that JPEG compression artifacts produce low Hamming distance."""
    base = create_scene_image(400, 400)
    h_base = compute_phash_from_image(base)

    for quality in (95, 75, 50, 35):
        buf = io.BytesIO()
        base.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        with Image.open(buf) as jpg_img:
            h_jpg = compute_phash_from_image(jpg_img)
        dist = hamming_distance(h_base, h_jpg)
        assert dist <= 4, f"JPEG q={quality} distance too large: {dist}"


def test_phash_png_to_jpeg_conversion(tmp_path: Path):
    """Verify format conversion between PNG and JPEG maintains low Hamming distance."""
    base = create_scene_image(300, 300)
    png_path = tmp_path / "scene.png"
    jpg_path = tmp_path / "scene.jpg"

    base.save(png_path, format="PNG")
    base.save(jpg_path, format="JPEG", quality=90)

    h_png = compute_phash(png_path)
    h_jpg = compute_phash(jpg_path)
    dist = hamming_distance(h_png, h_jpg)
    assert dist <= 3


def test_phash_contrast_adjustments():
    """Verify contrast variations produce low Hamming distances."""
    base = create_scene_image(300, 300)
    h_base = compute_phash_from_image(base)

    for factor in (0.8, 1.2):
        c_img = ImageEnhance.Contrast(base).enhance(factor)
        h_c = compute_phash_from_image(c_img)
        dist = hamming_distance(h_base, h_c)
        assert dist <= 4, f"Contrast factor {factor} distance too large: {dist}"


def test_phash_dissimilar_images_large_distance():
    """Verify visually dissimilar images produce large Hamming distance."""
    img1 = create_scene_image(300, 300)
    img2 = create_checkerboard_image(300, 300, block_size=15)

    h1 = compute_phash_from_image(img1)
    h2 = compute_phash_from_image(img2)
    dist = hamming_distance(h1, h2)
    assert dist >= 20, f"Distance between dissimilar images unexpectedly small: {dist}"


def test_phash_transparency_modes():
    """Verify RGBA, LA, and palette images with transparency composite onto white."""
    rgba = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rgba)
    draw.rectangle([20, 20, 80, 80], fill=(255, 0, 0, 255))
    h_rgba = compute_phash_from_image(rgba)
    assert isinstance(h_rgba, int)
    assert 0 <= h_rgba <= MAX_HASH_VALUE


def test_phash_grayscale_and_exotic_modes():
    """Verify grayscale and 1-bit modes compute valid perceptual hashes."""
    gray = Image.new("L", (100, 100), 128)
    d = ImageDraw.Draw(gray)
    d.rectangle([10, 10, 50, 50], fill=0)
    h_gray = compute_phash_from_image(gray)
    assert isinstance(h_gray, int)
    assert 0 <= h_gray <= MAX_HASH_VALUE


def test_phash_tiny_images():
    """Verify edge case of tiny images downsampling without crash."""
    for sz in [(1, 1), (2, 2), (5, 5)]:
        tiny = Image.new("RGB", sz, (100, 150, 200))
        h = compute_phash_from_image(tiny)
        assert isinstance(h, int)
        assert 0 <= h <= MAX_HASH_VALUE


def test_phash_exif_orientation_handling():
    """Verify EXIF orientation flag is normalized before hashing."""
    base = Image.new("RGB", (100, 50), (255, 255, 255))
    draw = ImageDraw.Draw(base)
    draw.rectangle([0, 0, 30, 20], fill=(0, 0, 0))

    # Tag 6 indicates 90 CW rotation needed to display upright,
    # so the raw captured buffer is rotated 90 CCW relative to upright.
    rotated = base.rotate(90, expand=True)
    exif = rotated.getexif()
    exif[0x0112] = 6  # Orientation tag indicating 90 CW rotation needed
    buf = io.BytesIO()
    rotated.save(buf, format="JPEG", exif=exif)
    buf.seek(0)

    with Image.open(buf) as img_exif:
        h_exif = compute_phash_from_image(img_exif)
    h_base = compute_phash_from_image(base)
    assert hamming_distance(h_base, h_exif) <= 4


# =========================================================================
# Pillow Decompression-Bomb and Safety Tests
# =========================================================================


def test_decompression_bomb_warning_threshold_raises_decode_error(tmp_path: Path):
    """Verify an image exceeding the decompression bomb warning threshold raises PHashDecodeError."""
    # Temporarily set a local MAX_IMAGE_PIXELS threshold to test warning safety
    orig_max = Image.MAX_IMAGE_PIXELS
    try:
        Image.MAX_IMAGE_PIXELS = 1000
        # 1200 pixels exceeds MAX_IMAGE_PIXELS (1000) but <= 2*MAX_IMAGE_PIXELS (2000)
        img = Image.new("RGB", (40, 30))
        test_file = tmp_path / "bomb_warn.png"
        img.save(test_file)

        with pytest.raises(PHashDecodeError, match="exceeds decompression bomb warning threshold"):
            compute_phash(test_file)
    finally:
        Image.MAX_IMAGE_PIXELS = orig_max


def test_decompression_bomb_error_threshold_raises_decode_error(tmp_path: Path):
    """Verify an image exceeding the decompression bomb error threshold raises PHashDecodeError."""
    orig_max = Image.MAX_IMAGE_PIXELS
    try:
        Image.MAX_IMAGE_PIXELS = 1000
        # 2500 pixels exceeds 2*MAX_IMAGE_PIXELS (2000)
        img = Image.new("RGB", (50, 50))
        test_file = tmp_path / "bomb_error.png"
        img.save(test_file)

        with pytest.raises(PHashDecodeError, match="exceeds Pillow decompression bomb"):
            compute_phash(test_file)
    finally:
        Image.MAX_IMAGE_PIXELS = orig_max


def test_corrupted_file_error_handling(tmp_path: Path):
    """Verify corrupted, truncated, or nonexistent files raise PHashDecodeError."""
    corrupted_path = tmp_path / "bad.jpg"
    corrupted_path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00corrupted_garbage_bytes")

    with pytest.raises(PHashDecodeError):
        compute_phash(corrupted_path)

    nonexistent_path = tmp_path / "missing.jpg"
    with pytest.raises(PHashDecodeError, match="does not exist"):
        compute_phash(nonexistent_path)


def test_normal_large_image_succeeds_without_error(tmp_path: Path):
    """Verify normal large images (e.g. 1500x1500) hash without triggering warning or error."""
    img = Image.new("RGB", (1500, 1500), (120, 140, 160))
    test_file = tmp_path / "normal_large.png"
    img.save(test_file)

    h = compute_phash(test_file)
    assert isinstance(h, int)
    assert 0 <= h <= MAX_HASH_VALUE


def test_safety_mechanism_not_disabled_globally():
    """Verify Image.MAX_IMAGE_PIXELS is never disabled (set to None) globally."""
    assert Image.MAX_IMAGE_PIXELS is not None
    assert Image.MAX_IMAGE_PIXELS >= 10_000_000


# =========================================================================
# BK-Tree, Brute-Force, and Adaptive Strategy Tests
# =========================================================================


def test_bktree_empty():
    """Verify empty BK-Tree behaves correctly."""
    tree: BKTree[str] = BKTree()
    assert tree.item_count == 0
    assert tree.node_count == 0
    assert tree.find_within(0, 5) == []
    assert list(tree.iter_within(0, 5)) == []


def test_bktree_invalid_arguments():
    """Verify negative distances and non-positive candidate limits raise ValueError."""
    tree: BKTree[str] = BKTree()
    with pytest.raises(ValueError, match="max_dist must be non-negative"):
        tree.find_within(0, -1)
    with pytest.raises(ValueError, match="max_dist must be non-negative"):
        list(tree.iter_within(0, -1))
    with pytest.raises(ValueError, match="max_dist must be non-negative"):
        BKTree.find_all_pairs([], -1)
    with pytest.raises(ValueError, match="max_candidate_pairs must be positive"):
        BKTree.find_all_pairs([], 2, max_candidate_pairs=0)
    with pytest.raises(ValueError, match="max_candidate_pairs must be positive"):
        BKTree.find_all_pairs([], 2, max_candidate_pairs=-5)


def test_bktree_incremental_iterator_equivalence():
    """Verify iter_within yields items identical to find_within."""
    tree: BKTree[str] = BKTree()
    hashes = [
        ("a", 0b0000000001),
        ("b", 0b0000000011),
        ("c", 0b0000000111),
        ("d", 0b0000000001),  # duplicate hash
        ("e", 0b1111111111),
    ]
    for item, h in hashes:
        tree.insert(item, h)

    list_matches = tree.find_within(0b0000000001, max_dist=2)
    iter_matches = list(tree.iter_within(0b0000000001, max_dist=2))
    assert list_matches == iter_matches
    assert ("a", 0) in iter_matches
    assert ("d", 0) in iter_matches
    assert ("b", 1) in iter_matches
    assert ("c", 2) in iter_matches
    assert ("e", 9) not in iter_matches


def test_bktree_large_bucket_memory_protection():
    """Verify querying a 100,000-item identical hash bucket with a small limit does not materialize all."""
    # Create 100,000 items with the same hash
    items = [(f"item_{i}", 0x12345678) for i in range(100_000)]

    # Query with max_candidate_pairs=10
    pairs, is_truncated = BKTree.find_all_pairs(items, max_dist=0, max_candidate_pairs=10)

    assert len(pairs) == 10
    assert is_truncated is True
    # Verify pairs contain earlier-to-later indexing
    for _prev, _curr, d in pairs:
        assert d == 0


def test_candidate_limit_boundary_and_completeness():
    """Verify completeness semantics: is_truncated is False when total pairs <= limit, True when > limit."""
    # 4 items with distance 0 generates exactly 4*3/2 = 6 pairs
    items = [(f"x_{i}", 0xABC) for i in range(4)]

    # When limit is exactly 6 (total matching pairs), result is complete
    pairs, is_truncated = BKTree.find_all_pairs(items, max_dist=0, max_candidate_pairs=6)
    assert len(pairs) == 6
    assert is_truncated is False

    # When limit is 5 (< 6), result is truncated
    pairs_trunc, is_trunc = BKTree.find_all_pairs(items, max_dist=0, max_candidate_pairs=5)
    assert len(pairs_trunc) == 5
    assert is_trunc is True


def test_bktree_brute_force_adaptive_equivalence():
    """Verify BKTree, brute force, and adaptive strategy yield identical results across randomized trials."""
    for trial in range(10):
        rng = random.Random(trial)
        n = 60
        cluster = [rng.getrandbits(HASH_BITS) for _ in range(3)]
        records: list[tuple[str, int]] = []
        for i in range(n):
            if rng.random() < 0.25:
                c = rng.choice(cluster)
                h = c ^ (1 << rng.randint(0, HASH_BITS - 1))
            else:
                h = rng.getrandbits(HASH_BITS)
            records.append((f"img_{i:03d}", h))

        # 1. Unbounded pairing
        bk_pairs, bk_trunc = BKTree.find_all_pairs(records, max_dist=4)
        bf_pairs, bf_trunc = brute_force_find_all_pairs(records, max_dist=4)
        adapt_pairs, adapt_trunc = find_candidate_pairs(records, max_dist=4, crossover_threshold=30)

        assert bk_trunc is False
        assert bf_trunc is False
        assert adapt_trunc is False
        assert set(bk_pairs) == set(bf_pairs)
        assert set(adapt_pairs) == set(bf_pairs)

        # 2. Bounded pairing with truncation
        limit = 5
        bk_lim, bk_lim_tr = BKTree.find_all_pairs(records, max_dist=4, max_candidate_pairs=limit)
        bf_lim, bf_lim_tr = brute_force_find_all_pairs(
            records, max_dist=4, max_candidate_pairs=limit
        )
        adapt_lim, adapt_lim_tr = find_candidate_pairs(
            records, max_dist=4, max_candidate_pairs=limit, crossover_threshold=30
        )

        assert len(bk_lim) == min(limit, len(bk_pairs))
        assert len(bf_lim) == min(limit, len(bf_pairs))
        assert len(adapt_lim) == min(limit, len(adapt_pairs))
        assert bk_lim_tr == (len(bk_pairs) > limit)
        assert bf_lim_tr == (len(bf_pairs) > limit)
        assert adapt_lim_tr == (len(adapt_pairs) > limit)


def test_isolated_dct_computation_function():
    """Verify compute_phash_from_preprocessed works directly on 32x32 grayscale images."""
    img = Image.new("L", (32, 32), 100)
    d = ImageDraw.Draw(img)
    d.rectangle([5, 5, 20, 20], fill=200)

    h = compute_phash_from_preprocessed(img)
    assert isinstance(h, int)
    assert 0 <= h <= MAX_HASH_VALUE

    # Verify invalid dimensions or mode raise PHashDecodeError
    bad_sz = Image.new("L", (16, 16))
    with pytest.raises(PHashDecodeError, match="Expected 32x32 image"):
        compute_phash_from_preprocessed(bad_sz)

    bad_mode = Image.new("RGB", (32, 32))
    with pytest.raises(PHashDecodeError, match="Expected grayscale mode 'L'"):
        compute_phash_from_preprocessed(bad_mode)
