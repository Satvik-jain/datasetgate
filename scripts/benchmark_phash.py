"""Perceptual duplicate detection benchmark script for DatasetGate.

Measures and distinguishes:
1. Image decoding time vs pure pHash DCT computation time.
2. BK-Tree insertion time.
3. BK-Tree query time.
4. End-to-end pairing comparison: BK-Tree vs Exhaustive Brute-Force across dataset sizes
   (N = 50, 100, 250, 500, 1000).
5. Candidate explosion protection behavior.
6. System environment details (OS, CPU, Python version, Pillow version).
"""

from __future__ import annotations

import os
import platform
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import PIL
from PIL import Image, ImageDraw

from datasetgate.validators.phash import (
    PHASH_ALGORITHM_ID,
    BKTree,
    compute_phash,
    compute_phash_from_image,
    hamming_distance,
)


@dataclass
class SystemInfo:
    os_name: str
    os_release: str
    machine: str
    processor: str
    python_version: str
    pillow_version: str


def get_system_info() -> SystemInfo:
    return SystemInfo(
        os_name=platform.system(),
        os_release=platform.release(),
        machine=platform.machine(),
        processor=platform.processor() or "Unknown",
        python_version=platform.python_version(),
        pillow_version=PIL.__version__,
    )


def generate_benchmark_images(temp_dir: Path, count: int = 100) -> list[Path]:
    """Generate diverse synthetic images on disk for decoding benchmarks."""
    rng = random.Random(42)
    paths: list[Path] = []
    for i in range(count):
        # 640x480 RGB image with varying geometric shapes
        img = Image.new(
            "RGB",
            (640, 480),
            color=(rng.randint(20, 230), rng.randint(20, 230), rng.randint(20, 230)),
        )
        draw = ImageDraw.Draw(img)
        for _ in range(10):
            shape_type = rng.choice(["rect", "ellipse", "line"])
            x0, y0 = rng.randint(0, 500), rng.randint(0, 350)
            x1, y1 = x0 + rng.randint(20, 140), y0 + rng.randint(20, 120)
            color = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
            if shape_type == "rect":
                draw.rectangle([x0, y0, x1, y1], fill=color)
            elif shape_type == "ellipse":
                draw.ellipse([x0, y0, x1, y1], fill=color)
            else:
                draw.line([(x0, y0), (x1, y1)], fill=color, width=3)

        path = temp_dir / f"bench_{i:04d}.jpg"
        img.save(path, format="JPEG", quality=85)
        paths.append(path)
    return paths


def benchmark_image_decoding_vs_dct(image_paths: list[Path]) -> dict[str, float]:
    """Distinguish disk decoding, image preprocessing, and pure DCT math computation."""
    n = len(image_paths)

    # 1. Pure File Open & Read Time (open + load pixels into memory)
    t0 = time.perf_counter()
    for p in image_paths:
        with Image.open(p) as img:
            img.load()
    read_total_s = time.perf_counter() - t0

    # Pre-open images for subsequent isolated stages
    opened_images = [Image.open(p) for p in image_paths]
    for img in opened_images:
        img.load()

    # 2. Preprocessing Time (EXIF, alpha compositing, grayscale, 32x32 downsampling)
    from datasetgate.validators.phash import preprocess_image_for_phash

    t0 = time.perf_counter()
    preprocessed_images = [preprocess_image_for_phash(img) for img in opened_images]
    prep_total_s = time.perf_counter() - t0

    for img in opened_images:
        img.close()

    # 3. Pure 2D DCT & AC Median Math Time (from 32x32 grayscale image)
    # Re-running compute_phash_from_image on preprocessed images measures the DCT computation
    t0 = time.perf_counter()
    for prep in preprocessed_images:
        _ = compute_phash_from_image(prep)
    dct_total_s = time.perf_counter() - t0

    for prep in preprocessed_images:
        prep.close()

    # 4. End-to-end compute_phash time (open file -> preprocess -> DCT -> hash)
    t0 = time.perf_counter()
    for p in image_paths:
        _ = compute_phash(p)
    file_total_s = time.perf_counter() - t0

    return {
        "count": n,
        "read_total_ms": read_total_s * 1000.0,
        "read_avg_ms": (read_total_s / n) * 1000.0,
        "prep_total_ms": prep_total_s * 1000.0,
        "prep_avg_ms": (prep_total_s / n) * 1000.0,
        "dct_total_ms": dct_total_s * 1000.0,
        "dct_avg_ms": (dct_total_s / n) * 1000.0,
        "file_total_ms": file_total_s * 1000.0,
        "file_avg_ms": (file_total_s / n) * 1000.0,
    }


