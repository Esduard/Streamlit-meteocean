from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ModelMetadata:
    target_variable: str  # "current_speed" | "wave_height" | "wind_speed"
    model_family: str  # "prophet"
    model_type: str  # "univariate" | "exogenous"
    model_path: Path
    required_features: tuple[str, ...]  # Prophet extra_regressors keys; empty for univariate
    feature_name_map: tuple[str, ...] | None  # human-readable names in positional order
    frequency: str  # "H"
    max_univariate_horizon_hours: int  # 8760
    display_name: str  # derived from model_path.parent.name
    training_cutoff: datetime | None = None  # last timestamp seen during training

    @property
    def is_exogenous(self) -> bool:
        return self.model_type == "exogenous"
