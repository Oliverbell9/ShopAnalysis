"""Track the observed RAW transaction commit state.

NOT_COMMITTED does not independently establish rollback.
UNKNOWN requires evidence-based manual recovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommitState(Enum):
    NOT_COMMITTED = "NOT_COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    COMMITTED = "COMMITTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class CommitTracker:
    state: CommitState = CommitState.NOT_COMMITTED

    def committed(self) -> None:
        """Record successful return from the RAW COMMIT statement."""
        self.state = CommitState.COMMITTED

    def uncertain(self) -> None:
        """Record a commit attempt whose outcome is uncertain."""
        if self.state == CommitState.NOT_COMMITTED:
            self.state = CommitState.UNKNOWN

    def rolled_back(self) -> None:
        """Confirm rollback only before any commit attempt."""
        if self.state == CommitState.NOT_COMMITTED:
            self.state = CommitState.ROLLED_BACK
