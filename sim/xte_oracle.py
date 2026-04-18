"""Cross-track error oracle for SIL testing.

Math is identical to FIX-Gateway compute.py xteFunction so that SIL results
are directly comparable to the FIX-Gateway plugin output.

Sign convention (verified against FIX-Gateway tests/plugins/compute/test_compute.py):
  Negative: aircraft north (left when facing east) of desired track
  Positive: aircraft south (right when facing east) of desired track

Note: The test-matrix document X-PLANE-TEST-MATRIX-PHASE-1B.md listed the opposite
sign (south=negative). The implementation here follows the actual FIX-Gateway code,
which is the authoritative source.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Math helpers — exact copies of private functions in FIX-Gateway compute.py
# ---------------------------------------------------------------------------

def _radians(degrees: float) -> float:
    return math.radians(degrees)


def _initial_bearing_rad(lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float) -> float:
    lat1 = _radians(lat1_deg)
    lon1 = _radians(lon1_deg)
    lat2 = _radians(lat2_deg)
    lon2 = _radians(lon2_deg)
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.atan2(y, x)


def _great_circle_distance_rad(lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float) -> float:
    lat1 = _radians(lat1_deg)
    lon1 = _radians(lon1_deg)
    lat2 = _radians(lat2_deg)
    lon2 = _radians(lon2_deg)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _normalize_angle_rad(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


_EARTH_RADIUS_NM = 3440.065


# ---------------------------------------------------------------------------
# Public compute function
# ---------------------------------------------------------------------------

def compute_xte_nm(
    own_lat: float,
    own_lon: float,
    wp_lat: float,
    wp_lon: float,
    desired_course_deg: float,
) -> float:
    """Return signed cross-track error in nautical miles.

    Arguments match the FIX-Gateway xteFunction input order:
      own_lat/own_lon:        aircraft position (decimal degrees)
      wp_lat/wp_lon:          active waypoint (decimal degrees)
      desired_course_deg:     desired track in degrees true

    Sign convention (matches FIX-Gateway unit tests):
      Negative => aircraft left / north of an eastbound course
      Positive => aircraft right / south of an eastbound course
    """
    if own_lat == wp_lat and own_lon == wp_lon:
        return 0.0
    theta13 = _initial_bearing_rad(wp_lat, wp_lon, own_lat, own_lon)
    theta12 = _radians(desired_course_deg)
    delta13 = _great_circle_distance_rad(wp_lat, wp_lon, own_lat, own_lon)
    angle = _normalize_angle_rad(theta13 - theta12)
    xte_rad = math.asin(math.sin(delta13) * math.sin(angle))
    return xte_rad * _EARTH_RADIUS_NM


# ---------------------------------------------------------------------------
# Scenario config and oracle
# ---------------------------------------------------------------------------

@dataclass
class XteScenario:
    """Defines the geometry and pass criteria for one XTE oracle check."""
    wp_lat: float
    wp_lon: float
    desired_course_deg: float
    sample_start_cycle: int = 30       # begin collecting samples at this cycle
    sample_end_cycle: int = 270        # stop collecting samples after this cycle
    expected_min_nm: Optional[float] = None   # mean XTE must be >= this; None = no lower bound
    expected_max_nm: Optional[float] = None   # mean XTE must be <= this; None = no upper bound


@dataclass
class XteSample:
    cycle: int
    own_lat: float
    own_lon: float
    xte_nm: float


@dataclass
class XteOracleResult:
    samples: int
    mean_xte_nm: float
    min_xte_nm: float
    max_xte_nm: float
    std_xte_nm: float
    passed: Optional[bool]
    reason: str
    sample_list: List[XteSample] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "samples": self.samples,
            "mean_xte_nm": round(self.mean_xte_nm, 4),
            "min_xte_nm": round(self.min_xte_nm, 4),
            "max_xte_nm": round(self.max_xte_nm, 4),
            "std_xte_nm": round(self.std_xte_nm, 4),
            "passed": self.passed,
            "reason": self.reason,
        }


class XteOracle:
    """Accumulates per-cycle XTE samples and evaluates pass/fail at end of run."""

    def __init__(self, scenario: XteScenario) -> None:
        self._scenario = scenario
        self._samples: List[XteSample] = []

    def record(self, cycle: int, own_lat: float, own_lon: float) -> Optional[float]:
        """Compute and store XTE for this cycle if within the sample window.

        Returns the XTE value if recorded, or None if outside the window.
        """
        s = self._scenario
        if cycle < s.sample_start_cycle or cycle > s.sample_end_cycle:
            return None
        xte = compute_xte_nm(own_lat, own_lon, s.wp_lat, s.wp_lon, s.desired_course_deg)
        self._samples.append(XteSample(cycle=cycle, own_lat=own_lat, own_lon=own_lon, xte_nm=xte))
        return xte

    def evaluate(self) -> XteOracleResult:
        """Return pass/fail result from all recorded samples."""
        if not self._samples:
            return XteOracleResult(
                samples=0,
                mean_xte_nm=0.0,
                min_xte_nm=0.0,
                max_xte_nm=0.0,
                std_xte_nm=0.0,
                passed=None,
                reason="no_samples",
                sample_list=[],
            )

        values = [s.xte_nm for s in self._samples]
        n = len(values)
        mean = sum(values) / n
        mn = min(values)
        mx = max(values)
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)

        s = self._scenario
        if s.expected_min_nm is not None and mean < s.expected_min_nm:
            passed = False
            reason = f"mean_xte {mean:.3f} < expected_min {s.expected_min_nm}"
        elif s.expected_max_nm is not None and mean > s.expected_max_nm:
            passed = False
            reason = f"mean_xte {mean:.3f} > expected_max {s.expected_max_nm}"
        else:
            passed = True
            reason = "ok"

        return XteOracleResult(
            samples=n,
            mean_xte_nm=mean,
            min_xte_nm=mn,
            max_xte_nm=mx,
            std_xte_nm=std,
            passed=passed,
            reason=reason,
            sample_list=self._samples,
        )
