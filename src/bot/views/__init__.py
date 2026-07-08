"""Views package for UI components."""

from .modals import SubmissionModal, GradingModal
from .buttons import SubmitButton, GradeButton
from .selects import (
    ClassSelect,
    StudentSelect,
    RelatorSelect,
    MultiStudentSelect,
)
from .select_views import (
    SetRelatorView,
    SetRelatorViewV2,
    ApproveStudentView,
    ClassInfoView,
    BatchApproveView,
    DosenSelect,
)

__all__ = [
    # Modals
    "SubmissionModal",
    "GradingModal",
    # Buttons
    "SubmitButton",
    "GradeButton",
    # Selects
    "ClassSelect",
    "StudentSelect",
    "RelatorSelect",
    "MultiStudentSelect",
    "DosenSelect",
    # Views
    "SetRelatorView",
    "SetRelatorViewV2",
    "ApproveStudentView",
    "ClassInfoView",
    "BatchApproveView",
]
