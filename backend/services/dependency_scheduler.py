from collections import defaultdict
from datetime import timedelta
from sqlalchemy.orm import Session

from backend.models import Task


def validate_no_dependency_cycle(
    db: Session,
    task_id: int | None,
    depends_on_id: int | None,
) -> None:
    """Ensure setting task.depends_on_id does not introduce a cycle in the task graph."""
    if depends_on_id is None:
        return
    if task_id is not None and task_id == depends_on_id:
        raise ValueError("A task cannot depend on itself")

    visited: set[int] = set()
    if task_id is not None:
        visited.add(task_id)

    curr_id: int | None = depends_on_id
    while curr_id is not None:
        if curr_id in visited:
            raise ValueError("Circular dependency detected in task chain")
        visited.add(curr_id)
        parent = db.query(Task).filter(Task.id == curr_id).first()
        if not parent:
            break
        curr_id = parent.depends_on_id


def cascade_dependent_tasks(db: Session, predecessor: Task) -> list[Task]:
    """Recursively shift downstream dependent tasks forward if predecessor's end date overlaps them."""
    cascaded: list[Task] = []
    visited: set[int] = {predecessor.id}

    def _walk(pred: Task):
        pred_end = pred.due_date or pred.start_date
        if pred_end is None:
            return

        dependents = db.query(Task).filter(Task.depends_on_id == pred.id).all()
        for child in dependents:
            if child.id in visited:
                continue
            visited.add(child.id)

            min_allowed_start = pred_end + timedelta(days=1)
            child_start = child.start_date or child.due_date
            child_end = child.due_date or child.start_date

            if child_start is None:
                child.start_date = min_allowed_start
                child.due_date = min_allowed_start
                db.flush()
                cascaded.append(child)
                _walk(child)
            elif child_start < min_allowed_start:
                duration_days = max((child_end - child_start).days, 0) if child_end else 0
                child.start_date = min_allowed_start
                child.due_date = min_allowed_start + timedelta(days=duration_days)
                db.flush()
                cascaded.append(child)
                _walk(child)

    _walk(predecessor)
    return cascaded


def compute_critical_path(tasks: list[Task]) -> tuple[list[int], int]:
    """Compute the longest dependency path (in days) among incomplete tasks in a project."""
    incomplete = [t for t in tasks if t.status != "done"]
    if not incomplete:
        return [], 0

    task_map = {t.id: t for t in incomplete if t.id is not None}
    children_map: dict[int, list[int]] = defaultdict(list)
    for t in incomplete:
        if t.depends_on_id and t.depends_on_id in task_map:
            children_map[t.depends_on_id].append(t.id)

    def _task_duration(t: Task) -> int:
        if t.start_date and t.due_date and t.due_date >= t.start_date:
            return (t.due_date - t.start_date).days + 1
        return 1

    memo: dict[int, tuple[int, list[int]]] = {}

    def _longest_from(tid: int, stack: set[int]) -> tuple[int, list[int]]:
        if tid in memo:
            return memo[tid]
        if tid in stack:
            return 0, []

        stack.add(tid)
        t_obj = task_map[tid]
        own_days = _task_duration(t_obj)

        best_child_days = 0
        best_child_chain: list[int] = []
        for cid in children_map.get(tid, []):
            c_days, c_chain = _longest_from(cid, stack)
            if c_days > best_child_days:
                best_child_days = c_days
                best_child_chain = c_chain

        stack.remove(tid)
        res = (own_days + best_child_days, [tid] + best_child_chain)
        memo[tid] = res
        return res

    best_total = 0
    best_path: list[int] = []
    for tid in sorted(task_map.keys()):
        total_d, chain = _longest_from(tid, set())
        if total_d > best_total:
            best_total = total_d
            best_path = chain

    return best_path, best_total
