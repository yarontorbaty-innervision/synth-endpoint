"""
OS-level playback controller for realistic workflow simulation.

Controls the actual mouse cursor and keyboard to replay workflows
as if a real user is operating the computer.

Supports macOS and Windows.
"""

from analyzer.playback.os_controller import OSController
from analyzer.playback.workflow_player import WorkflowPlayer

__all__ = ["OSController", "WorkflowPlayer"]
