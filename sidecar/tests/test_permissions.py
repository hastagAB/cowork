"""Tests for the permission guard."""

import pytest

from cowork.agent.permissions import PermissionGuard
from cowork.models import PermissionConfig, PermissionTier


def test_allowed_path():
    config = PermissionConfig(allowed_paths=["~/Documents", "~/Downloads"])
    guard = PermissionGuard(config)

    # Paths under allowed dirs should be AUTO
    import os
    home = os.path.expanduser("~")
    assert guard.check_path(f"{home}/Documents/report.pdf") == PermissionTier.AUTO
    assert guard.check_path(f"{home}/Downloads/file.txt") == PermissionTier.AUTO


def test_blocked_path():
    config = PermissionConfig(allowed_paths=["~/Documents"])
    guard = PermissionGuard(config)

    # Paths outside allowed dirs should be BLOCKED
    assert guard.check_path("/etc/passwd") == PermissionTier.BLOCKED
    assert guard.check_path("C:\\Windows\\System32\\cmd.exe") == PermissionTier.BLOCKED


def test_blocked_extensions():
    config = PermissionConfig(allowed_paths=[])
    guard = PermissionGuard(config)

    # Executable extensions always blocked
    assert guard.check_path("/tmp/malware.exe") == PermissionTier.BLOCKED
    assert guard.check_path("/tmp/script.bat") == PermissionTier.BLOCKED
    assert guard.check_path("/tmp/setup.msi") == PermissionTier.BLOCKED


def test_empty_allowed_paths_permits_all():
    config = PermissionConfig(allowed_paths=[])
    guard = PermissionGuard(config)

    # Non-executable files allowed when no restrictions configured
    assert guard.check_path("/tmp/anything.txt") == PermissionTier.AUTO


def test_requires_confirmation():
    config = PermissionConfig(confirm_destructive=True)
    guard = PermissionGuard(config)

    assert guard.requires_confirmation("DELETE")
    assert guard.requires_confirmation("MOVE")
    assert guard.requires_confirmation("OVERWRITE")
    assert not guard.requires_confirmation("READ")
    assert not guard.requires_confirmation("WRITE")
