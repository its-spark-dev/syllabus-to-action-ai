from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple


DATE_FORMATS_WITH_YEAR = (
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d",
)

DATE_FORMATS_NO_YEAR = (
    "%b %d",
    "%B %d",
    "%m/%d",
)


def _parse_date(date_str: str, year_hint: int) -> Optional[date]:
    cleaned = date_str.strip()

    for fmt in DATE_FORMATS_WITH_YEAR:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    for fmt in DATE_FORMATS_NO_YEAR:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(year=year_hint).date()
        except ValueError:
            continue

    return None


def _add_task(plan: Dict[str, List[str]], week_label: str, task: str) -> None:
    if not task:
        return
    if week_label not in plan:
        plan[week_label] = []
    if task not in plan[week_label]:
        plan[week_label].append(task)


def _week_label(week_index: int) -> str:
    return f"Week {week_index}"


def _collect_dated_items(
    items: Iterable[Dict[str, object]],
    year_hint: int,
) -> List[Tuple[date, Dict[str, object]]]:
    dated_items: List[Tuple[date, Dict[str, object]]] = []
    for item in items:
        date_str = item.get("date")
        if not isinstance(date_str, str) or not date_str:
            continue
        parsed_date = _parse_date(date_str, year_hint)
        if parsed_date:
            dated_items.append((parsed_date, item))
    return dated_items


def generate_weekly_plan(
    parsed_syllabi: List[Dict[str, object]],
    term_start_date: str = "2026-01-12",
) -> Dict[str, List[str]]:
    """
    Generate a weekly study plan from parsed syllabus data.

    Output shape:
    {
        "Week 1": ["Assignment A", "Read Chapter 1"],
        "Week 2": ["Exam prep", ...],
        ...
    }
    """
    plan: Dict[str, List[str]] = {}
    today = date.today()

    # Transform the flat assessment list into a course -> kind -> items map.
    # This keeps downstream planning logic grouped by course and assessment type.
    courses: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
    for item in parsed_syllabi:
        course_name = item.get("course") or "Unknown Course"
        kind = item.get("kind") or "other"
        if course_name not in courses:
            courses[course_name] = {"exam": [], "homework": [], "project": [], "other": []}
        kind_bucket = kind if kind in courses[course_name] else "other"
        courses[course_name][kind_bucket].append(item)

    all_dated: List[Tuple[date, Dict[str, object]]] = []
    for course_items in courses.values():
        for items in course_items.values():
            all_dated.extend(_collect_dated_items(items, today.year))

    start_date = _parse_date(term_start_date, today.year) or today
    end_date = max((item[0] for item in all_dated), default=start_date)
    last_week_index = max(1, ((end_date - start_date).days // 7) + 1)

    for course_name, course_items in courses.items():
        for kind, items in course_items.items():
            for item in items:
                title = item.get("title") or "Untitled assessment"
                if "weekly" in title.lower():
                    # Schedule weekly tasks across every calendar week of the term.
                    for week_index in range(1, last_week_index + 1):
                        _add_task(plan, _week_label(week_index), f"{course_name}: {title}")
                    continue
                date_str = item.get("date")
                if isinstance(date_str, str) and date_str:
                    parsed_date = _parse_date(date_str, today.year)
                else:
                    parsed_date = None

                # Only schedule tasks with valid dates in the weekly plan.
                # Undated items remain in parsed_syllabi for downstream study-guide use.
                if not parsed_date:
                    continue

                week_index = max(1, ((parsed_date - start_date).days // 7) + 1)
                _add_task(plan, _week_label(week_index), f"{course_name}: {title}")

                weight = item.get("weight_percent")
                if kind == "exam":
                    # Distribute prep across the two weeks before the exam due week.
                    if isinstance(weight, (int, float)):
                        if weight <= 20:
                            sessions = 1
                        elif weight <= 30:
                            sessions = 2
                        else:
                            sessions = 3
                    else:
                        sessions = 1

                    prep_weeks = [max(1, week_index - 1), max(1, week_index - 2)]
                    prep_weeks = list(dict.fromkeys(prep_weeks))

                    # Allocate at least one session to each prep week when possible.
                    week_assignments: List[int] = []
                    if sessions >= 2 and len(prep_weeks) == 2:
                        week_assignments.extend(prep_weeks)
                        sessions_remaining = sessions - 2
                    else:
                        sessions_remaining = sessions

                    for _ in range(sessions_remaining):
                        week_assignments.append(prep_weeks[0])

                    week_counts: Dict[int, int] = {}
                    for assigned_week in week_assignments:
                        week_counts[assigned_week] = week_counts.get(assigned_week, 0) + 1

                    # Avoid identical duplicate tasks in the same week by labeling extra sessions.
                    for assigned_week, count in week_counts.items():
                        for session_index in range(1, count + 1):
                            suffix = "" if session_index == 1 else f" (Session {session_index})"
                            _add_task(
                                plan,
                                _week_label(assigned_week),
                                f"{course_name}: Prep for {title}{suffix}",
                            )

    return plan


# Example: generate_weekly_plan([...], term_start_date="2026-01-12")
# -> {"Week 1": ["CSE 2331: Midterm 1", "CSE 2331: Prep for Midterm 1", ...]}
# Example: generate_weekly_plan([...])
# -> {"Week 3": ["BIO 101: Final Exam"], "Week 1": ["BIO 101: Prep for Final Exam", ...]}
