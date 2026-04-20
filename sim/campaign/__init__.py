"""MAOS-FCS SIL campaign infrastructure package.

Provides reusable building blocks for campaign runners:
  - FailureClass  — normalized outcome taxonomy (PASS / ORACLE_FAIL / INFRA_FAIL / …)
  - RunMetadata   — per-scenario run envelope dataclass
  - write_run_env — writes run_env.json alongside scenario artifacts
"""
from campaign.metadata import RunMetadata, write_run_env
from campaign.taxonomy import FailureClass

__all__ = ["FailureClass", "RunMetadata", "write_run_env"]
