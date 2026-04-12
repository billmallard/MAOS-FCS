#!/usr/bin/env python3
"""Validation and pre-flight check for X-Plane SIL testing.

Usage:
    python tools/validation/validate_xplane_sil.py [--verbose]

Checks:
    1. Python dependencies (control, actuator, event modules)
    2. Config files exist and are valid JSON
    3. Aircraft configuration references valid actuator profiles
    4. X-Plane installation found
    5. Network ports (UDP 49000/49001) available for SIL
    6. Environment setup ready for SIL loop

Exit codes:
    0 = All checks passed
    1 = One or more checks failed (see details before running SIL)
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class Colors:
    """ANSI color codes for console output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─' * 70}{Colors.RESET}\n")


def print_pass(check: str, detail: str = "") -> None:
    """Print a passing check."""
    msg = f"{Colors.GREEN}✓ {check}{Colors.RESET}"
    if detail:
        msg += f"  ({detail})"
    print(msg)


def print_fail(check: str, detail: str = "") -> None:
    """Print a failing check."""
    msg = f"{Colors.RED}✗ {check}{Colors.RESET}"
    if detail:
        msg += f"  {detail}"
    print(msg)


def print_warn(check: str, detail: str = "") -> None:
    """Print a warning."""
    msg = f"{Colors.YELLOW}⚠ {check}{Colors.RESET}"
    if detail:
        msg += f"  {detail}"
    print(msg)


def print_info(msg: str) -> None:
    """Print informational text."""
    print(f"  {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Validators
# ─────────────────────────────────────────────────────────────────────────────

def check_python_version() -> Tuple[bool, str]:
    """Verify Python version >= 3.9."""
    version = sys.version_info
    if version.major > 3 or (version.major == 3 and version.minor >= 9):
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    return False, f"Python {version.major}.{version.minor} (requires >= 3.9)"


def check_python_dependencies() -> Tuple[bool, List[str]]:
    """Verify required Python modules can be imported."""
    repo_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(repo_root / "sim"))

    required = [
        "control_arch",
        "actuator_runtime",
        "aircraft_config",
        "xplane_bridge",
        "fcs_runtime",
        "event_log",
        "triplex_voter",
    ]

    missing = []
    installed = []

    for module in required:
        try:
            __import__(module)
            installed.append(module)
        except ImportError as e:
            missing.append(f"{module} — {str(e)}")

    return len(missing) == 0, missing if missing else installed


def check_config_files(repo_root: Path) -> Tuple[bool, List[str], List[str]]:
    """Verify config files exist and are valid JSON."""
    configs = {
        "Aircraft": repo_root / "configs" / "aircraft" / "ga_default.json",
        "Actuator profiles": repo_root / "configs" / "actuator_profiles",
        "Control laws": repo_root / "configs" / "control_laws" / "ga_default.json",
    }

    messages = []
    missing = []

    for name, path in configs.items():
        if isinstance(path, Path) and path.is_file():
            try:
                with open(path) as f:
                    json.load(f)
                messages.append(f"{name}: {path.name}")
            except json.JSONDecodeError as e:
                missing.append(f"{name} invalid JSON: {e}")
        elif isinstance(path, Path) and path.is_dir():
            json_files = list(path.glob("*.json"))
            if json_files:
                messages.append(f"{name}: {len(json_files)} profiles found")
            else:
                missing.append(f"{name} directory empty")
        else:
            missing.append(f"{name} not found: {path}")

    return len(missing) == 0, messages, missing


def check_aircraft_references(repo_root: Path) -> Tuple[bool, List[str]]:
    """Verify aircraft config references valid actuator profiles by vendor_key."""
    aircraft_cfg = repo_root / "configs" / "aircraft" / "ga_default.json"
    profiles_dir = repo_root / "configs" / "actuator_profiles"

    messages = []

    try:
        with open(aircraft_cfg) as f:
            cfg = json.load(f)
        
        aircraft_name = cfg.get("aircraft_name", "Unknown")
        messages.append(f"Aircraft: {aircraft_name}")

        active_profiles = cfg.get("active_profiles", [])
        if not active_profiles:
            return False, messages + ["No active_profiles defined"]

        # Load all available profiles and build vendor_key map
        available_vendor_keys = {}
        for profile_file in profiles_dir.glob("*.json"):
            try:
                with open(profile_file) as f:
                    profile_data = json.load(f)
                    vendor_key = profile_data.get("vendor_key", profile_file.stem)
                    available_vendor_keys[vendor_key] = profile_file.name
            except json.JSONDecodeError:
                pass

        unresolved = []
        for profile_ref in active_profiles:
            if profile_ref in available_vendor_keys:
                messages.append(f"  Profile '{profile_ref}' found ({available_vendor_keys[profile_ref]})")
            else:
                unresolved.append(profile_ref)

        if unresolved:
            return False, messages + [f"Unresolved profiles: {unresolved}"]

        return True, messages

    except Exception as e:
        return False, messages + [str(e)]


