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
        (S.IN_PROGRESS, S.BACKLOG),   # назад
        (S.REVIEW, S.IN_PROGRESS),    # назад
        (S.BACKLOG, S.DONE),          # стрибок
        (S.REVIEW, S.CANCELLED),      # у ТЗ не дозволено
        (S.DONE, S.IN_PROGRESS),      # з фінального
        (S.CANCELLED, S.BACKLOG),     # з фінального
    ],
)
def test_forbidden(current, target):
    assert not can_transition(current, target)