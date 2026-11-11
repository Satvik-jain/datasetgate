"""Validators for dataset integrity, annotations, duplicates, and leakage."""

from datasetgate.validators.annotations import AnnotationValidator
from datasetgate.validators.base import BaseValidator
from datasetgate.validators.duplicates import DuplicateValidator
from datasetgate.validators.image_integrity import ImageIntegrityValidator
from datasetgate.validators.phash import (
    ADAPTIVE_CROSSOVER_THRESHOLD,
    HASH_BITS,
    MAX_HASH_VALUE,
    PHASH_ALGORITHM_ID,
    BKTree,
    BKTreeNode,
    PHashDecodeError,
    PHashError,
    bit_agreement_pct,
    brute_force_find_all_pairs,
    compute_phash,
    compute_phash_from_image,
    compute_phash_from_preprocessed,
    find_candidate_pairs,
    hamming_distance,
    hex_to_phash,
    phash_to_hex,
    preprocess_image_for_phash,
)

__all__ = [
    "ADAPTIVE_CROSSOVER_THRESHOLD",
    "AnnotationValidator",
    "BaseValidator",
    "BKTree",
    "BKTreeNode",
    "DuplicateValidator",
    "HASH_BITS",
    "ImageIntegrityValidator",
    "MAX_HASH_VALUE",
    "PHASH_ALGORITHM_ID",
    "PHashDecodeError",
    "PHashError",
    "bit_agreement_pct",
    "brute_force_find_all_pairs",
    "compute_phash",
    "compute_phash_from_image",
    "compute_phash_from_preprocessed",
    "find_candidate_pairs",
    "hamming_distance",
    "hex_to_phash",
    "phash_to_hex",
    "preprocess_image_for_phash",
]