def check_xplane_installation() -> Tuple[bool, str]:
    """Verify X-Plane 12 installation exists."""
    xplane_paths = [
        Path("C:\\X-Plane 12"),
        Path("C:\\Program Files\\X-Plane 12"),
        Path("C:\\Program Files (x86)\\X-Plane 12"),
    ]

    for path in xplane_paths:
        if path.exists():
            exe = path / "X-Plane.exe"
            if exe.exists():
                return True, str(path)
            # Check for X-Plane 11 as fallback
            exe = path / "X-Plane 11.exe"
            if exe.exists():
                return True, str(path)

    return False, "X-Plane 12 not found in standard locations"


def check_network_ports() -> Tuple[bool, List[str]]:
    """Verify UDP ports 49000/49001 are available."""
    messages = []
    failures = []

    ports = [
        (49000, "X-Plane receive port"),
        (49001, "X-Plane send port"),
    ]

    for port, desc in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            sock.close()
            messages.append(f"UDP {port}: available ({desc})")
        except OSError as e:
            failures.append(f"UDP {port} — {desc}: {e}")

    return len(failures) == 0, messages if not failures else failures


def check_environment_variables() -> Tuple[bool, List[str]]:
    """Report environment variables used by SIL."""
    messages = []
    
    env_vars = {
        "XPLANE_HOST": ("127.0.0.1", "X-Plane host address"),
        "SIL_HZ": ("20", "SIL loop frequency (Hz)"),
        "SIL_CYCLES": ("200", "Number of cycles"),
        "SIL_LOG": ("sil_events.jsonl", "Event log file"),
    }

    for var, (default, desc) in env_vars.items():
        value = os.environ.get(var, default)
        status = "set" if var in os.environ else "default"
        messages.append(f"{var}={value} ({status}) — {desc}")

    return True, messages


def main(verbose: bool = False) -> int:
    """Run all validation checks."""
    repo_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(repo_root / "sim"))

    print_header("X-Plane SIL Pre-Flight Validation")
    
    all_passed = True

    # 1. Python version
    print_header("Environment")
    passed, detail = check_python_version()
    if passed:
        print_pass("Python version", detail)
    else:
        print_fail("Python version", detail)
        all_passed = False

    # 2. Python dependencies
    passed, details = check_python_dependencies()
    if passed:
        print_pass("Python dependencies", f"{len(details)} modules")
        if verbose:
            for mod in details:
                print_info(f"✓ {mod}")
    else:
        print_fail("Python dependencies", f"{len(details)} missing")
        for detail in details:
            print_info(f"✗ {detail}")
        all_passed = False

    # 3. Environment variables
    passed, details = check_environment_variables()
    print_pass("Environment variables")
    if verbose:
        for detail in details:
            print_info(detail)

    # 4. Config files
    print_header("Configuration Files")
    passed, messages, failures = check_config_files(repo_root)
    if passed:
        print_pass("Config files found and valid")
        if verbose:
            for msg in messages:
                print_info(msg)
    else:
        print_fail("Config files", f"{len(failures)} issues")
        for msg in messages:
            print_info(msg)
        for failure in failures:
            print_info(f"✗ {failure}")
        all_passed = False

    # 5. Aircraft references
    passed, details = check_aircraft_references(repo_root)
    if passed:
        print_pass("Aircraft configuration references resolved")
        if verbose:
            for detail in details:
                print_info(detail)
    else:
        print_fail("Aircraft configuration", "unresolved references")
        for detail in details:
            print_info(detail)
        all_passed = False

    # 6. X-Plane installation
    print_header("X-Plane Installation")
    passed, detail = check_xplane_installation()
    if passed:
        print_pass("X-Plane found", detail)
    else:
        print_warn("X-Plane not found", detail)
        print_info("→ SIL will run in dry-run mode (no X-Plane connection)")

    # 7. Network ports
    print_header("Network Configuration")
    passed, messages = check_network_ports()
    if passed:
        print_pass("UDP ports available")
        if verbose:
            for msg in messages:
                print_info(msg)
    else:
        print_fail("UDP ports", f"{len(messages)} issues")
        for msg in messages:
            print_info(msg)
        all_passed = False

    # Summary
    print_header("Validation Summary")
    if all_passed:
        print_pass("All critical checks passed!")
        print(f"\n{Colors.GREEN}Ready to start SIL loop.{Colors.RESET}")
        print(f"Run: {Colors.BOLD}python sim/examples/sil_xplane.py{Colors.RESET}\n")
        return 0
    else:
        print_fail("Some checks failed (see details above)")
        print(f"\n{Colors.RED}Fix the issues above before running SIL.{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sys.exit(main(verbose=verbose))
