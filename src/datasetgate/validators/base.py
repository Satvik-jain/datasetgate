"""Base validator interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from datasetgate.core.config import DatasetGateConfig
from datasetgate.core.models import DatasetManifest, Finding


class BaseValidator(ABC):
    """Abstract validator interface."""

    @abstractmethod
    def validate(self, manifest: DatasetManifest, config: DatasetGateConfig) -> list[Finding]:
        """Run validation rules on the dataset manifest and return detected findings."""
        pass
