"""Perceptual hashing (pHash) and BK-tree spatial indexing engine.

Algorithm: 64-bit Discrete Cosine Transform (DCT) Perceptual Hash
Variant Identifier: phash-dct-64-ac-median

This module implements a self-contained, deterministic perceptual image hashing
engine using Pillow for image decoding and a Burkhard-Keller (BK) tree for discrete
Hamming-distance metric indexing.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Generic, TypeVar

from PIL import Image, ImageOps

# Algorithm identifier indicating 64-bit DCT with median threshold over AC coefficients
PHASH_ALGORITHM_ID = "phash-dct-64-ac-median"
HASH_BITS = 64
SAMPLE_SIZE = 32
LOW_FREQ_SIZE = 8

# Precompute the top 8 basis rows of the 32-point orthogonal DCT-II matrix
# C[k, n] = alpha_k * cos(pi * (2n + 1) * k / (2 * N))
# alpha_0 = sqrt(1 / N), alpha_k = sqrt(2 / N) for k > 0
_N = SAMPLE_SIZE
_DCT_BASIS: list[list[float]] = []
for _k in range(LOW_FREQ_SIZE):
    _alpha = math.sqrt(1.0 / _N) if _k == 0 else math.sqrt(2.0 / _N)
    _row = [_alpha * math.cos(math.pi * (2 * _n + 1) * _k / (2.0 * _N)) for _n in range(_N)]
    _DCT_BASIS.append(_row)


class PHashError(Exception):
    """Base exception for perceptual hashing operations."""


class PHashDecodeError(PHashError):
    """Raised when an image file cannot be read, decoded, or preprocessed."""


def preprocess_image_for_phash(image: Image.Image) -> Image.Image:
    """Normalize and preprocess an image for deterministic 32x32 DCT hashing.

    Steps:
    1. Apply EXIF orientation transposition if orientation metadata exists.
    2. Convert images with transparency (RGBA, LA, transparent palette P) by
       compositing them over an opaque white (255, 255, 255) background.
    3. Convert to 8-bit single-channel grayscale ('L').
    4. Downsample to 32x32 pixels using bilinear interpolation.

    Args:
        image: Pillow Image object in any supported mode.

    Returns:
        32x32 grayscale Pillow Image.
    """
    try:
        # 1. EXIF orientation correction
        transposed = ImageOps.exif_transpose(image)
        if transposed is not None:
            image = transposed
    except Exception:
        # Malformed EXIF should not prevent hashing
        pass

    # 2. Alpha compositing for transparent modes
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        try:
            rgba = image.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[3])
            image = bg
        except Exception as e:
            raise PHashDecodeError(f"Failed to composite transparent image: {e}") from e
    elif image.mode != "L":
        # Convert non-grayscale (CMYK, 1, YCbCr, I, etc.) cleanly to RGB first
        try:
            image = image.convert("RGB")
        except Exception as e:
            raise PHashDecodeError(
                f"Failed to convert image mode '{image.mode}' to RGB: {e}"
            ) from e

    # 3. Convert to grayscale and downsample to 32x32
    try:
        gray = image.convert("L")
        return gray.resize((SAMPLE_SIZE, SAMPLE_SIZE), Image.Resampling.BILINEAR)
    except Exception as e:
        raise PHashDecodeError(f"Failed to downsample image to 32x32: {e}") from e


def compute_phash_from_image(image: Image.Image) -> int:
    """Compute 64-bit DCT perceptual hash from an open Pillow Image.

    Args:
        image: Open Pillow Image object.

    Returns:
        64-bit unsigned integer perceptual hash.

    Raises:
        PHashDecodeError: If preprocessing or decoding fails.
    """
    small = preprocess_image_for_phash(image)

    # Extract 32x32 pixel values
    if hasattr(small, "get_flattened_data"):
        raw_pixels = list(small.get_flattened_data())
    else:
        raw_pixels = list(small.getdata())  # type: ignore[attr-defined]

    if len(raw_pixels) != SAMPLE_SIZE * SAMPLE_SIZE:
        raise PHashDecodeError(
            f"Expected {SAMPLE_SIZE * SAMPLE_SIZE} pixels, got {len(raw_pixels)}"
        )

    grid = [raw_pixels[i * SAMPLE_SIZE : (i + 1) * SAMPLE_SIZE] for i in range(SAMPLE_SIZE)]

    # 2D Separable DCT: compute only 8 rows x 8 columns low-frequency block
    # Step 1: Row DCT (8 rows x 32 columns)
    inter: list[list[float]] = [[0.0] * SAMPLE_SIZE for _ in range(LOW_FREQ_SIZE)]
    for k in range(LOW_FREQ_SIZE):
        basis_k = _DCT_BASIS[k]
        inter_k = inter[k]
        for j in range(SAMPLE_SIZE):
            s = 0.0
            for n in range(SAMPLE_SIZE):
                s += basis_k[n] * grid[n][j]
            inter_k[j] = s

    # Step 2: Column DCT (8 x 8 coefficients)
    low_freq: list[float] = []
    for k in range(LOW_FREQ_SIZE):
        inter_k = inter[k]
        for col_idx in range(LOW_FREQ_SIZE):
            basis_col = _DCT_BASIS[col_idx]
            s = 0.0
            for j in range(SAMPLE_SIZE):
                s += inter_k[j] * basis_col[j]
            low_freq.append(s)

    # Step 3: Median calculation over 63 AC coefficients (excluding DC term at [0, 0])
    ac_coeffs = low_freq[1:]
    sorted_ac = sorted(ac_coeffs)
    # With 63 items, the exact middle index is 31 (0-indexed)
    median = sorted_ac[31]

    # Step 4: 64-bit hash construction (1 if coefficient > median, else 0)
    hash_val = 0
    for val in low_freq:
        hash_val = (hash_val << 1) | (1 if val > median else 0)

    return hash_val


def compute_phash(path: Path | str) -> int:
    """Compute 64-bit DCT perceptual hash for an image file at path.

    Args:
        path: Path to the image file on disk.

    Returns:
        64-bit unsigned integer perceptual hash.

    Raises:
        PHashDecodeError: If file cannot be identified, opened, or decoded.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise PHashDecodeError(f"Image file does not exist: {file_path}")

    try:
        with Image.open(file_path) as img:
            return compute_phash_from_image(img)
    except Image.DecompressionBombError as e:
        raise PHashDecodeError(
            f"Image exceeds Pillow decompression bomb safety limit: {file_path} ({e})"
        ) from e
    except (OSError, SyntaxError, ValueError) as e:
        raise PHashDecodeError(f"Cannot identify or decode image file '{file_path}': {e}") from e
    except Exception as e:
        raise PHashDecodeError(f"Unexpected error decoding image '{file_path}': {e}") from e


