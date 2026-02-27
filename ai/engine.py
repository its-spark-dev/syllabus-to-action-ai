from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


DATE_FORMATS = (
    "%b %d, %Y",
    "%B %d, %Y",
    "%b %d",
    "%B %d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m/%d",
    "%Y-%m-%d",
)


def _remove_trailing_punctuation(value: str) -> str:
    return re.sub(r"[^\w\s]+$", "", value)


def _parse_date(date_str: str, default_year: Optional[int] = None) -> Optional[date]:
    cleaned = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            if "%Y" not in fmt:
                year = default_year if default_year is not None else date.today().year
                return parsed.replace(year=year)
            return parsed
        except ValueError:
            continue
    return None


def _estimate_minutes(kind: str, title: str, is_prep: bool) -> int:
    lowered = title.lower()
    if is_prep and "final" in lowered:
        return 180
    if is_prep and kind == "exam":
        return 120
    if kind == "homework":
        return 90
    if kind == "project":
        return 120
    return 90


def _priority_for(weight: float, days_until_due: Optional[int]) -> str:
    if weight >= 30 or (days_until_due is not None and days_until_due <= 7):
        return "High"
    if weight >= 15 or (days_until_due is not None and days_until_due <= 14):
        return "Med"
    return "Low"


def _due_soon_score(days_until_due: Optional[int]) -> int:
    if days_until_due is None:
        return 0
    if days_until_due <= 3:
        return 50
    if days_until_due <= 7:
        return 35
    if days_until_due <= 14:
        return 25
    if days_until_due <= 21:
        return 15
    return 0


def _priority_rank(priority: str) -> int:
    if priority == "High":
        return 0
    if priority == "Med":
        return 1
    return 2


def _priority_from_score(score: float, weight_for_priority: float) -> str:
    if score >= 75:
        priority = "High"
    elif score >= 50:
        priority = "Med"
    else:
        priority = "Low"

    if weight_for_priority >= 30:
        return "High"
    if weight_for_priority >= 20 and priority == "Low":
        return "Med"
    return priority


def _priority_level(priority: str) -> int:
    if priority == "High":
        return 2
    if priority == "Med":
        return 1
    return 0


def _priority_from_level(level: int) -> str:
    if level >= 2:
        return "High"
    if level == 1:
        return "Med"
    return "Low"


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    bounded = max(0.0, min(100.0, pct))
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * bounded / 100.0
    low = int(position)
    high = min(len(ordered) - 1, low + 1)
    if low == high:
        return float(ordered[low])
    ratio = position - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * ratio)


def _max_compression_window(
    weighted_dates: List[Tuple[date, float]],
    max_days: int = 5,
) -> Tuple[float, int]:
    if len(weighted_dates) < 2:
        return 0.0, 0
    ordered = sorted(weighted_dates, key=lambda item: item[0])
    best_weight = 0.0
    best_window = 0
    for index, (left_date, left_weight) in enumerate(ordered[:-1]):
        for right_date, right_weight in ordered[index + 1:]:
            window = (right_date - left_date).days
            if window < 0:
                continue
            if window > max_days:
                break
            combined = left_weight + right_weight
            if combined > best_weight or (combined == best_weight and window < best_window):
                best_weight = combined
                best_window = window
    return best_weight, best_window


def _build_summary(
    weekly_plan: Dict[str, List[Dict[str, object]]],
    today: Optional[date] = None,
) -> Dict[str, List[Dict[str, object]]]:
    today = today or date.today()
    all_tasks: List[Dict[str, object]] = []
    for tasks in weekly_plan.values():
        for task in tasks:
            due_date_raw = task.get("date")
            due_date = (
                _parse_date(due_date_raw, default_year=today.year)
                if isinstance(due_date_raw, str) and due_date_raw
                else None
            )
            if not isinstance(due_date, date) or due_date < today:
                continue
            all_tasks.append(
                {
                    "task": task,
                    "priority_rank": 2 - _priority_rank(str(task.get("priority", "Low"))),
                    "due_date": due_date,
                }
            )
    candidates_7_day = [
        item for item in all_tasks if (item["due_date"] - today).days <= 7
    ]
    candidates_7_day.sort(key=lambda item: (item["due_date"], -item["priority_rank"]))

    candidates_14_day = [
        item for item in all_tasks if (item["due_date"] - today).days <= 14
    ]
    candidates_14_day.sort(key=lambda item: (item["due_date"], -item["priority_rank"]))

    if candidates_7_day:
        selected = candidates_7_day[:3]
    else:
        selected = candidates_14_day[:3]

    return {"this_weeks_focus": [item["task"] for item in selected[:3]]}


def _match_category(label: str, item: Dict[str, object]) -> bool:
    label_lower = label.lower()
    title_lower = (item.get("title") or "").lower()
    kind = item.get("kind") or "other"

    if any(token in label_lower for token in ("homework", "assignment", "problem set")):
        return kind == "homework"
    if any(token in label_lower for token in ("project", "capstone")):
        return kind == "project" or "project" in title_lower
    if "quiz" in label_lower:
        return "quiz" in title_lower
    if any(token in label_lower for token in ("midterm", "final", "exam")):
        return kind == "exam" or any(token in title_lower for token in ("exam", "midterm", "final"))
    if any(token in label_lower for token in ("participation", "attendance")):
        return "participation" in title_lower
    return False


def _category_info_for_item(
    grading_categories: Dict[str, float],
    item: Dict[str, object],
) -> Tuple[Optional[str], float]:
    for label, weight in grading_categories.items():
        if _match_category(label, item):
            return label, float(weight)
    return None, 0.0


def _compute_priority_score(
    weight_for_priority: float,
    days_until_due: Optional[int],
    kind: str,
    raw_title: str,
    is_prep: bool,
) -> float:
    score = weight_for_priority
    if weight_for_priority >= 30:
        score += 35
    elif weight_for_priority >= 20:
        score += 25
    elif weight_for_priority >= 10:
        score += 10

    score += _due_soon_score(days_until_due)

    if kind == "exam" and not is_prep:
        score += 25
    if is_prep:
        score -= 10

    if kind == "homework" and (days_until_due is None or days_until_due > 5):
        score = min(score, 60)

    return score


def _distribute_homework_weights(
    items: List[Dict[str, object]],
    grading_categories: Dict[str, float],
) -> Dict[Tuple[str, str], float]:
    homework_weight = None
    for label, value in grading_categories.items():
        if "homework" in label.lower() or "assignments" in label.lower():
            homework_weight = float(value)
            break
    if homework_weight is None:
        return {}

    homework_items = [
        item
        for item in items
        if item.get("kind") == "homework"
        and not isinstance(item.get("weight_percent"), (int, float))
    ]
    if not homework_items:
        return {}

    per_item = homework_weight / len(homework_items)
    distributed: Dict[Tuple[str, str], float] = {}
    for item in homework_items:
        course_name = item.get("course") or "Unknown Course"
        title = item.get("title") or ""
        if title:
            distributed[(course_name, title)] = per_item
    return distributed


def _distribute_category_weights(
    items: List[Dict[str, object]],
    grading_categories: Dict[str, float],
) -> Dict[Tuple[str, str], float]:
    distributed: Dict[Tuple[str, str], float] = {}
    if not grading_categories:
        return distributed

    unweighted_items = [
        item
        for item in items
        if not isinstance(item.get("weight_percent"), (int, float))
    ]

    for label, category_weight in grading_categories.items():
        matches = [item for item in unweighted_items if _match_category(label, item)]
        if not matches:
            continue
        per_item = float(category_weight) / len(matches)
        for item in matches:
            course_name = item.get("course") or "Unknown Course"
            title = item.get("title") or ""
            if title:
                distributed[(course_name, title)] = per_item
    return distributed


def _build_tactical_tips(
    grading_breakdown: Dict[str, float],
    upcoming_assessments: List[Dict[str, object]],
) -> List[str]:
    tips: List[str] = []
    if grading_breakdown:
        top_items = sorted(grading_breakdown.items(), key=lambda item: item[1], reverse=True)[:2]
        top_labels = ", ".join(label for label, _ in top_items)
        tips.append(f"Prioritize {top_labels}; higher weight items deserve more time.")
    if upcoming_assessments:
        tips.append("Front-load prep for the next upcoming assessment.")
    tips.append("Break large tasks into 2-3 focused sessions per week.")
    tips.append("Review feedback from early homework to improve exam performance.")
    return tips[:5]


def _dedup_key(task: Dict[str, object]) -> Tuple[object, object, object]:
    raw_task = task.get("task") or ""
    course = task.get("course")
    due = task.get("due")
    if raw_task.lower().startswith("prep for "):
        base = raw_task[9:]
        base = re.sub(r"\s*\(session\s*\d+\)\s*$", "", base, flags=re.IGNORECASE)
        normalized_task = f"Prep for {base.strip()}"
    else:
        normalized_task = raw_task
    return (course, normalize_title(normalized_task), due)


