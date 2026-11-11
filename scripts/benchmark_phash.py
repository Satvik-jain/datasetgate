"""Perceptual duplicate detection benchmark script for DatasetGate.

Measures and distinguishes:
1. File access and image decoding.
2. Image normalization and 32x32 resizing.
3. Pure 2D DCT transform, AC median calculation, and 63-bit hash generation (isolated, no redundant preprocessing).
4. End-to-end compute_phash pipeline.
5. BK-Tree insertion time.
6. BK-Tree candidate query time.
7. Brute-force pairwise comparison time vs BK-Tree across scaling dataset sizes
   (N = 50, 100, 250, 500, 750, 1000, 1500, 2000).
8. Adaptive strategy performance and empirical crossover point verification.
9. Candidate explosion memory protection on large buckets (up to 100,000 items).
10. System hardware and environment metadata.
"""

from __future__ import annotations

import os
import platform
import random
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import PIL
from PIL import Image, ImageDraw

from datasetgate.validators.phash import (
    ADAPTIVE_CROSSOVER_THRESHOLD,
    HASH_BITS,
    PHASH_ALGORITHM_ID,
    BKTree,
    brute_force_find_all_pairs,
    compute_phash,
    compute_phash_from_preprocessed,
    find_candidate_pairs,
    preprocess_image_for_phash,
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


def benchmark_pipeline_stages(
    image_paths: list[Path], num_iterations: int = 5
) -> dict[str, dict[str, float]]:
    """Measure isolated stages of the pHash pipeline across repeated iterations with warm-up."""
    n = len(image_paths)

    # Pre-open images for isolated preprocessing and DCT stages
    opened_images: list[Image.Image] = []
    for p in image_paths:
        with Image.open(p) as img:
            img.load()
            opened_images.append(img.copy())

    preprocessed_images: list[Image.Image] = [
        preprocess_image_for_phash(img) for img in opened_images
    ]

    # --- Warm-up run (not timed) ---
    for p in image_paths[:10]:
        with Image.open(p) as img:
            img.load()
    for img in opened_images[:10]:
        _ = preprocess_image_for_phash(img)
    for prep in preprocessed_images[:10]:
        _ = compute_phash_from_preprocessed(prep)
    for p in image_paths[:10]:
        _ = compute_phash(p)

    # --- Timed iterations ---
    decode_times: list[float] = []
    prep_times: list[float] = []
    dct_times: list[float] = []
    e2e_times: list[float] = []

    for _ in range(num_iterations):
        # Stage 1: File access and full image decode
        t0 = time.perf_counter()
        for p in image_paths:
            with Image.open(p) as img:
                img.load()
        decode_times.append((time.perf_counter() - t0) * 1000.0)

        # Stage 2: Normalization and 32x32 resizing
        t0 = time.perf_counter()
        for img in opened_images:
            _ = preprocess_image_for_phash(img)
        prep_times.append((time.perf_counter() - t0) * 1000.0)

        # Stage 3: Pure 2D DCT, AC median, and 63-bit hash generation (isolated!)
        t0 = time.perf_counter()
        for prep in preprocessed_images:
            _ = compute_phash_from_preprocessed(prep)
        dct_times.append((time.perf_counter() - t0) * 1000.0)

        # Stage 4: End-to-end compute_phash (file -> hash)
        t0 = time.perf_counter()
        for p in image_paths:
            _ = compute_phash(p)
        e2e_times.append((time.perf_counter() - t0) * 1000.0)

    # Cleanup memory
    for img in opened_images:
        img.close()
    for prep in preprocessed_images:
        prep.close()

    def stats(vals: list[float]) -> dict[str, float]:
        mean_val = statistics.mean(vals)
        return {
            "mean_total_ms": mean_val,
            "min_total_ms": min(vals),
            "stdev_ms": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "avg_per_image_ms": mean_val / n,
        }

    return {
        "decode": stats(decode_times),
        "prep": stats(prep_times),
        "dct": stats(dct_times),
        "e2e": stats(e2e_times),
    }


def generate_synthetic_hash_dataset(n: int, seed: int = 1337) -> list[tuple[str, int]]:
    """Generate realistic 63-bit hashes with near-duplicate clusters and background diversity."""
    rng = random.Random(seed)
    records: list[tuple[str, int]] = []
    cluster_centers = [rng.getrandbits(HASH_BITS) for _ in range(max(1, n // 20))]

    for i in range(n):
        item_id = f"img_{i:05d}.jpg"
        dice = rng.random()
        if dice < 0.15 and cluster_centers:
            center = rng.choice(cluster_centers)
            flips = rng.randint(1, 3)
            h = center
            for _ in range(flips):
                h ^= 1 << rng.randint(0, HASH_BITS - 1)
        elif dice < 0.20 and cluster_centers:
            h = rng.choice(cluster_centers)
        else:
            h = rng.getrandbits(HASH_BITS)
        records.append((item_id, h))

    return records


def run_scaling_benchmark(
    dataset_sizes: list[int] | None = None,
    threshold: int = 4,
) -> list[dict]:
    """Measure BK-Tree, Brute-Force, and Adaptive pairing across scaling dataset sizes."""
    if dataset_sizes is None:
        dataset_sizes = [50, 100, 250, 500, 750, 1000, 1500, 2000]

    results = []

    for n in dataset_sizes:
        records = generate_synthetic_hash_dataset(n, seed=42 + n)

        # 1. BK-Tree Insertion
        bktree: BKTree[str] = BKTree()
        t0 = time.perf_counter()
        for item_id, h in records:
            bktree.insert(item_id, h)
        insert_time_ms = (time.perf_counter() - t0) * 1000.0

        # 2. BK-Tree Query Time (find_within for all N items)
        t0 = time.perf_counter()
        for _item_id, h in records:
            _ = bktree.find_within(h, max_dist=threshold)
        query_time_ms = (time.perf_counter() - t0) * 1000.0

        # 3. BK-Tree 1-Pass Pairing (find_all_pairs)
        t0 = time.perf_counter()
        bk_pairs, is_trunc_bk = BKTree.find_all_pairs(records, max_dist=threshold)
        bk_pass_ms = (time.perf_counter() - t0) * 1000.0

        # 4. Brute-Force Pairwise Search (brute_force_find_all_pairs)
        t0 = time.perf_counter()
        bf_pairs, is_trunc_bf = brute_force_find_all_pairs(records, max_dist=threshold)
        bf_time_ms = (time.perf_counter() - t0) * 1000.0

        # 5. Adaptive Strategy (find_candidate_pairs)
        t0 = time.perf_counter()
        adapt_pairs, is_trunc_adapt = find_candidate_pairs(records, max_dist=threshold)
        adapt_time_ms = (time.perf_counter() - t0) * 1000.0

        # Equivalence Verification
        assert len(bk_pairs) == len(bf_pairs) == len(adapt_pairs), (
            f"Count mismatch at N={n}: BK={len(bk_pairs)}, BF={len(bf_pairs)}, Adapt={len(adapt_pairs)}"
        )
        assert is_trunc_bk is is_trunc_bf is is_trunc_adapt is False

        speedup_bk = (bf_time_ms / bk_pass_ms) if bk_pass_ms > 0 else 1.0

        results.append(
            {
                "n": n,
                "comparisons": n * (n - 1) // 2,
                "pairs_found": len(bk_pairs),
                "insert_time_ms": insert_time_ms,
                "query_time_ms": query_time_ms,
                "bk_pass_ms": bk_pass_ms,
                "brute_force_time_ms": bf_time_ms,
                "adapt_time_ms": adapt_time_ms,
                "speedup_bk": speedup_bk,
            }
        )

    return results


def run_candidate_explosion_benchmark() -> dict:
    """Benchmark candidate explosion protection on a 100,000-item bucket."""
    n = 100_000
    base_hash = 0x5555555555555555
    records = [(f"item_{i:06d}", base_hash) for i in range(n)]

    max_limit = 10
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
    print("=" * 90)
    print("DatasetGate Perceptual Duplicate Engine — Algorithm Audit & Performance Benchmark")
    print(f"Algorithm: {PHASH_ALGORITHM_ID} ({HASH_BITS}-bit AC-only DCT)")
    print(f"Adaptive Crossover Threshold: N = {ADAPTIVE_CROSSOVER_THRESHOLD}")
    print("=" * 90)

    # 1. System Environment
    sys_info = get_system_info()
    print("\n[1] System Environment")
    print(f"  Operating System : {sys_info.os_name} {sys_info.os_release} ({sys_info.machine})")
    print(f"  Processor        : {sys_info.processor}")
    print(f"  Python Version   : {sys_info.python_version}")
    print(f"  Pillow Version   : {sys_info.pillow_version}")
    print(f"  PID / CWD        : {os.getpid()} / {Path.cwd()}")

    # 2. Pipeline Stages Benchmark
    print("\n[2] Isolated Pipeline Stages Timing (100 synthetic 640x480 JPEGs, 5 runs + warm-up)")
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        print("  Generating test images on disk...")
        img_paths = generate_benchmark_images(tmp_dir, count=100)

        timing = benchmark_pipeline_stages(img_paths, num_iterations=5)

        print("\n  Stage Breakdown:")
        print(
            f"  1. Disk Read & Image Decode  : {timing['decode']['mean_total_ms']:7.2f} ms mean "
            f"({timing['decode']['avg_per_image_ms']:.3f} ms/image, min={timing['decode']['min_total_ms']:.2f}ms)"
        )
        print(
            f"  2. Normalization & 32x32 Gray: {timing['prep']['mean_total_ms']:7.2f} ms mean "
            f"({timing['prep']['avg_per_image_ms']:.3f} ms/image, min={timing['prep']['min_total_ms']:.2f}ms)"
        )
        print(
            f"  3. Pure 2D DCT & 63-bit Math : {timing['dct']['mean_total_ms']:7.2f} ms mean "
            f"({timing['dct']['avg_per_image_ms']:.3f} ms/image, min={timing['dct']['min_total_ms']:.2f}ms)"
        )
        print(
            f"  4. End-to-End File -> pHash  : {timing['e2e']['mean_total_ms']:7.2f} ms mean "
            f"({timing['e2e']['avg_per_image_ms']:.3f} ms/image, min={timing['e2e']['min_total_ms']:.2f}ms)"
        )

    # 3. Spatial Indexing Scaling & Crossover Analysis
    print("\n[3] Spatial Indexing Scaling & Crossover Analysis (Hamming Distance <= 4)")
    scaling_results = run_scaling_benchmark()

    header = (
        f"{'N':>6} | {'Pairs (N*(N-1)/2)':>18} | {'Found':>6} | "
        f"{'BK Insert':>10} | {'BK Query':>9} | {'BK 1-Pass':>9} | "
        f"{'BruteForce':>10} | {'Adaptive':>9} | {'BF/BK':>6}"
    )
    print("\n  " + header)
    print("  " + "-" * len(header))

    for r in scaling_results:
        row = (
            f"{r['n']:>6} | {r['comparisons']:>18} | {r['pairs_found']:>6} | "
            f"{r['insert_time_ms']:>8.2f}ms | {r['query_time_ms']:>7.2f}ms | {r['bk_pass_ms']:>7.2f}ms | "
            f"{r['brute_force_time_ms']:>8.2f}ms | {r['adapt_time_ms']:>7.2f}ms | {r['speedup_bk']:>5.2f}x"
        )
        print("  " + row)

    # 4. Candidate Explosion Protection
    print("\n[4] Candidate Explosion Protection Benchmark (Large Bucket Test)")
    explosion = run_candidate_explosion_benchmark()
    print(f"  Test Bucket Size     : {explosion['n_items']:,} identical hashes")
    print(f"  Unbounded Pair Count : {explosion['theoretical_pairs']:,} candidate pairs")
    print(f"  Max Candidate Limit  : {explosion['max_limit']:,} pairs")
    print(f"  Returned Pair Count  : {explosion['returned_pairs']:,} pairs")
    print(f"  Truncation Flagged   : {explosion['is_truncated']}")
    print(f"  Execution Time       : {explosion['elapsed_ms']:.2f} ms")

    print("\n" + "=" * 90)
    print("Benchmark complete.")
    print("=" * 90)


if __name__ == "__main__":
    main()