def phash_to_hex(hash_value: int) -> str:
    """Format a 64-bit perceptual hash as a 16-character lowercase hex string."""
    return f"{hash_value:016x}"


def hex_to_phash(hex_str: str) -> int:
    """Parse a 16-character hexadecimal string into a 64-bit integer hash."""
    return int(hex_str, 16)


def hamming_distance(hash_a: int, hash_b: int) -> int:
    """Compute Hamming distance (number of differing bits) between two 64-bit hashes."""
    return (hash_a ^ hash_b).bit_count()


def bit_agreement_pct(distance: int, total_bits: int = HASH_BITS) -> float:
    """Calculate the percentage of matching hash bits for a given Hamming distance.

    Formula: (1 - distance / total_bits) * 100

    NOTE: This metric strictly represents the mathematical agreement ratio between
    64-bit binary hashes. It is NOT a measure of semantic visual similarity, human
    perceived similarity, or interchangeable image content.
    """
    if total_bits <= 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - (distance / total_bits)) * 100.0))


T = TypeVar("T")


class BKTreeNode(Generic[T]):
    """Node in a Burkhard-Keller metric tree.

    Holds all items with the exact same 64-bit hash in `items` bucket.
    Edges to children represent discrete Hamming distances.
    """

    __slots__ = ("children", "hash_value", "items")

    def __init__(self, hash_value: int, item: T) -> None:
        self.hash_value: int = hash_value
        self.items: list[T] = [item]
        self.children: dict[int, BKTreeNode[T]] = {}