def normalize_title(title: str) -> str:
    cleaned = title.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[-–—:|,.;!?]+\s*$", "", cleaned)
    cleaned = re.sub(r"\b(the|exam|final)\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = _remove_trailing_punctuation(cleaned)
    return cleaned.strip()


def _deduplicate_tasks(
    tasks: List[Dict[str, object]],
    seen: Optional[set] = None,
) -> List[Dict[str, object]]:
    deduped: List[Dict[str, object]] = []
    seen_keys = seen if seen is not None else set()
    for task in tasks:
        key = _dedup_key(task)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(task)
    return deduped


USE_REAL_AI = False


def deterministic_ai_refinement(
    parsed_syllabi: List[Dict[str, object]],
    weekly_plan: Dict[str, List[str]],
    anchor_date: Optional[date] = None,
) -> Dict[str, Dict[str, object]]:
    """
    Rule-based fallback that deterministically refines weekly tasks and builds a study guide.

    Returns:
    {
        "weekly_plan": Dict[str, List[Dict]],
        "study_guide": Dict[str, Dict],
    }
    """
    # Group the flat assessment items by course to build summaries and lookups.
    courses: Dict[str, List[Dict[str, object]]] = {}
    for item in parsed_syllabi:
        course_name = item.get("course") or "Unknown Course"
        courses.setdefault(course_name, []).append(item)

    item_lookup: Dict[Tuple[str, str], Dict[str, object]] = {}
    for course_name, items in courses.items():
        normalized_course_name = str(course_name).strip()
        for item in items:
            title = str(item.get("title") or "")
            normalized_item_title = normalize_title(title)
            if normalized_item_title:
                item_lookup[(normalized_course_name, normalized_item_title)] = item

    distributed_weights_by_course: Dict[str, Dict[Tuple[str, str], float]] = {}
    grading_categories_by_course: Dict[str, Dict[str, float]] = {}
    for course_name, items in courses.items():
        grading_categories: Dict[str, float] = {}
        course_tasks = [item for item in items if item.get("title") != "__GRADING_CATEGORIES__"]
        for item in items:
            if item.get("title") == "__GRADING_CATEGORIES__":
                categories = item.get("categories")
                if isinstance(categories, dict):
                    for label, value in categories.items():
                        if isinstance(value, (int, float)):
                            grading_categories[label] = float(value)
        grading_categories_by_course[course_name] = grading_categories
        distributed_weights_by_course[course_name] = _distribute_category_weights(
            course_tasks,
            grading_categories,
        )

    refined_weekly_plan: Dict[str, List[Dict[str, object]]] = {}
    today = anchor_date or date.today()
    prep_load_by_course_week: Dict[str, Dict[str, int]] = {}
    global_seen_tasks: set = set()

    for week_label, tasks in weekly_plan.items():
        refined_tasks: List[Dict[str, object]] = []
        for task in tasks:
            course_part, _, title_part = task.partition(": ")
            course_name = course_part or "Unknown Course"
            raw_title = title_part or task
            is_prep = raw_title.lower().startswith("prep for ")
            title = raw_title[9:] if is_prep else raw_title
            normalized_course_name = course_name.strip()
            normalized_lookup_title = normalize_title(title)
            item = item_lookup.get((normalized_course_name, normalized_lookup_title))

            kind = "other"
            date_str = None
            explicit_weight = 0.0
            if item:
                kind = item.get("kind") or "other"
                title_text = (item.get("title") or "").lower()
                if any(token in title_text for token in ("project", "milestone", "submission")):
                    kind = "project"
                date_str = item.get("date")
                weight_value = item.get("weight_percent")
                if isinstance(weight_value, (int, float)):
                    explicit_weight = float(weight_value)

            due_date = (
                _parse_date(date_str, default_year=today.year)
                if isinstance(date_str, str) and date_str
                else None
            )
            days_until_due = (due_date - today).days if due_date else None
            category_label = None
            category_weight = 0.0
            distributed_weight = 0.0
            if item:
                matched_course_name = str(item.get("course") or course_name)
                matched_title = str(item.get("title") or title)
                if matched_course_name in grading_categories_by_course:
                    category_label, category_weight = _category_info_for_item(
                        grading_categories_by_course[matched_course_name],
                        item,
                    )
                    distributed_weight = distributed_weights_by_course.get(
                        matched_course_name,
                        {},
                    ).get(
                        (matched_course_name, matched_title),
                        0.0,
                    )
            weight_for_priority = explicit_weight if explicit_weight > 0 else distributed_weight
            display_weight = 0.0 if is_prep else explicit_weight
            weight_effective = 0.0 if is_prep else weight_for_priority
            real_assessment_priority: Optional[str] = None
            priority_score = _compute_priority_score(
                weight_for_priority,
                days_until_due,
                kind,
                raw_title,
                is_prep,
            )
            if is_prep:
                real_assessment_score = _compute_priority_score(
                    weight_for_priority,
                    days_until_due,
                    kind,
                    title,
                    False,
                )
                priority_score = min(priority_score, real_assessment_score - 1.0)
                real_assessment_priority = _priority_from_score(
                    real_assessment_score,
                    weight_for_priority,
                )

            priority = _priority_from_score(priority_score, weight_for_priority)
            if is_prep and real_assessment_priority:
                prep_level = _priority_level(priority)
                real_level = _priority_level(real_assessment_priority)
                if real_level - prep_level > 1:
                    priority = _priority_from_level(real_level - 1)

            exam_guard = (
                kind == "exam"
                and not is_prep
                and weight_for_priority >= 20
                and days_until_due is not None
                and days_until_due <= 14
            )
            estimated_minutes = _estimate_minutes(kind, title, is_prep)
            reason = f"{kind} task"
            if display_weight:
                reason = f"{reason}; weight {display_weight:.0f}%"
            if due_date:
                reason = f"{reason}; due {date_str}"

            refined_tasks.append(
                {
                    "course": course_name,
                    "task": raw_title,
                    "priority": priority,
                    "priority_score": priority_score,
                    "reason": reason,
                    "estimated_minutes": estimated_minutes,
                    "due": date_str,
                    "date": date_str,
                    "weight_percent": display_weight,
                    "weight_effective": weight_effective,
                    "kind": kind,
                    "category_label": category_label,
                    "category_weight": distributed_weight,
                    "exam_guard": exam_guard,
                }
            )

        refined_tasks.sort(
            key=lambda item: (
                -int(bool(item.get("exam_guard"))),
                -float(item.get("priority_score", 0.0)),
                _parse_date(item.get("due"), default_year=today.year) if item.get("due") else date.max,
            )
        )
        refined_tasks = _deduplicate_tasks(refined_tasks)
        refined_tasks = _deduplicate_tasks(refined_tasks, global_seen_tasks)
        refined_weekly_plan[week_label] = refined_tasks
        for task in refined_tasks:
            if not task.get("task", "").lower().startswith("prep for"):
                continue
            course_name = task.get("course") or "Unknown Course"
            prep_load_by_course_week.setdefault(course_name, {})
            prep_load_by_course_week[course_name][week_label] = (
                prep_load_by_course_week[course_name].get(week_label, 0)
                + int(task.get("estimated_minutes") or 0)
            )

    course_week_tasks: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
    for week_label, tasks in refined_weekly_plan.items():
        for task in tasks:
            course_name = task.get("course") or "Unknown Course"
            course_week_tasks.setdefault(course_name, {}).setdefault(week_label, []).append(task)

    study_guide: Dict[str, Dict[str, object]] = {}
    for course_name, items in courses.items():
        grading_breakdown: Dict[str, float] = {}
        grading_categories: Dict[str, float] = {}
        total_weight = 0.0
        upcoming_assessments: List[Tuple[date, Dict[str, object]]] = []
        high_weight_dates: List[date] = []
        term_end: Optional[date] = None
        course_tasks: List[Dict[str, object]] = []

        for item in items:
            if item.get("title") == "__GRADING_CATEGORIES__":
                categories = item.get("categories")
                if isinstance(categories, dict):
                    for label, value in categories.items():
                        if isinstance(value, (int, float)):
                            grading_categories[label] = float(value)
                continue

            course_tasks.append(item)
            weight = item.get("weight_percent")
            title = item.get("title") or "Unlabeled"
            date_str = item.get("date")
            parsed_date = (
                _parse_date(date_str, default_year=today.year)
                if isinstance(date_str, str) and date_str
                else None
            )
            if parsed_date:
                upcoming_assessments.append((parsed_date, item))
                if term_end is None or parsed_date > term_end:
                    term_end = parsed_date
                if isinstance(weight, (int, float)) and weight >= 25:
                    high_weight_dates.append(parsed_date)

        # CATEGORY OVERRIDE LOGIC – DO NOT REMOVE
        # Study Guide should reflect official grading categories when present.
        if grading_categories:
            # Use all grading categories as-is; do not filter by task type.
            grading_breakdown = dict(grading_categories)
            total_weight_detected = sum(grading_categories.values())
        else:
            grading_breakdown = {}
            for item in course_tasks:
                weight = item.get("weight_percent")
                if not isinstance(weight, (int, float)):
                    continue
                title = item.get("title") or "Unlabeled"
                title_lower = title.lower()
                if any(token in title_lower for token in ("milestone", "submission")):
                    continue
                grading_breakdown[title] = float(weight)
            total_weight_detected = sum(grading_breakdown.values())

        upcoming_assessments.sort(key=lambda item: item[0])
        upcoming_list: List[Dict[str, object]] = []
        for _, item in upcoming_assessments:
            weight_value = item.get("weight_percent")
            if isinstance(weight_value, (int, float)):
                weight_display = float(weight_value)
            else:
                weight_display = None

            upcoming_list.append(
                {
                    "title": item.get("title") or "Unlabeled",
                    "kind": item.get("kind") or "other",
                    "date": item.get("date"),
                    "weight_percent": weight_display,
                }
            )

        risk_analysis: List[str] = []
        high_weight_dates.sort()
        # Only flag clustering when high-weight assessments are tightly packed (<= 5 days apart).
        for left, right in zip(high_weight_dates, high_weight_dates[1:]):
            if (right - left).days <= 5:
                risk_analysis.append("Heavy assessment clustering detected.")
                break

        if term_end and any((term_end - due).days <= 14 for due in high_weight_dates):
            risk_analysis.append("High cumulative workload near term end.")

        course_prep = prep_load_by_course_week.get(course_name, {})
        if any(minutes > 300 for minutes in course_prep.values()):
            risk_analysis.append("Consider starting review earlier.")

        # Surface grading categories first, then individual items if present.
        # Validate grading breakdown totals for warning messages.
        warnings: List[str] = []
        if total_weight_detected > 100:
            warnings.append("⚠ Detected grading breakdown exceeds 100%. Please verify syllabus.")
        if total_weight_detected < 90:
            warnings.append("⚠ Grading breakdown may be incomplete.")

        weekly_metrics: Dict[str, Dict[str, object]] = {}
        course_weeks = course_week_tasks.get(course_name, {})
        weekly_raw: Dict[str, Dict[str, object]] = {}
        for week_label, tasks in course_weeks.items():
            exam_count = 0
            milestone_count = 0
            weighted_exam_count = 0
            high_weight_exam_count = 0
            weekly_minutes_sum = 0
            weekly_weight_sum = 0.0
            weighted_due_dates: List[Tuple[date, float]] = []
            for task in tasks:
                task_name = str(task.get("task", "")).lower()
                if task.get("kind") == "exam" and not task_name.startswith("prep for"):
                    exam_count += 1
                    weight_effective = float(task.get("weight_effective") or task.get("weight_percent") or 0.0)
                    if weight_effective >= 20:
                        weighted_exam_count += 1
                    if weight_effective >= 25:
                        high_weight_exam_count += 1
                if task.get("kind") == "project" and any(
                    token in task_name for token in ("milestone", "submission")
                ):
                    milestone_count += 1
                weekly_minutes_sum += int(task.get("estimated_minutes") or 0)
                weekly_weight_sum += float(task.get("weight_effective") or 0.0)
                due_raw = task.get("due") or task.get("date")
                if isinstance(due_raw, str) and due_raw:
                    parsed_due = _parse_date(due_raw, default_year=today.year)
                    task_weight = float(task.get("weight_effective") or task.get("weight_percent") or 0.0)
                    if isinstance(parsed_due, date) and task_weight > 0 and not task_name.startswith("prep for"):
                        weighted_due_dates.append((parsed_due, task_weight))
            task_count = len(tasks)
            compression_weight, compression_window = _max_compression_window(weighted_due_dates, max_days=5)

            weekly_raw[week_label] = {
                "weekly_weight_sum": weekly_weight_sum,
                "weekly_stress_score": weekly_minutes_sum,
                "task_count": task_count,
                "exam_count": exam_count,
                "milestone_count": milestone_count,
                "high_weight_exam_count": high_weight_exam_count,
                "compression_weight_percent": compression_weight,
                "compression_window_days": compression_window,
            }

            if weighted_exam_count >= 2:
                warnings.append(f"Assessment collision detected in {week_label}.")

        stress_values = [
            float(week_data.get("weekly_stress_score") or 0.0)
            for week_data in weekly_raw.values()
        ]
        p70_stress = _percentile(stress_values, 70.0)
        p85_stress = _percentile(stress_values, 85.0)

        sorted_week_labels = sorted(weekly_raw.keys(), key=_week_label_sort_key)
        previous_stress: Optional[float] = None
        for week_label in sorted_week_labels:
            week_data = weekly_raw[week_label]
            weekly_stress_score = float(week_data.get("weekly_stress_score") or 0.0)
            weekly_weight_sum = float(week_data.get("weekly_weight_sum") or 0.0)
            exam_count = int(week_data.get("exam_count") or 0)
            high_weight_exam_count = int(week_data.get("high_weight_exam_count") or 0)
            compression_weight = float(week_data.get("compression_weight_percent") or 0.0)
            compression_window = int(week_data.get("compression_window_days") or 0)

            if previous_stress is not None and weekly_stress_score > previous_stress:
                base = previous_stress if previous_stress > 0 else 1.0
                stress_acceleration_percent = ((weekly_stress_score - previous_stress) / base) * 100.0
            else:
                stress_acceleration_percent = 0.0
            previous_stress = weekly_stress_score

            risk_score = 0
            stress_band = "base"
            if p85_stress > 0 and weekly_stress_score >= p85_stress:
                risk_score += 3
                stress_band = "p85+"
            elif p70_stress > 0 and weekly_stress_score >= p70_stress:
                risk_score += 2
                stress_band = "p70+"

            if weekly_weight_sum >= 35:
                risk_score += 2
            elif weekly_weight_sum >= 20:
                risk_score += 1

            if exam_count >= 2:
                risk_score += 1
            if high_weight_exam_count >= 1:
                risk_score += 2

            if stress_acceleration_percent >= 50:
                risk_score += 2
            elif stress_acceleration_percent >= 25:
                risk_score += 1

            if compression_weight >= 30 and 0 <= compression_window <= 5:
                risk_score += 2

            if risk_score >= 6:
                risk_level = "High Risk"
            elif risk_score >= 3:
                risk_level = "Elevated"
            else:
                risk_level = "Normal"

            weekly_metrics[week_label] = {
                **week_data,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "stress_band": stress_band,
                "p70_stress": round(p70_stress, 1),
                "p85_stress": round(p85_stress, 1),
                "stress_acceleration_percent": round(stress_acceleration_percent, 1),
                "compression_weight_percent": round(compression_weight, 1),
                "compression_window_days": compression_window,
            }

        sorted_weeks: List[str] = []
        if course_weeks:
            sorted_weeks = sorted(
                course_weeks.keys(),
                key=lambda label: int(label.split()[1]) if label.split()[-1].isdigit() else 0,
            )
            last_three_weeks = sorted_weeks[-3:]
            end_term_weight = sum(
                weekly_metrics.get(week, {}).get("weekly_weight_sum", 0.0)
                for week in last_three_weeks
            )
            if end_term_weight > 40:
                warnings.append("High cumulative workload near term end.")

        for week_label in sorted_weeks:
            week_risk_level = str(weekly_metrics.get(week_label, {}).get("risk_level", "Normal"))
            risk_analysis.append(f"{week_label} risk level: {week_risk_level}.")
            if week_risk_level in {"Elevated", "High Risk"}:
                risk_analysis.append(f"High workload detected in {week_label}.")

        study_guide[course_name] = {
            "grading_categories": grading_categories,
            "grading_breakdown": grading_breakdown,
            "total_weight_detected": total_weight_detected,
            "tactical_tips": _build_tactical_tips(grading_breakdown, upcoming_list),
            "upcoming_assessments": upcoming_list,
            "risk_analysis": risk_analysis,
            "warnings": warnings,
            "weekly_metrics": weekly_metrics,
        }

    return {
        "weekly_plan": refined_weekly_plan,
        "study_guide": study_guide,
        "summary": _build_summary(refined_weekly_plan, today=today),
    }


def _week_label_sort_key(week_label: str) -> int:
    parts = str(week_label).strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


def _risk_level_rank(risk_level: str) -> int:
    if risk_level == "Critical Risk":
        return 3
    if risk_level == "High Risk":
        return 2
    if risk_level == "Elevated":
        return 1
    return 0


def _aggregate_weekly_metrics(study_guide: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    aggregated: Dict[str, Dict[str, object]] = {}
    if not isinstance(study_guide, dict):
        return aggregated

    for info in study_guide.values():
        if not isinstance(info, dict):
            continue
        weekly_metrics = info.get("weekly_metrics", {})
        if not isinstance(weekly_metrics, dict):
            continue
        for week_label, week_data in weekly_metrics.items():
            if not isinstance(week_data, dict):
                continue
            week = str(week_label)
            current = aggregated.setdefault(
                week,
                {
                    "weekly_weight_sum": 0.0,
                    "weekly_stress_score": 0.0,
                    "task_count": 0,
                    "exam_count": 0,
                    "milestone_count": 0,
                    "high_weight_exam_count": 0,
                    "risk_level": "Normal",
                    "risk_score": 0.0,
                    "stress_acceleration_percent": 0.0,
                    "compression_weight_percent": 0.0,
                    "compression_window_days": 0,
                },
            )

            current["weekly_weight_sum"] = float(current.get("weekly_weight_sum") or 0.0) + float(
                week_data.get("weekly_weight_sum") or 0.0
            )
            current["weekly_stress_score"] = float(current.get("weekly_stress_score") or 0.0) + float(
                week_data.get("weekly_stress_score") or 0.0
            )
            current["task_count"] = int(current.get("task_count") or 0) + int(week_data.get("task_count") or 0)
            current["exam_count"] = int(current.get("exam_count") or 0) + int(week_data.get("exam_count") or 0)
            current["milestone_count"] = int(current.get("milestone_count") or 0) + int(
                week_data.get("milestone_count") or 0
            )
            current["high_weight_exam_count"] = int(current.get("high_weight_exam_count") or 0) + int(
                week_data.get("high_weight_exam_count") or 0
            )

            candidate_score = float(week_data.get("risk_score") or 0.0)
            if candidate_score > float(current.get("risk_score") or 0.0):
                current["risk_score"] = candidate_score

            candidate_acc = float(week_data.get("stress_acceleration_percent") or 0.0)
            if candidate_acc > float(current.get("stress_acceleration_percent") or 0.0):
                current["stress_acceleration_percent"] = candidate_acc

            candidate_compression = float(week_data.get("compression_weight_percent") or 0.0)
            current_compression = float(current.get("compression_weight_percent") or 0.0)
            candidate_window = int(week_data.get("compression_window_days") or 0)
            current_window = int(current.get("compression_window_days") or 0)
            if candidate_compression > current_compression or (
                candidate_compression == current_compression
                and candidate_compression > 0
                and (current_window <= 0 or candidate_window < current_window)
            ):
                current["compression_weight_percent"] = candidate_compression
                current["compression_window_days"] = candidate_window

            existing_level = str(current.get("risk_level") or "Normal")
            candidate_level = str(week_data.get("risk_level") or "Normal")
            if _risk_level_rank(candidate_level) > _risk_level_rank(existing_level):
                current["risk_level"] = candidate_level

    return {
        week: aggregated[week]
        for week in sorted(aggregated.keys(), key=_week_label_sort_key)
    }


def _top_contributors_from_metrics(metrics: Dict[str, object], limit: int = 5) -> List[Dict[str, object]]:
    if not isinstance(metrics, dict):
        return []
    weekly_plan = metrics.get("weekly_plan", {})
    if not isinstance(weekly_plan, dict) or not weekly_plan:
        return []

    engine_summary = build_engine_summary(metrics)
    peak_week = str(engine_summary.get("peak_week") or "")
    tasks = weekly_plan.get(peak_week, [])
    if not isinstance(tasks, list):
        return []

    scored_tasks = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        scored_tasks.append(
            (
                -float(task.get("priority_score") or 0.0),
                -float(task.get("weight_effective") or task.get("weight_percent") or 0.0),
                -int(task.get("estimated_minutes") or 0),
                index,
                task,
            )
        )
    scored_tasks.sort()

    contributors: List[Dict[str, object]] = []
    for _, _, _, index, task in scored_tasks[:max(1, limit)]:
        contributors.append(
            {
                "task_id": f"{peak_week}:{index}",
                "course": task.get("course"),
                "task": task.get("task"),
                "kind": task.get("kind"),
                "due": task.get("due"),
                "stress_contribution": int(task.get("estimated_minutes") or 0),
                "weight_effective": float(task.get("weight_effective") or task.get("weight_percent") or 0.0),
                "priority_score": float(task.get("priority_score") or 0.0),
            }
        )
    return contributors


def build_peak_contributors(metrics: Dict[str, object], limit: int = 5) -> List[Dict[str, object]]:
    return _top_contributors_from_metrics(metrics, limit=limit)


def _recompute_weekly_metrics_from_weekly_plan(
    weekly_plan: Dict[str, List[Dict[str, object]]],
    default_year: int,
) -> Dict[str, Dict[str, object]]:
    weekly_raw: Dict[str, Dict[str, object]] = {}
    for week_label, tasks in weekly_plan.items():
        if not isinstance(tasks, list):
            continue
        exam_count = 0
        high_weight_exam_count = 0
        weekly_minutes_sum = 0
        weekly_weight_sum = 0.0
        weighted_due_dates: List[Tuple[date, float]] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            task_name = str(task.get("task") or "").lower()
            kind = str(task.get("kind") or "other")
            is_prep = task_name.startswith("prep for")
            task_weight = float(task.get("weight_effective") or task.get("weight_percent") or 0.0)
            if kind == "exam" and not is_prep:
                exam_count += 1
                if task_weight >= 25:
                    high_weight_exam_count += 1
            weekly_minutes_sum += int(task.get("estimated_minutes") or 0)
            weekly_weight_sum += task_weight
            due_raw = task.get("due") or task.get("date")
            if isinstance(due_raw, str) and due_raw and task_weight > 0 and not is_prep:
                parsed_due = _parse_date(due_raw, default_year=default_year)
                if isinstance(parsed_due, date):
                    weighted_due_dates.append((parsed_due, task_weight))

        compression_weight, compression_window = _max_compression_window(weighted_due_dates, max_days=5)
        weekly_raw[week_label] = {
            "weekly_weight_sum": weekly_weight_sum,
            "weekly_stress_score": float(weekly_minutes_sum),
            "task_count": len(tasks),
            "exam_count": exam_count,
            "high_weight_exam_count": high_weight_exam_count,
            "compression_weight_percent": compression_weight,
            "compression_window_days": compression_window,
        }

    stress_values = [float(item.get("weekly_stress_score") or 0.0) for item in weekly_raw.values()]
    p70_stress = _percentile(stress_values, 70.0)
    p85_stress = _percentile(stress_values, 85.0)

    weekly_metrics: Dict[str, Dict[str, object]] = {}
    previous_stress: Optional[float] = None
    for week_label in sorted(weekly_raw.keys(), key=_week_label_sort_key):
        raw = weekly_raw[week_label]
        stress = float(raw.get("weekly_stress_score") or 0.0)
        weight = float(raw.get("weekly_weight_sum") or 0.0)
        exam_count = int(raw.get("exam_count") or 0)
        high_weight_exam_count = int(raw.get("high_weight_exam_count") or 0)
        compression_weight = float(raw.get("compression_weight_percent") or 0.0)
        compression_window = int(raw.get("compression_window_days") or 0)

        if previous_stress is not None and stress > previous_stress:
            base = previous_stress if previous_stress > 0 else 1.0
            acceleration = ((stress - previous_stress) / base) * 100.0
        else:
            acceleration = 0.0
        previous_stress = stress

        risk_score = 0
        if p85_stress > 0 and stress >= p85_stress:
            risk_score += 3
        elif p70_stress > 0 and stress >= p70_stress:
            risk_score += 2
        if weight >= 35:
            risk_score += 2
        elif weight >= 20:
            risk_score += 1
        if exam_count >= 2:
            risk_score += 1
        if high_weight_exam_count >= 1:
            risk_score += 2
        if acceleration >= 50:
            risk_score += 2
        elif acceleration >= 25:
            risk_score += 1
        if compression_weight >= 30 and 0 <= compression_window <= 5:
            risk_score += 2

        if risk_score >= 6:
            risk_level = "High Risk"
        elif risk_score >= 3:
            risk_level = "Elevated"
        else:
            risk_level = "Normal"

        weekly_metrics[week_label] = {
            **raw,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "stress_acceleration_percent": round(acceleration, 1),
            "p70_stress": round(p70_stress, 1),
            "p85_stress": round(p85_stress, 1),
            "compression_weight_percent": round(compression_weight, 1),
            "compression_window_days": compression_window,
        }

    return weekly_metrics


def _peak_from_weekly_metrics(weekly_metrics: Dict[str, Dict[str, object]]) -> Tuple[str, float]:
    if not weekly_metrics:
        return "", 0.0
    peak_week = max(
        weekly_metrics.keys(),
        key=lambda week: float(weekly_metrics[week].get("weekly_stress_score") or 0.0),
    )
    return peak_week, float(weekly_metrics[peak_week].get("weekly_stress_score") or 0.0)


def _weeks_changed(
    before: Dict[str, Dict[str, object]],
    after: Dict[str, Dict[str, object]],
) -> List[str]:
    changed: List[str] = []
    all_weeks = sorted(set(before.keys()) | set(after.keys()), key=_week_label_sort_key)
    for week in all_weeks:
        before_stress = float(before.get(week, {}).get("weekly_stress_score") or 0.0)
        after_stress = float(after.get(week, {}).get("weekly_stress_score") or 0.0)
        if round(before_stress, 3) != round(after_stress, 3):
            changed.append(week)
    return changed


def _volatility_index(stress_values: List[float]) -> float:
    if not stress_values:
        return 0.0
    mean = sum(stress_values) / len(stress_values)
    variance = sum((value - mean) ** 2 for value in stress_values) / len(stress_values)
    return variance ** 0.5


def _derive_acceleration_and_compression_risk(
    weekly_metrics: Dict[str, Dict[str, object]],
    peak_week: str,
) -> Tuple[float, float]:
    if not weekly_metrics:
        return 0.0, 0.0

    acceleration_index = max(
        [float(week.get("stress_acceleration_percent") or 0.0) for week in weekly_metrics.values()] or [0.0]
    )

    peak_label = peak_week if peak_week and peak_week in weekly_metrics else ""
    if peak_week and peak_week not in weekly_metrics:
        logger.warning(
            "AI KPI calculation: peak_week '%s' not found in weekly_metrics; using highest-stress week fallback.",
            peak_week,
        )
    if not peak_label:
        peak_label = max(
            weekly_metrics.keys(),
            key=lambda week: float(weekly_metrics[week].get("weekly_stress_score") or 0.0),
        )
    peak_data = weekly_metrics.get(peak_label, {})
    compression_weight_percent = float(peak_data.get("compression_weight_percent") or 0.0)
    compression_window_days = float(peak_data.get("compression_window_days") or 0.0)

    # compression_risk is derived strictly from peak-week weekly_metrics values.
    raw_compression_risk = compression_weight_percent * max(0.0, compression_window_days)
    compression_risk = min(100.0, max(0.0, raw_compression_risk / 5.0))
    return round(acceleration_index, 1), round(compression_risk, 1)


def _derive_time_allocation_from_metrics(
    metrics: Optional[Dict[str, object]],
    summary_json: Dict[str, object],
) -> Dict[str, float]:
    total_exam_weight = 0.0
    project_weight = 0.0
    homework_weight = 0.0

    if isinstance(metrics, dict):
        study_guide = metrics.get("study_guide", {})
    else:
        study_guide = {}

    if isinstance(study_guide, dict):
        for info in study_guide.values():
            if not isinstance(info, dict):
                continue
            source = info.get("grading_categories")
            if not isinstance(source, dict) or not source:
                source = info.get("grading_breakdown")
            if not isinstance(source, dict):
                continue
            for label, weight in source.items():
                if not isinstance(weight, (int, float)):
                    continue
                label_lower = str(label).lower()
                weight_value = float(weight)
                if any(token in label_lower for token in ("exam", "midterm", "final", "quiz")):
                    total_exam_weight += weight_value
                elif any(
                    token in label_lower
                    for token in ("project", "capstone", "milestone", "submission", "paper", "presentation")
                ):
                    project_weight += weight_value
                elif any(
                    token in label_lower for token in ("homework", "assignment", "hw", "lab", "problem set")
                ):
                    homework_weight += weight_value

    compression_weight = float(summary_json.get("compression_weight_percent") or 0.0)
    compression_window = float(summary_json.get("compression_window_days") or 0.0)
    upcoming_exam_weight = float(summary_json.get("nearest_exam_weight") or 0.0)
    compression_present = compression_weight >= 30 and 0 <= compression_window <= 5

    exam_focus = total_exam_weight if total_exam_weight > 0 else max(20.0, upcoming_exam_weight)
    project_focus = project_weight if project_weight > 0 else 30.0
    homework_focus = homework_weight if homework_weight > 0 else 30.0

    # Base strategy on exam exposure across courses + compression + nearest upcoming exam.
    exam_focus += upcoming_exam_weight * 0.6
    if compression_present:
        exam_focus += 10.0
        project_focus += 4.0
        homework_focus -= 2.0

    if upcoming_exam_weight >= 30:
        exam_focus += 8.0
        homework_focus -= 6.0
    elif upcoming_exam_weight >= 20:
        exam_focus += 4.0
        homework_focus -= 3.0

    exam_focus = max(8.0, exam_focus)
    project_focus = max(8.0, project_focus)
    homework_focus = max(8.0, homework_focus)
    total = exam_focus + project_focus + homework_focus

    exam_pct = round(exam_focus * 100.0 / total, 1)
    project_pct = round(project_focus * 100.0 / total, 1)
    homework_pct = round(100.0 - exam_pct - project_pct, 1)
    return {
        "exam_prep": exam_pct,
        "projects": project_pct,
        "homework": homework_pct,
    }


def _select_simulation_candidate(simulation_results: Optional[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not isinstance(simulation_results, dict):
        return None

    shift_payload = simulation_results.get("shift")
    strategy_payload = simulation_results.get("strategy")
    active_scenario = str(simulation_results.get("active_scenario") or "").lower()

    candidates: List[Dict[str, object]] = []
    if isinstance(shift_payload, dict) and "error" not in shift_payload:
        candidates.append({"type": "shift", "payload": shift_payload})
    if isinstance(strategy_payload, dict) and "error" not in strategy_payload:
        candidates.append({"type": "strategy", "payload": strategy_payload})

    selected: Optional[Dict[str, object]] = None
    if active_scenario == "shift":
        selected = next((item for item in candidates if item["type"] == "shift"), None)
    elif active_scenario == "strategy":
        selected = next((item for item in candidates if item["type"] == "strategy"), None)
    if selected is None and candidates:
        selected = min(
            candidates,
            key=lambda item: float(item["payload"].get("peak_delta_percent") or item["payload"].get("delta_percent") or 0.0),
        )
    return selected


def _build_simulation_narrative(
    simulation_results: Optional[Dict[str, object]],
    simulation_impact: Dict[str, object],
) -> str:
    selected = _select_simulation_candidate(simulation_results)
    if selected is None:
        return (
            "Simulation peak change +0.0%; week shift=no (N/A->N/A); "
            "acceleration change 0.0%->0.0% (+0.0); compression change 0.0->0.0 (+0.0)."
        )

    payload = selected["payload"]
    before_metrics = payload.get("weekly_metrics_before", {})
    after_metrics = payload.get("weekly_metrics_after", {})
    if not isinstance(before_metrics, dict):
        before_metrics = {}
    if not isinstance(after_metrics, dict):
        after_metrics = {}

    peak_before = payload.get("peak_before", {})
    peak_after = payload.get("peak_after", {})
    peak_before_week = str(peak_before.get("week") or "") if isinstance(peak_before, dict) else ""
    peak_after_week = str(peak_after.get("week") or "") if isinstance(peak_after, dict) else ""

    acceleration_before, compression_before = _derive_acceleration_and_compression_risk(
        before_metrics,
        peak_before_week,
    )
    acceleration_after, compression_after = _derive_acceleration_and_compression_risk(
        after_metrics,
        peak_after_week,
    )
    acceleration_delta = acceleration_after - acceleration_before
    compression_delta = compression_after - compression_before

    peak_delta = float(simulation_impact.get("peak_delta_percent") or payload.get("peak_delta_percent") or 0.0)
    week_shift_detected = bool(
        payload.get("week_shift_detected")
        if payload.get("week_shift_detected") is not None
        else simulation_impact.get("week_shift_detected")
    )
    week_shift_text = "yes" if week_shift_detected else "no"

    return (
        f"Simulation peak change {peak_delta:+.1f}%; week shift={week_shift_text} "
        f"({peak_before_week or 'N/A'}->{peak_after_week or 'N/A'}); "
        f"acceleration change {acceleration_before:.1f}%->{acceleration_after:.1f}% ({acceleration_delta:+.1f}); "
        f"compression change {compression_before:.1f}->{compression_after:.1f} ({compression_delta:+.1f})."
    )


def _derive_simulation_impact(simulation_results: Optional[Dict[str, object]]) -> Dict[str, object]:
    if not isinstance(simulation_results, dict):
        return {
            "peak_delta_percent": 0.0,
            "week_shift_detected": False,
            "driver_task": "",
            "explanation": "No simulation scenario provided.",
        }
    selected = _select_simulation_candidate(simulation_results)

    if selected is None:
        return {
            "peak_delta_percent": 0.0,
            "week_shift_detected": False,
            "driver_task": "",
            "explanation": "Simulation did not produce a valid scenario output.",
        }

    payload = selected["payload"]
    delta = float(payload.get("peak_delta_percent") or payload.get("delta_percent") or 0.0)
    week_shift_detected = bool(payload.get("week_shift_detected") or False)
    driver_task = str(payload.get("task_title") or payload.get("task_selector") or "")
    if selected["type"] == "strategy" and not driver_task:
        driver_task = "allocation_strategy"

    if selected["type"] == "shift":
        from_week = payload.get("shifted_from_week")
        to_week = payload.get("shifted_to_week")
        if delta < 0:
            explanation = (
                f"Shifted '{driver_task}' from {from_week} to {to_week}, reducing peak stress by {abs(delta):.1f}%."
                if driver_task
                else f"Task shift simulation reduced peak stress by {abs(delta):.1f}%."
            )
        elif delta > 0:
            explanation = (
                f"Shifted '{driver_task}' from {from_week} to {to_week}, increasing peak stress by {delta:.1f}%."
                if driver_task
                else f"Task shift simulation increased peak stress by {delta:.1f}%."
            )
        else:
            explanation = (
                f"Shifted '{driver_task}' from {from_week} to {to_week} with no peak stress change."
                if driver_task
                else "Task shift simulation did not change peak stress."
            )
    else:
        if delta < 0:
            explanation = (
                f"Strategy simulation reduced peak stress by {abs(delta):.1f}% via allocation rebalancing."
            )
        elif delta > 0:
            explanation = (
                f"Strategy simulation increased peak stress by {delta:.1f}% with updated allocation multipliers."
            )
        else:
            explanation = "Strategy simulation did not change peak stress."

    return {
        "peak_delta_percent": round(delta, 1),
        "week_shift_detected": week_shift_detected,
        "driver_task": driver_task,
        "explanation": explanation,
    }


def _build_why_risky(
    summary_json: Dict[str, object],
    weekly_metrics: Dict[str, Dict[str, object]],
    kpis: Dict[str, float],
) -> Dict[str, object]:
    peak_week = str(summary_json.get("peak_week") or "")
    peak_metrics = weekly_metrics.get(peak_week, {}) if peak_week else {}
    peak_root_cause = summary_json.get("peak_root_cause", {})
    if not isinstance(peak_root_cause, dict):
        peak_root_cause = {}

    exam_count = int(
        peak_metrics.get("exam_count")
        if peak_metrics.get("exam_count") is not None
        else peak_root_cause.get("exam_count", 0)
    )
    milestone_count = int(
        peak_metrics.get("milestone_count")
        if peak_metrics.get("milestone_count") is not None
        else peak_root_cause.get("milestone_count", 0)
    )
    weekly_weight_sum = float(
        peak_metrics.get("weekly_weight_sum")
        if peak_metrics.get("weekly_weight_sum") is not None
        else peak_root_cause.get("weekly_weight_sum", 0.0)
    )
    compression_weight_percent = float(
        peak_metrics.get("compression_weight_percent")
        if peak_metrics.get("compression_weight_percent") is not None
        else peak_root_cause.get("compression_weight_percent", 0.0)
    )
    compression_window_days = int(
        peak_metrics.get("compression_window_days")
        if peak_metrics.get("compression_window_days") is not None
        else peak_root_cause.get("compression_window_days", 0)
    )
    stress_acceleration_percent = float(
        peak_metrics.get("stress_acceleration_percent")
        if peak_metrics.get("stress_acceleration_percent") is not None
        else peak_root_cause.get("stress_acceleration_percent", 0.0)
    )

    peak_label = peak_week or "N/A"
    explanation = (
        f"{peak_label} is high risk because exam_count={exam_count}, milestone_count={milestone_count}, "
        f"weekly_weight_sum={weekly_weight_sum:.1f}, compression window={compression_window_days} days "
        f"with compression_weight_percent={compression_weight_percent:.1f}%, and "
        f"stress_acceleration_percent={stress_acceleration_percent:.1f}%. "
        f"KPI context: peak_stress_score={kpis.get('peak_stress_score', 0.0):.1f}, "
        f"volatility_index={kpis.get('volatility_index', 0.0):.1f}, "
        f"risk_week_ratio={kpis.get('risk_week_ratio', 0.0):.2f}, "
        f"burnout_probability_percent={kpis.get('burnout_probability_percent', 0.0):.1f}, "
        f"peak_delta_percent={kpis.get('peak_delta_percent', 0.0):+.1f}."
    )

    return {
        "peak_week": peak_week,
        "exam_count": exam_count,
        "milestone_count": milestone_count,
        "weekly_weight_sum": round(weekly_weight_sum, 1),
        "compression_weight_percent": round(compression_weight_percent, 1),
        "compression_window_days": int(compression_window_days),
        "stress_acceleration_percent": round(stress_acceleration_percent, 1),
        "detail": explanation,
    }


def simulate_shift(
    metrics: Dict[str, object],
    task_id_or_title: object,
    shift_days: int,
) -> Dict[str, object]:
    import copy

    if not isinstance(metrics, dict):
        return {"error": "invalid_metrics"}
    weekly_plan = metrics.get("weekly_plan", {})
    if not isinstance(weekly_plan, dict) or not weekly_plan:
        return {"error": "no_weekly_plan"}

    before_plan = copy.deepcopy(weekly_plan)
    after_plan = copy.deepcopy(weekly_plan)

    flat: List[Tuple[str, int, Dict[str, object]]] = []
    for week_label in sorted(after_plan.keys(), key=_week_label_sort_key):
        tasks = after_plan.get(week_label, [])
        if not isinstance(tasks, list):
            continue
        for task_index, task in enumerate(tasks):
            if isinstance(task, dict):
                flat.append((week_label, task_index, task))

    selected: Optional[Tuple[str, int, Dict[str, object]]] = None
    if isinstance(task_id_or_title, int):
        if 0 <= task_id_or_title < len(flat):
            selected = flat[task_id_or_title]
    else:
        query = str(task_id_or_title or "").strip().lower()
        for candidate in flat:
            title = str(candidate[2].get("task") or "").strip().lower()
            if title == query:
                selected = candidate
                break
        if selected is None and query:
            for candidate in flat:
                title = str(candidate[2].get("task") or "").strip().lower()
                if query in title:
                    selected = candidate
                    break

    if selected is None:
        return {"error": "task_not_found"}

    original_week, original_index, _ = selected
    original_tasks = after_plan.get(original_week, [])
    if not isinstance(original_tasks, list) or not (0 <= original_index < len(original_tasks)):
        return {"error": "task_not_found"}

    task = original_tasks.pop(original_index)
    if not original_tasks:
        after_plan.pop(original_week, None)

    origin_week_index = _week_label_sort_key(original_week) or 1
    due_raw = task.get("due") or task.get("date")
    shifted_date: Optional[date] = None
    if isinstance(due_raw, str) and due_raw:
        parsed_due = _parse_date(due_raw, default_year=date.today().year)
        if isinstance(parsed_due, date):
            shifted_date = parsed_due + timedelta(days=int(shift_days))
            task["due"] = shifted_date.isoformat()
            task["date"] = shifted_date.isoformat()

    if shifted_date is not None:
        all_dates: List[date] = [shifted_date]
        for tasks in after_plan.values():
            if not isinstance(tasks, list):
                continue
            for candidate in tasks:
                if not isinstance(candidate, dict):
                    continue
                candidate_due = candidate.get("due") or candidate.get("date")
                if isinstance(candidate_due, str) and candidate_due:
                    parsed = _parse_date(candidate_due, default_year=date.today().year)
                    if isinstance(parsed, date):
                        all_dates.append(parsed)
        base_date = min(all_dates) if all_dates else shifted_date
        target_week_index = max(1, ((shifted_date - base_date).days // 7) + 1)
    else:
        week_delta = int(round(int(shift_days) / 7.0))
        if shift_days != 0 and week_delta == 0:
            week_delta = 1 if shift_days > 0 else -1
        target_week_index = max(1, origin_week_index + week_delta)

    target_week = f"Week {target_week_index}"
    after_plan.setdefault(target_week, []).append(task)
    week_shift_detected = original_week != target_week

    before_metrics = _recompute_weekly_metrics_from_weekly_plan(before_plan, default_year=date.today().year)
    after_metrics = _recompute_weekly_metrics_from_weekly_plan(after_plan, default_year=date.today().year)
    peak_before_week, peak_before_stress = _peak_from_weekly_metrics(before_metrics)
    peak_after_week, peak_after_stress = _peak_from_weekly_metrics(after_metrics)

    if peak_before_stress > 0:
        delta_percent = ((peak_after_stress - peak_before_stress) / peak_before_stress) * 100.0
    else:
        delta_percent = 0.0
    changed_weeks = _weeks_changed(before_metrics, after_metrics)
    week_shift_detected = peak_before_week != peak_after_week

    return {
        "task_selector": task_id_or_title,
        "task_title": task.get("task"),
        "shift_days": int(shift_days),
        "shifted_from_week": original_week,
        "shifted_to_week": target_week,
        "week_shift_detected": week_shift_detected,
        "peak_before": {"week": peak_before_week, "stress_score": round(peak_before_stress, 1)},
        "peak_after": {"week": peak_after_week, "stress_score": round(peak_after_stress, 1)},
        "peak_delta_percent": round(delta_percent, 1),
        "delta_percent": round(delta_percent, 1),
        "simulation_impact": {
            "peak_delta_percent": round(delta_percent, 1),
            "week_shift_detected": week_shift_detected,
            "driver_task": str(task.get("task") or ""),
            "explanation": (
                f"Moved '{task.get('task')}' from {original_week} to {target_week}, "
                f"changing peak stress by {delta_percent:.1f}%."
            ),
        },
        "weeks_changed": changed_weeks,
        "changed_week_count": len(changed_weeks),
        "weekly_metrics_before": before_metrics,
        "weekly_metrics_after": after_metrics,
    }


def strategy_simulation(
    metrics: Dict[str, object],
    target_split: Dict[str, float],
) -> Dict[str, object]:
    import copy

    if not isinstance(metrics, dict):
        return {"error": "invalid_metrics"}
    weekly_plan = metrics.get("weekly_plan", {})
    if not isinstance(weekly_plan, dict) or not weekly_plan:
        return {"error": "no_weekly_plan"}

    desired_exam = float(target_split.get("exam_prep", 0.0))
    desired_projects = float(target_split.get("projects", 0.0))
    desired_homework = float(target_split.get("homework", 0.0))
    total_desired = desired_exam + desired_projects + desired_homework
    if total_desired <= 0:
        desired_exam, desired_projects, desired_homework = 34.0, 33.0, 33.0
        total_desired = 100.0
    desired_exam = desired_exam * 100.0 / total_desired
    desired_projects = desired_projects * 100.0 / total_desired
    desired_homework = 100.0 - desired_exam - desired_projects

    adjusted_plan = copy.deepcopy(weekly_plan)

    def _bucket(task: Dict[str, object]) -> str:
        task_name = str(task.get("task") or "").lower()
        kind = str(task.get("kind") or "other")
        if task_name.startswith("prep for") or kind == "exam":
            return "exam_prep"
        if kind == "project":
            return "projects"
        return "homework"

    current_minutes = {"exam_prep": 0.0, "projects": 0.0, "homework": 0.0}
    for tasks in adjusted_plan.values():
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict):
                continue
            current_minutes[_bucket(task)] += float(task.get("estimated_minutes") or 0.0)

    current_total = sum(current_minutes.values()) or 1.0
    current_split = {
        "exam_prep": current_minutes["exam_prep"] * 100.0 / current_total,
        "projects": current_minutes["projects"] * 100.0 / current_total,
        "homework": current_minutes["homework"] * 100.0 / current_total,
    }
    target_values = {
        "exam_prep": desired_exam,
        "projects": desired_projects,
        "homework": desired_homework,
    }

    multipliers: Dict[str, float] = {}
    for key in ("exam_prep", "projects", "homework"):
        current_share = current_split[key]
        target_share = target_values[key]
        if current_share <= 0:
            multipliers[key] = 1.0
        else:
            multipliers[key] = max(0.65, min(1.5, target_share / current_share))

    for tasks in adjusted_plan.values():
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict):
                continue
            bucket = _bucket(task)
            minutes = float(task.get("estimated_minutes") or 0.0)
            adjusted_minutes = max(20.0, minutes * multipliers[bucket])
            task["estimated_minutes"] = int(round(adjusted_minutes))

    before_metrics = _recompute_weekly_metrics_from_weekly_plan(weekly_plan, default_year=date.today().year)
    after_metrics = _recompute_weekly_metrics_from_weekly_plan(adjusted_plan, default_year=date.today().year)
    peak_before_week, peak_before_stress = _peak_from_weekly_metrics(before_metrics)
    peak_after_week, peak_after_stress = _peak_from_weekly_metrics(after_metrics)

    if peak_before_stress > 0:
        delta_percent = ((peak_after_stress - peak_before_stress) / peak_before_stress) * 100.0
    else:
        delta_percent = 0.0
    changed_weeks = _weeks_changed(before_metrics, after_metrics)
    week_shift_detected = peak_before_week != peak_after_week

    return {
        "target_split": {
            "exam_prep": round(desired_exam, 1),
            "projects": round(desired_projects, 1),
            "homework": round(desired_homework, 1),
        },
        "current_split": {
            "exam_prep": round(current_split["exam_prep"], 1),
            "projects": round(current_split["projects"], 1),
            "homework": round(current_split["homework"], 1),
        },
        "peak_before": {"week": peak_before_week, "stress_score": round(peak_before_stress, 1)},
        "peak_after": {"week": peak_after_week, "stress_score": round(peak_after_stress, 1)},
        "peak_delta_percent": round(delta_percent, 1),
        "delta_percent": round(delta_percent, 1),
        "week_shift_detected": week_shift_detected,
        "simulation_impact": {
            "peak_delta_percent": round(delta_percent, 1),
            "week_shift_detected": week_shift_detected,
            "driver_task": "allocation_strategy",
            "explanation": (
                f"Adjusted allocation from exam/project/homework "
                f"{current_split['exam_prep']:.1f}/{current_split['projects']:.1f}/{current_split['homework']:.1f} "
                f"to {desired_exam:.1f}/{desired_projects:.1f}/{desired_homework:.1f}, "
                f"changing peak stress by {delta_percent:.1f}%."
            ),
        },
        "weeks_changed": changed_weeks,
        "changed_week_count": len(changed_weeks),
        "weekly_metrics_before": before_metrics,
        "weekly_metrics_after": after_metrics,
    }


def build_engine_summary(metrics: Dict[str, object]) -> Dict[str, object]:
    weekly_plan = metrics.get("weekly_plan", {}) if isinstance(metrics, dict) else {}
    study_guide = metrics.get("study_guide", {}) if isinstance(metrics, dict) else {}
    weekly_metrics = _aggregate_weekly_metrics(study_guide)

    task_count = 0
    if isinstance(weekly_plan, dict):
        for tasks in weekly_plan.values():
            if isinstance(tasks, list):
                task_count += len(tasks)

    stress_by_week = {
        week: float(data.get("weekly_stress_score") or 0.0)
        for week, data in weekly_metrics.items()
    }
    total_weeks = len(stress_by_week)
    if stress_by_week:
        peak_week = max(stress_by_week, key=stress_by_week.get)
        peak_stress_score = stress_by_week[peak_week]
    else:
        peak_week = ""
        peak_stress_score = 0.0

    high_pressure_weeks = sum(
        1
        for data in weekly_metrics.values()
        if str(data.get("risk_level") or "Normal") in {"Elevated", "High Risk", "Critical Risk"}
    )
    average_weekly_stress = sum(stress_by_week.values()) / total_weeks if total_weeks else 0.0
    volatility_index = _volatility_index(list(stress_by_week.values()))
    risk_week_ratio = (high_pressure_weeks / total_weeks) if total_weeks else 0.0

    compression_weight_percent = 0.0
    compression_window_days = 0
    for data in weekly_metrics.values():
        candidate_weight = float(data.get("compression_weight_percent") or 0.0)
        candidate_window = int(data.get("compression_window_days") or 0)
        if candidate_weight > compression_weight_percent or (
            candidate_weight == compression_weight_percent
            and candidate_weight > 0
            and (compression_window_days <= 0 or candidate_window < compression_window_days)
        ):
            compression_weight_percent = candidate_weight
            compression_window_days = candidate_window

    stress_acceleration_percent = max(
        [float(data.get("stress_acceleration_percent") or 0.0) for data in weekly_metrics.values()] or [0.0]
    )
    burnout_probability_percent = min(
        95.0,
        max(
            4.0,
            risk_week_ratio * 55.0
            + min(1.0, peak_stress_score / 700.0) * 26.0
            + min(1.0, stress_acceleration_percent / 120.0) * 19.0,
        ),
    )

    peak_root_cause = {
        "exam_count": 0,
        "milestone_count": 0,
        "weekly_weight_sum": 0.0,
        "compression_weight_percent": 0.0,
        "compression_window_days": 0,
        "stress_acceleration_percent": 0.0,
    }
    if peak_week and peak_week in weekly_metrics:
        peak_data = weekly_metrics[peak_week]
        peak_root_cause = {
            "exam_count": int(peak_data.get("exam_count") or 0),
            "milestone_count": int(peak_data.get("milestone_count") or 0),
            "weekly_weight_sum": round(float(peak_data.get("weekly_weight_sum") or 0.0), 1),
            "compression_weight_percent": round(float(peak_data.get("compression_weight_percent") or 0.0), 1),
            "compression_window_days": int(peak_data.get("compression_window_days") or 0),
            "stress_acceleration_percent": round(float(peak_data.get("stress_acceleration_percent") or 0.0), 1),
        }

    today = date.today()
    nearest_exam_weight = 0.0
    exam_dates: List[Tuple[date, float]] = []
    if isinstance(study_guide, dict):
        for info in study_guide.values():
            if not isinstance(info, dict):
                continue
            upcoming = info.get("upcoming_assessments", [])
            if not isinstance(upcoming, list):
                continue
            for assessment in upcoming:
                if not isinstance(assessment, dict):
                    continue
                if str(assessment.get("kind") or "").lower() != "exam":
                    continue
                weight = assessment.get("weight_percent")
                date_value = assessment.get("date")
                if not isinstance(weight, (int, float)) or not isinstance(date_value, str) or not date_value:
                    continue
                parsed = _parse_date(date_value, default_year=today.year)
                if isinstance(parsed, date):
                    exam_dates.append((parsed, float(weight)))
    if exam_dates:
        future = sorted([item for item in exam_dates if item[0] >= today], key=lambda item: item[0])
        if future:
            nearest_exam_weight = future[0][1]
        else:
            nearest_exam_weight = sorted(exam_dates, key=lambda item: item[0])[0][1]

    return {
        "peak_week": peak_week,
        "peak_stress_score": round(peak_stress_score, 1),
        "total_weeks": int(total_weeks),
        "high_pressure_weeks": int(high_pressure_weeks),
        "compression_weight_percent": round(compression_weight_percent, 1),
        "compression_window_days": int(compression_window_days),
        "nearest_exam_weight": round(nearest_exam_weight, 1),
        "average_weekly_stress": round(average_weekly_stress, 1),
        "volatility_index": round(volatility_index, 1),
        "risk_week_ratio": round(risk_week_ratio, 3),
        "burnout_probability_percent": round(burnout_probability_percent, 1),
        "stress_acceleration_percent": round(stress_acceleration_percent, 1),
        "task_count": int(task_count),
        "peak_root_cause": peak_root_cause,
    }


def _fallback_ai_intelligence(
    summary_json: Dict[str, object],
    metrics: Optional[Dict[str, object]] = None,
    simulation_results: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    def _num(key: str, default: float = 0.0) -> float:
        value = summary_json.get(key, default)
        return float(value) if isinstance(value, (int, float)) else default

    if isinstance(metrics, dict):
        weekly_metrics = _aggregate_weekly_metrics(metrics.get("study_guide", {}))
    else:
        weekly_metrics = {}
    total_weeks = max(1.0, _num("total_weeks", 1.0))
    high_pressure_weeks = _num("high_pressure_weeks", 0.0)
    peak_stress = _num("peak_stress_score", 0.0)
    volatility_index = _num("volatility_index", 0.0)
    risk_week_ratio = _num("risk_week_ratio", min(1.0, high_pressure_weeks / total_weeks))
    acceleration_index, compression_risk = _derive_acceleration_and_compression_risk(
        weekly_metrics,
        str(summary_json.get("peak_week") or ""),
    )
    burnout_probability = min(
        95.0,
        max(
            4.0,
            risk_week_ratio * 55.0
            + min(1.0, peak_stress / 700.0) * 26.0
            + min(1.0, acceleration_index / 120.0) * 19.0,
        ),
    )
    simulation_impact = _derive_simulation_impact(simulation_results)
    peak_delta_percent = round(float(simulation_impact.get("peak_delta_percent") or 0.0), 1)
    kpis = {
        "peak_stress_score": round(peak_stress, 1),
        "volatility_index": round(volatility_index, 1),
        "risk_week_ratio": round(risk_week_ratio, 3),
        "burnout_probability_percent": round(burnout_probability, 1),
        "acceleration_index": acceleration_index,
        "compression_risk": compression_risk,
        "peak_delta_percent": peak_delta_percent,
    }
    why_risky = _build_why_risky(summary_json, weekly_metrics, kpis)
    allocation = _derive_time_allocation_from_metrics(metrics, summary_json)
    simulation_narrative = _build_simulation_narrative(simulation_results, simulation_impact)

    return {
        "kpis": kpis,
        "why_risky": why_risky,
        "simulation_impact": simulation_impact,
        "simulation_narrative": simulation_narrative,
        "time_allocation_strategy": allocation,
    }


def call_ai_intelligence(
    summary_json: Dict[str, object],
    metrics: Optional[Dict[str, object]] = None,
    simulation_results: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """
    Single-request AI intelligence call with strict JSON schema enforcement.
    Falls back to deterministic insights when request/parsing/validation fails.
    """
    import json
    import os

    weekly_metrics = {}
    top_contributors: List[Dict[str, object]] = []
    if isinstance(metrics, dict):
        weekly_metrics = _aggregate_weekly_metrics(metrics.get("study_guide", {}))
        top_contributors = _top_contributors_from_metrics(metrics, limit=5)

    input_payload = {
        "engine_summary": summary_json,
        "weekly_metrics": weekly_metrics,
        "top_contributors": top_contributors,
        "simulation_results": simulation_results or {},
    }

    fallback = _fallback_ai_intelligence(
        summary_json,
        metrics=metrics,
        simulation_results=simulation_results,
    )
    simulation_impact_real = _derive_simulation_impact(simulation_results)

    prompt = (
        "SYSTEM: You are an academic workload AI intelligence module.\n"
        "Return strict JSON only. No markdown, no extra text.\n"
        "Use only the provided input payload.\n"
        "Return exactly this schema and keys:\n"
        "{\n"
        '  "kpis": {\n'
        '    "peak_stress_score": number,\n'
        '    "volatility_index": number,\n'
        '    "risk_week_ratio": number,\n'
        '    "burnout_probability_percent": number,\n'
        '    "acceleration_index": number,\n'
        '    "compression_risk": number,\n'
        '    "peak_delta_percent": number,\n'
        "  },\n"
        '  "why_risky": {\n'
        '    "peak_week": string,\n'
        '    "exam_count": number,\n'
        '    "milestone_count": number,\n'
        '    "weekly_weight_sum": number,\n'
        '    "compression_weight_percent": number,\n'
        '    "compression_window_days": number,\n'
        '    "stress_acceleration_percent": number,\n'
        '    "detail": string\n'
        "  },\n"
        '  "simulation_impact": {\n'
        '    "peak_delta_percent": number,\n'
        '    "week_shift_detected": boolean,\n'
        '    "driver_task": string,\n'
        '    "explanation": string\n'
        "  },\n"
        '  "simulation_narrative": string,\n'
        '  "time_allocation_strategy": {\n'
        '    "exam_prep": number,\n'
        '    "projects": number,\n'
        '    "homework": number\n'
        "  }\n"
        "}\n"
        "Hard constraints:\n"
        "- kpis.burnout_probability_percent must be between 0 and 100.\n"
        "- kpis.risk_week_ratio must be between 0 and 1.\n"
        "- kpis.compression_risk must be between 0 and 100.\n"
        "- kpis.acceleration_index must equal max(stress_acceleration_percent across weekly_metrics).\n"
        "- kpis.compression_risk must be computed from peak_week weekly_metrics as compression_weight_percent * compression_window_days, normalized to 0-100 and capped at 100.\n"
        "- kpis.peak_delta_percent must equal baseline vs selected simulation scenario peak change.\n"
        "- time_allocation_strategy must sum to 100.\n"
        "- why_risky.detail must explicitly mention compression window, acceleration %, and exam count with numeric values.\n"
        "- why_risky.detail must explicitly reference peak_stress_score, volatility_index, risk_week_ratio, burnout_probability_percent, peak_delta_percent.\n"
        "- simulation_impact.explanation must state if peak stress is reduced or increased and what caused it.\n"
        "- simulation_narrative must reference peak change, week shift, acceleration change, compression change.\n"
        "Input payload JSON:\n"
        f"{json.dumps(input_payload)}"
    )

    def _extract_response_text(response: object) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            direct = response.get("generated_text")
            if isinstance(direct, str):
                return direct
            results = response.get("results")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    for key in ("generated_text", "output_text", "text"):
                        value = first.get(key)
                        if isinstance(value, str):
                            return value
        return ""

    def _parse_json_object(text: str) -> Optional[Dict[str, object]]:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                return None
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None

    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float))

    def _validate(payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        if set(payload.keys()) != {"kpis", "why_risky", "simulation_impact", "simulation_narrative", "time_allocation_strategy"}:
            return False

        kpis = payload.get("kpis")
        if not isinstance(kpis, dict):
            return False
        if set(kpis.keys()) != {
            "peak_stress_score",
            "volatility_index",
            "risk_week_ratio",
            "burnout_probability_percent",
            "acceleration_index",
            "compression_risk",
            "peak_delta_percent",
        }:
            return False
        if not all(_is_number(kpis.get(key)) for key in kpis.keys()):
            return False
        if not 0.0 <= float(kpis["burnout_probability_percent"]) <= 100.0:
            return False
        if not 0.0 <= float(kpis["risk_week_ratio"]) <= 1.0:
            return False
        if not 0.0 <= float(kpis["compression_risk"]) <= 100.0:
            return False

        why_risky = payload.get("why_risky")
        if not isinstance(why_risky, dict):
            return False
        if set(why_risky.keys()) != {
            "peak_week",
            "exam_count",
            "milestone_count",
            "weekly_weight_sum",
            "compression_weight_percent",
            "compression_window_days",
            "stress_acceleration_percent",
            "detail",
        }:
            return False
        if not isinstance(why_risky["peak_week"], str):
            return False
        if not all(_is_number(why_risky[key]) for key in (
            "exam_count",
            "milestone_count",
            "weekly_weight_sum",
            "compression_weight_percent",
            "compression_window_days",
            "stress_acceleration_percent",
        )):
            return False
        if not isinstance(why_risky["detail"], str) or not why_risky["detail"].strip():
            return False
        detail_lower = why_risky["detail"].lower()
        required_tokens = (
            "peak_stress_score",
            "volatility_index",
            "risk_week_ratio",
            "burnout_probability_percent",
            "peak_delta_percent",
        )
        if not all(token in detail_lower for token in required_tokens):
            return False
        required_risk_tokens = ("compression window", "acceleration", "exam")
        if not all(token in detail_lower for token in required_risk_tokens):
            return False

        simulation_impact = payload.get("simulation_impact")
        if not isinstance(simulation_impact, dict):
            return False
        if set(simulation_impact.keys()) != {
            "peak_delta_percent",
            "week_shift_detected",
            "driver_task",
            "explanation",
        }:
            return False
        if not _is_number(simulation_impact.get("peak_delta_percent")):
            return False
        if not isinstance(simulation_impact.get("week_shift_detected"), bool):
            return False
        if not isinstance(simulation_impact.get("driver_task"), str):
            return False
        if not isinstance(simulation_impact.get("explanation"), str):
            return False

        narrative = payload.get("simulation_narrative")
        if not isinstance(narrative, str):
            return False
        narrative_lower = narrative.lower()
        if not all(token in narrative_lower for token in ("peak change", "week shift", "acceleration change", "compression change")):
            return False

        allocation = payload.get("time_allocation_strategy")
        if not isinstance(allocation, dict):
            return False
        if set(allocation.keys()) != {"exam_prep", "projects", "homework"}:
            return False
        if not all(_is_number(allocation.get(key)) for key in allocation.keys()):
            return False
        alloc_sum = float(allocation["exam_prep"]) + float(allocation["projects"]) + float(allocation["homework"])
        if abs(alloc_sum - 100.0) > 1.5:
            return False
        return True

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            api_key=os.environ["WATSONX_API_KEY"],
            url=os.environ["WATSONX_URL"],
        )
        model = ModelInference(
            model_id="ibm/granite-4-h-small",
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
        )
        response = model.generate(
            prompt=prompt,
            params={"max_new_tokens": 550, "temperature": 0.1},
        )
        response_text = _extract_response_text(response)
    except Exception:
        return fallback

    parsed = _parse_json_object(response_text)
    if not _validate(parsed):
        return fallback

    assert isinstance(parsed, dict)
    parsed_kpis = parsed.get("kpis")
    if isinstance(parsed_kpis, dict):
        acceleration_index, compression_risk = _derive_acceleration_and_compression_risk(
            weekly_metrics,
            str(summary_json.get("peak_week") or ""),
        )
        parsed_kpis["acceleration_index"] = acceleration_index
        parsed_kpis["compression_risk"] = compression_risk
        parsed_kpis["peak_delta_percent"] = round(float(simulation_impact_real.get("peak_delta_percent") or 0.0), 1)
        parsed["kpis"] = parsed_kpis

    parsed["simulation_narrative"] = _build_simulation_narrative(simulation_results, simulation_impact_real)

    allocation = parsed.get("time_allocation_strategy")
    if isinstance(allocation, dict):
        exam = float(allocation.get("exam_prep") or 0.0)
        projects = float(allocation.get("projects") or 0.0)
        homework = float(allocation.get("homework") or 0.0)
        total = exam + projects + homework
        if total > 0:
            exam = round(exam * 100.0 / total, 1)
            projects = round(projects * 100.0 / total, 1)
            homework = round(100.0 - exam - projects, 1)
            parsed["time_allocation_strategy"] = {
                "exam_prep": exam,
                "projects": projects,
                "homework": homework,
            }

    return parsed


def call_ibm_ai(
    deterministic_result: Dict[str, object],
    anchor_date: date,
) -> Dict[str, object]:
    """
    Build a strict JSON prompt and call IBM WatsonX/Granite model for insights only.
    The deterministic_result remains the source of truth for schedules/weights.
    """
    import json
    import os

    prompt_payload = {
        "weekly_plan": deterministic_result.get("weekly_plan", {}),
        "study_guide": deterministic_result.get("study_guide", {}),
        "anchor_date": anchor_date.isoformat(),
    }
    prompt = (
        "SYSTEM: You are an academic workload strategist.\n"
        "Your role is to detect workload patterns, risk clusters, and strategic adjustments.\n"
        "Analyze the input JSON and return JSON only.\n"
        "Detect deadline clustering.\n"
        "Identify high-weight compression.\n"
        "Suggest pre-loading or redistribution strategy.\n"
        "Recommendations must be actionable, not generic.\n"
        "Use quantified reasoning when possible (mention week labels and/or weights).\n"
        "Do not restate the input.\n"
        "Do not fabricate new deadlines or weights.\n"
        "Do not modify weights, priority, due dates, or weekly grouping.\n"
        "Return strictly this schema:\n"
        "{\n"
        '  "ai_insights": {\n'
        '    "global_analysis": [string],\n'
        '    "course_strategies": {\n'
        '      "<course_name>": {\n'
        '        "risk_commentary": [string],\n'
        '        "study_strategy": [string],\n'
        '        "time_allocation_suggestion": {\n'
        '          "suggested_hours_per_week": number,\n'
        '          "focus_split_percent": {\n'
        '            "exam_prep": number,\n'
        '            "projects": number,\n'
        '            "homework": number\n'
        "          }\n"
        "        }\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
        "Input JSON:\n"
        f"{json.dumps(prompt_payload)}"
    )

    def _extract_response_text(response: object) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            direct_text = response.get("generated_text")
            if isinstance(direct_text, str):
                return direct_text

            results = response.get("results")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    for key in ("generated_text", "output_text", "text"):
                        value = first.get(key)
                        if isinstance(value, str):
                            return value

            choices = response.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    text = first_choice.get("text")
                    if isinstance(text, str):
                        return text

        return ""

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            api_key=os.environ["WATSONX_API_KEY"],
            url=os.environ["WATSONX_URL"],
        )
        model = ModelInference(
            model_id="ibm/granite-4-h-small",
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
        )
        response = model.generate(
            prompt=prompt,
            params={
                "max_new_tokens": 1200,
                "temperature": 0.2,
            },
        )
        response_text = _extract_response_text(response)
    except Exception:
        return deterministic_result

    def _parse_model_output(text: str) -> Optional[Dict[str, object]]:
        if not text:
            return None
        cleaned_text = text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass

        # Try to extract a JSON object from a larger response.
        match = re.search(r"\{.*\}", cleaned_text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _is_string_list(value: object) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float))

    def _is_valid_ai_output(payload: object) -> bool:
        if not isinstance(payload, dict) or set(payload.keys()) != {"ai_insights"}:
            return False
        ai_insights = payload.get("ai_insights")
        if not isinstance(ai_insights, dict):
            return False
        if set(ai_insights.keys()) != {"global_analysis", "course_strategies"}:
            return False
        if not _is_string_list(ai_insights.get("global_analysis")):
            return False

        course_strategies = ai_insights.get("course_strategies")
        if not isinstance(course_strategies, dict):
            return False

        for course_name, strategy in course_strategies.items():
            if not isinstance(course_name, str) or not isinstance(strategy, dict):
                return False
            if set(strategy.keys()) != {
                "risk_commentary",
                "study_strategy",
                "time_allocation_suggestion",
            }:
                return False
            if not _is_string_list(strategy.get("risk_commentary")):
                return False
            if not _is_string_list(strategy.get("study_strategy")):
                return False

            allocation = strategy.get("time_allocation_suggestion")
            if not isinstance(allocation, dict):
                return False
            if set(allocation.keys()) != {"suggested_hours_per_week", "focus_split_percent"}:
                return False
            if not _is_number(allocation.get("suggested_hours_per_week")):
                return False

            split = allocation.get("focus_split_percent")
            if not isinstance(split, dict):
                return False
            if set(split.keys()) != {"exam_prep", "projects", "homework"}:
                return False
            if not all(_is_number(split.get(key)) for key in ("exam_prep", "projects", "homework")):
                return False

        return True

    parsed = _parse_model_output(response_text)
    if not _is_valid_ai_output(parsed):
        return deterministic_result

    return {**deterministic_result, **parsed}


def build_ibm_prompt(
    parsed_syllabi: List[Dict[str, object]],
    weekly_plan_draft: Dict[str, List[str]],
) -> str:
    """
    Convert parsed_syllabi and weekly_plan_draft into a clear text prompt
    for IBM WatsonX/Granite.

    The prompt should include:
    - Summaries of each course with assessments, dates, and weights
    - Weekly plan draft with tasks
    - Instructions for the model to:
      * Prioritize tasks
      * Suggest refined weekly tasks
      * Provide reasons and tactical advice

    Return: string prompt

    Example prompt skeleton:
    \"\"\"
    You are an academic planning assistant. Use the syllabus summaries and draft plan
    to produce a refined weekly plan with priorities, reasons, and tactical advice.

    Courses:
    - COURSE: CSE 2331
      Assessments:
      - Midterm 1 | kind=exam | date=March 5 | weight=25%
      - Homework | kind=homework | date=None | weight=20%

    Draft weekly plan:
    Week 1:
    - CSE 2331: Homework assignments weekly
    Week 2:
    - CSE 2331: Prep for Midterm 1

    Instructions:
    1) Prioritize tasks by weight and deadline proximity.
    2) Suggest refined weekly tasks and remove duplicates.
    3) Provide reasons and tactical advice per course.
    \"\"\"
    """
    courses: Dict[str, List[Dict[str, object]]] = {}
    for item in parsed_syllabi:
        course_name = item.get("course") or "Unknown Course"
        courses.setdefault(course_name, []).append(item)

    lines: List[str] = []
    lines.append(
        "You are an academic planning assistant. Use the syllabus summaries and draft plan "
        "to produce a refined weekly plan with priorities, reasons, and tactical advice."
    )
    lines.append("")
    lines.append("Courses:")
    for course_name, items in courses.items():
        lines.append(f"- COURSE: {course_name}")
        lines.append("  Assessments:")
        for item in items:
            title = item.get("title") or "Untitled"
            kind = item.get("kind") or "other"
            date_str = item.get("date")
            weight = item.get("weight_percent")
            weight_str = f"{weight}%" if isinstance(weight, (int, float)) else "None"
            date_out = date_str if date_str else "None"
            lines.append(f"  - {title} | kind={kind} | date={date_out} | weight={weight_str}")
        lines.append("")

    lines.append("Draft weekly plan:")
    for week_label, tasks in weekly_plan_draft.items():
        lines.append(f"{week_label}:")
        for task in tasks:
            lines.append(f"- {task}")
        lines.append("")

    lines.append("Instructions:")
    lines.append("1) Prioritize tasks by weight and deadline proximity.")
    lines.append("2) Suggest refined weekly tasks and remove duplicates.")
    lines.append("3) Provide reasons and tactical advice per course.")

    return "\n".join(lines)


def generate_plan_with_ai(
    parsed_syllabi: List[Dict[str, object]],
    weekly_plan: Dict[str, List[str]],
    anchor_date: Optional[date] = None,
) -> Dict[str, Dict[str, object]]:
    if anchor_date is None:
        raise ValueError("anchor_date required")

    deterministic_result = deterministic_ai_refinement(
        parsed_syllabi,
        weekly_plan,
        anchor_date=anchor_date,
    )

    if USE_REAL_AI:
        result = call_ibm_ai(deterministic_result, anchor_date=anchor_date)
    else:
        result = deterministic_result

    study_guide = result.get("study_guide", {})
    for course in parsed_syllabi:
        grading_categories = course.get("grading_categories")

        if grading_categories and course["course_name"] in study_guide:
            study_guide[course["course_name"]]["grading_breakdown"] = dict(grading_categories)
            study_guide[course["course_name"]]["total_weight_detected"] = sum(grading_categories.values())

    return result
