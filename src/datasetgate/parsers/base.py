"""Abstract base class for dataset parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.models import DatasetManifest


class BaseParser(ABC):
    """Abstract interface for dataset ingestion parsers."""

    @abstractmethod
    def can_parse(self, dataset_path: Path) -> bool:
        """Return True if this parser can handle the dataset at the given path."""
        pass

    @abstractmethod
    def parse(self, dataset_path: Path, config: DatasetGateConfig) -> DatasetManifest:
        """Parse dataset structure, images, labels, and classes into a DatasetManifest."""
        pass