class BKTree(Generic[T]):
    """Burkhard-Keller Tree for discrete metric search over 64-bit perceptual hashes.

    The BK-tree organizes nodes in a metric space using Hamming distance as the metric.
    Triangular inequality (|d(x, y) - d(x, z)| <= d(y, z)) allows pruning subtrees
    outside [d - max_dist, d + max_dist] during radius searches.

    Performance characteristics:
    - Typical search complexity: outperforms exhaustive O(N) linear scanning for
      sparse data distributions and small search radii.
    - Worst-case complexity: for uniform random distributions or very large radii,
      search approaches O(N) per query (O(N^2) all-pairs).
    - Memory: O(U) nodes where U is the number of unique 64-bit hashes.
    """

    def __init__(self) -> None:
        self.root: BKTreeNode[T] | None = None
        self._item_count: int = 0
        self._node_count: int = 0

    @property
    def item_count(self) -> int:
        """Total number of items stored in the tree."""
        return self._item_count

    @property
    def node_count(self) -> int:
        """Total number of unique hash nodes in the tree."""
        return self._node_count

    def insert(self, item: T, hash_value: int) -> None:
        """Insert an item with its 64-bit hash into the tree.

        If a node with the exact same hash already exists, the item is added to that
        node's bucket. Otherwise, a new node is created at distance d from its parent.
        """
        self._item_count += 1
        if self.root is None:
            self.root = BKTreeNode(hash_value, item)
            self._node_count = 1
            return

        curr = self.root
        while True:
            d = (hash_value ^ curr.hash_value).bit_count()
            if d == 0:
                curr.items.append(item)
                return
            if d in curr.children:
                curr = curr.children[d]
            else:
                curr.children[d] = BKTreeNode(hash_value, item)
                self._node_count += 1
                return

    def find_within(self, hash_value: int, max_dist: int) -> list[tuple[T, int]]:
        """Find all items in the tree within a maximum Hamming distance.

        Args:
            hash_value: Target 64-bit perceptual hash.
            max_dist: Maximum allowed Hamming distance (inclusive).

        Returns:
            List of (item, distance) tuples for all matching items.
        """
        if self.root is None or max_dist < 0:
            return []

        results: list[tuple[T, int]] = []
        # Use iterative stack for deterministic DFS traversal
        # Sorting children by distance ensures deterministic search order
        stack = [self.root]

        while stack:
            node = stack.pop()
            d = (hash_value ^ node.hash_value).bit_count()

            if d <= max_dist:
                for item in node.items:
                    results.append((item, d))

            low = d - max_dist
            high = d + max_dist

            # Traverse matching child branches in sorted order for determinism
            for child_dist in sorted(node.children.keys()):
                if low <= child_dist <= high:
                    stack.append(node.children[child_dist])

        return results

    def query_and_insert(self, item: T, hash_value: int, max_dist: int) -> list[tuple[T, int]]:
        """Query tree for existing matching items, then insert the new item.

        This single-pass method discovers matches against previously inserted items
        only. Because each pair (A, B) is evaluated only when the second item is inserted,
        this eliminates symmetric duplicate pair emissions (A, B) and (B, A) by construction.

        Args:
            item: Item to query and then insert.
            hash_value: 64-bit perceptual hash of the item.
            max_dist: Maximum Hamming distance threshold.

        Returns:
            List of (existing_item, distance) tuples found in the tree prior to insertion.
        """
        matches = self.find_within(hash_value, max_dist)
        self.insert(item, hash_value)
        return matches

    @classmethod
    def find_all_pairs(
        cls,
        items_with_hashes: list[tuple[T, int]],
        max_dist: int,
        max_candidate_pairs: int | None = None,
    ) -> tuple[list[tuple[T, T, int]], bool]:
        """Find all unique unordered candidate pairs within max_dist.

        Guarantees:
        - Every qualifying pair (item_a, item_b) is emitted exactly once with a < b
          according to the input list order.
        - Includes items sharing identical hashes (d = 0).
        - Includes candidate explosion protection: if `max_candidate_pairs` is reached,
          pair discovery halts and `is_truncated=True` is returned.

        Args:
            items_with_hashes: List of (item, 64-bit hash) tuples.
            max_dist: Maximum Hamming distance.
            max_candidate_pairs: Optional hard cap on returned candidate pairs.

        Returns:
            Tuple of (candidate_pairs, is_truncated) where each pair is
            (earlier_item, later_item, distance).
        """
        tree: BKTree[T] = cls()
        pairs: list[tuple[T, T, int]] = []
        is_truncated = False

        for item, h in items_with_hashes:
            matches = tree.query_and_insert(item, h, max_dist)
            for prev_item, d in matches:
                pairs.append((prev_item, item, d))
                if max_candidate_pairs is not None and len(pairs) >= max_candidate_pairs:
                    is_truncated = True
                    return pairs, is_truncated

        return pairs, is_truncated
