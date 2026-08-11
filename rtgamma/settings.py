"""Shared public defaults and immutable gamma calculation settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_GAMMA_ENGINE = 'pymedphys'
LEGACY_GAMMA_ENGINE = 'numba'
SUPPORTED_PYMEDPHYS_VERSION = '0.41.0'
REPORT_SCHEMA_VERSION = 2
# Increment whenever calculation, coordinate, resampling, or optimization code
# can change a cached Gamma array without changing its recorded inputs/settings.
GAMMA_CACHE_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class GammaSettings:
    dd_percent: float
    dta_mm: float
    cutoff_percent: float
    gamma_type: str
    norm: str
    engine: str
    interp_fraction: int
    resample_interp: str
    opt_shift: bool
    shift_range: str
    refine: str
    fine_range_mm: float
    fine_step_mm: float
    early_stop_epsilon: float
    early_stop_patience: int
    prescan_2d: bool

    @classmethod
    def from_namespace(cls, args: Any) -> 'GammaSettings':
        return cls(
            dd_percent=float(args.dd),
            dta_mm=float(args.dta),
            cutoff_percent=float(args.cutoff),
            gamma_type=str(args.gamma_type),
            norm=str(args.norm),
            engine=str(args.engine),
            interp_fraction=int(args.interp_fraction),
            resample_interp=str(args.interp),
            opt_shift=args.opt_shift == 'on',
            shift_range=str(args.shift_range),
            refine=str(args.refine),
            fine_range_mm=float(args.fine_range_mm),
            fine_step_mm=float(args.fine_step_mm),
            early_stop_epsilon=float(args.early_stop_epsilon),
            early_stop_patience=int(args.early_stop_patience),
            prescan_2d=args.prescan_2d == 'on',
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
