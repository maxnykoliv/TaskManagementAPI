import pytest

from app.domain.enums import TaskStatus as S
from app.domain.status_machine import can_transition


@pytest.mark.parametrize(
    "current,target",
    [
        (S.BACKLOG, S.IN_PROGRESS),
        (S.IN_PROGRESS, S.REVIEW),
        (S.REVIEW, S.DONE),
        (S.BACKLOG, S.CANCELLED),
        (S.IN_PROGRESS, S.CANCELLED),
    ],
)
def test_allowed(current, target):
    assert can_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (S.IN_PROGRESS, S.BACKLOG),  # backwards
        (S.REVIEW, S.IN_PROGRESS),  # backwards
        (S.BACKLOG, S.DONE),  # skips a step
        (S.REVIEW, S.CANCELLED),  # review can only go to done
        (S.DONE, S.IN_PROGRESS),  # from a final state
        (S.CANCELLED, S.BACKLOG),  # from a final state
    ],
)
def test_forbidden(current, target):
    assert not can_transition(current, target)