def generate_synthetic_hash_dataset(n: int, seed: int = 1337) -> list[tuple[str, int]]:
    """Generate a realistic distribution of 64-bit perceptual hashes.

    Includes exact duplicates, near-duplicate clusters (Hamming distance 1..4),
    and diverse background hashes.
    """
    rng = random.Random(seed)
    records: list[tuple[str, int]] = []

    # 10% near-duplicate clusters
    cluster_centers = [rng.getrandbits(64) for _ in range(max(1, n // 20))]

    for i in range(n):
        item_id = f"img_{i:05d}.jpg"
        dice = rng.random()
        if dice < 0.15 and cluster_centers:
            # Pick a center and flip 1 to 3 bits
            center = rng.choice(cluster_centers)
            flips = rng.randint(1, 3)
            h = center
            for _ in range(flips):
                bit = 1 << rng.randint(0, 63)
                h ^= bit
        elif dice < 0.20 and cluster_centers:
            # Exact duplicate of cluster center
            h = rng.choice(cluster_centers)
        else:
            # Random diverse 64-bit hash
            h = rng.getrandbits(64)
        records.append((item_id, h))

    return records


def brute_force_pairwise_search(
    records: list[tuple[str, int]], max_distance: int
) -> list[tuple[str, str, int]]:
    """O(N^2) exhaustive pairwise comparison baseline."""
    n = len(records)
    pairs: list[tuple[str, str, int]] = []
    for i in range(n):
        id_a, h_a = records[i]
        for j in range(i + 1, n):
            id_b, h_b = records[j]
            d = hamming_distance(h_a, h_b)
            if d <= max_distance:
                if id_a < id_b:
                    pairs.append((id_a, id_b, d))
                else:
                    pairs.append((id_b, id_a, d))
    return pairs


def run_scaling_benchmark(
    dataset_sizes: list[int] | None = None,
    threshold: int = 4,
) -> list[dict]:
    """Measure BK-Tree vs Brute-Force pairing across varying dataset sizes."""
    if dataset_sizes is None:
        dataset_sizes = [50, 100, 250, 500, 1000]
    results = []

    for n in dataset_sizes:
        records = generate_synthetic_hash_dataset(n, seed=42 + n)

        # 1. BK-Tree Insertion (inserting all N items into an empty BK-tree)
        bktree: BKTree[str] = BKTree()
        t0 = time.perf_counter()
        for item_id, h in records:
            bktree.insert(item_id, h)
        insert_time_ms = (time.perf_counter() - t0) * 1000.0

        # 2. BK-Tree Batch Query Time (querying all N items against the populated tree)
        t0 = time.perf_counter()
        for _item_id, h in records:
            _ = bktree.find_within(h, max_dist=threshold)
        query_time_ms = (time.perf_counter() - t0) * 1000.0

        # 3. BK-Tree Single-pass Pairing (find_all_pairs: builds tree and pairs in 1 pass)
        t0 = time.perf_counter()
        bk_pairs, is_truncated = BKTree.find_all_pairs(records, max_dist=threshold)
        single_pass_time_ms = (time.perf_counter() - t0) * 1000.0

        # 4. Exhaustive Brute-Force Pairwise Comparison
        t0 = time.perf_counter()
        bf_pairs = brute_force_pairwise_search(records, max_distance=threshold)
        bf_time_ms = (time.perf_counter() - t0) * 1000.0

        # Verification of correctness
        assert len(bk_pairs) == len(bf_pairs), (
            f"Pair count mismatch at N={n}: {len(bk_pairs)} vs {len(bf_pairs)}"
        )

        speedup = (bf_time_ms / single_pass_time_ms) if single_pass_time_ms > 0 else 1.0

        results.append(
            {
                "n": n,
                "comparisons": n * (n - 1) // 2,
                "pairs_found": len(bk_pairs),
                "insert_time_ms": insert_time_ms,
                "query_time_ms": query_time_ms,
                "bk_total_time_ms": insert_time_ms + query_time_ms,
                "single_pass_time_ms": single_pass_time_ms,
                "brute_force_time_ms": bf_time_ms,
                "speedup": speedup,
            }
        )

    return results


def run_candidate_explosion_benchmark() -> dict:
    """Benchmark candidate explosion protection when hash collisions or near-identical sets are large."""
    # Create 2000 identical hashes (generates ~2,000,000 potential pairs)
    n = 2000
    base_hash = 0xAAAAAAAAAAAAAAAA
    records = [(f"item_{i:04d}", base_hash) for i in range(n)]

    max_limit = 5000
    t0 = time.perf_counter()
    pairs, is_truncated = BKTree.find_all_pairs(records, max_dist=0, max_candidate_pairs=max_limit)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "n_items": n,
        "theoretical_pairs": n * (n - 1) // 2,
        "max_limit": max_limit,
        "returned_pairs": len(pairs),
        "is_truncated": is_truncated,
        "elapsed_ms": elapsed_ms,
    }


def main() -> None:
    print("=" * 80)
    print("DatasetGate Perceptual Hashing & Spatial Indexing Benchmark")
    print(f"Algorithm: {PHASH_ALGORITHM_ID}")
    print("=" * 80)

    # 1. System Environment
    sys_info = get_system_info()
    print("\n[1] System Environment")
    print(f"  Operating System : {sys_info.os_name} {sys_info.os_release} ({sys_info.machine})")
    print(f"  Processor        : {sys_info.processor}")
    print(f"  Python Version   : {sys_info.python_version}")
    print(f"  Pillow Version   : {sys_info.pillow_version}")
    print(f"  PID / CWD        : {os.getpid()} / {Path.cwd()}")

    # 2. Image Decoding vs DCT Calculation Breakdown
    print("\n[2] Image Decoding vs DCT pHash Computation Time")
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        print("  Generating 100 synthetic JPEG images (640x480) with geometric shapes...")
        img_paths = generate_benchmark_images(tmp_dir, count=100)

        timing = benchmark_image_decoding_vs_dct(img_paths)
        print(f"  Sample Count                 : {timing['count']} images (640x480 JPEG)")
        print(
            f"  1. Disk Read & Image Decode  : {timing['read_total_ms']:.2f} ms total ({timing['read_avg_ms']:.3f} ms/image)"
        )
        print(
            f"  2. Preprocessing (32x32 gray): {timing['prep_total_ms']:.2f} ms total ({timing['prep_avg_ms']:.3f} ms/image)"
        )
        print(
            f"  3. Pure 2D DCT & AC Median   : {timing['dct_total_ms']:.2f} ms total ({timing['dct_avg_ms']:.3f} ms/image)"
        )
        print(
            f"  Total Pipeline (File->pHash) : {timing['file_total_ms']:.2f} ms total ({timing['file_avg_ms']:.3f} ms/image)"
        )

    # 3. Spatial Indexing Scaling: BK-Tree vs Brute Force
    print("\n[3] Spatial Indexing Scaling: BK-Tree vs Brute Force (Hamming Distance <= 4)")
    print("  Comparing search and pairing across N = [50, 100, 250, 500, 1000]...")
    scaling_results = run_scaling_benchmark(threshold=4)

    header = (
        f"{'N':>6} | {'Pairs (N*(N-1)/2)':>18} | {'Found':>6} | "
        f"{'BK Insert':>10} | {'BK Query':>10} | {'BK 1-Pass':>10} | "
        f"{'BruteForce':>11} | {'Speedup':>8}"
    )
    print("\n  " + header)
    print("  " + "-" * len(header))

    for r in scaling_results:
        row = (
            f"{r['n']:>6} | {r['comparisons']:>18} | {r['pairs_found']:>6} | "
            f"{r['insert_time_ms']:>8.2f}ms | {r['query_time_ms']:>8.2f}ms | {r['single_pass_time_ms']:>8.2f}ms | "
            f"{r['brute_force_time_ms']:>9.2f}ms | {r['speedup']:>7.2f}x"
        )
        print("  " + row)

    # 4. Candidate Explosion Protection
    print("\n[4] Candidate Explosion Protection Benchmark")
    explosion = run_candidate_explosion_benchmark()
    print(f"  Test Scenario        : {explosion['n_items']} identical hashes")
    print(f"  Unbounded Pair Count : {explosion['theoretical_pairs']:,} candidate pairs")
    print(f"  Max Candidate Limit  : {explosion['max_limit']:,} pairs")
    print(f"  Returned Pair Count  : {explosion['returned_pairs']:,} pairs")
    print(f"  Truncation Flagged   : {explosion['is_truncated']}")
    print(f"  Execution Time       : {explosion['elapsed_ms']:.2f} ms")

    print("\n" + "=" * 80)
    print("Benchmark complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
