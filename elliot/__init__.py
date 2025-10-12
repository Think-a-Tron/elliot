"""elliot package exposing the orchestrator helpers and CLI entry points."""

from .agent import create_elliot_agent, run_elliot

__all__ = ["create_elliot_agent", "run_elliot"]
