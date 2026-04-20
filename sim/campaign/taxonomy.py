"""Failure classification taxonomy for SIL campaign outcomes (issue P0-C3)."""
from enum import Enum


class FailureClass(str, Enum):
    PASS        = "PASS"
    ORACLE_FAIL = "ORACLE_FAIL"   # FCS assertion evaluated but did not pass
    TEST_FAIL   = "TEST_FAIL"     # Scenario state error outside the oracle
    INFRA_FAIL  = "INFRA_FAIL"    # X-Plane unreachable, reset failed, bridge error
    ABORTED     = "ABORTED"       # Unexpected exception or forced termination

    @staticmethod
    def from_rc(rc: int) -> "FailureClass":
        """Map a SIL subprocess return code to a FailureClass."""
        if rc == 0:
            return FailureClass.PASS
        if rc == 1:
            return FailureClass.ORACLE_FAIL
        if rc == 2:
            return FailureClass.INFRA_FAIL
        return FailureClass.ABORTED
