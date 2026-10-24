from app.domain.enums import TaskStatus as S

ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    S.BACKLOG: frozenset({S.IN_PROGRESS, S.CANCELLED}),
    S.IN_PROGRESS: frozenset({S.REVIEW, S.CANCELLED}),
    S.REVIEW: frozenset({S.DONE}),
    S.DONE: frozenset(),
    S.CANCELLED: frozenset(),
}

ACTIVE_STATUSES = frozenset({S.BACKLOG, S.IN_PROGRESS, S.REVIEW})
FINAL_STATUSES = frozenset({S.DONE, S.CANCELLED})


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS[current]
