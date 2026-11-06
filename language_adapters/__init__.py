"""Execution contracts for installed, offline sandbox toolchains."""

from dataclasses import dataclass
from verification import PYTEST_COMMAND


@dataclass(frozen=True)
class LanguageAdapter:
    language: str
    command: tuple
    native: bool = False
    timeout: int = 35
    scope: str = "bundled harness; arbitrary dependency preparation unsupported"

    def receipt(self):
        return {
            "language": self.language,
            "command": list(self.command),
            "native_build_space": self.native,
            "deadline_seconds": self.timeout,
            "scope": self.scope,
        }


def adapter(language, timeout=35, native=False):
    supported = {
        "Python",
        "JavaScript",
        "TypeScript",
        "Go",
        "Rust",
        "Java",
        "C++",
        "SQLite SQL",
        "PostgreSQL SQL",
    }
    if language not in supported:
        raise ValueError("Unsupported language adapter.")
    return LanguageAdapter(
        language,
        tuple(PYTEST_COMMAND),
        native,
        timeout,
        "Python application edits with existing pytest and independent checks"
        if language == "Python"
        else "bundled harness with real language compiler/runtime/database; no general repository adapter",
    )
