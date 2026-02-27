from __future__ import annotations

import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


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
        for week_label, tasks in course_weeks.items():
            exam_count = 0
            milestone_count = 0
            weighted_exam_count = 0
            high_weight_exam_count = 0
            weekly_minutes_sum = 0
            weekly_weight_sum = 0.0
            for task in tasks:
                task_name = str(task.get("task", "")).lower()
                if task.get("kind") == "exam" and not task_name.startswith("prep for"):
                    exam_count += 1
                    if float(task.get("weight_percent") or 0.0) >= 20:
                        weighted_exam_count += 1
                    if float(task.get("weight_percent") or 0.0) >= 25:
                        high_weight_exam_count += 1
                if task.get("kind") == "project" and any(
                    token in task_name for token in ("milestone", "submission")
                ):
                    milestone_count += 1
                weekly_minutes_sum += int(task.get("estimated_minutes") or 0)
                weekly_weight_sum += float(task.get("weight_effective") or 0.0)
            task_count = len(tasks)
            high_risk_flag = (
                weekly_weight_sum > 30
                or exam_count >= 2
                or high_weight_exam_count >= 1
            )
            if weekly_minutes_sum > 600:
                risk_level = "Critical Risk"
            elif weekly_minutes_sum > 400 or high_risk_flag:
                risk_level = "High Risk"
            else:
                risk_level = "Normal"

            weekly_metrics[week_label] = {
                "weekly_weight_sum": weekly_weight_sum,
                "weekly_stress_score": weekly_minutes_sum,
                "risk_level": risk_level,
                "task_count": task_count,
                "exam_count": exam_count,
                "milestone_count": milestone_count,
                "high_weight_exam_count": high_weight_exam_count,
            }

            if weighted_exam_count >= 2:
                warnings.append(f"Assessment collision detected in {week_label}.")

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
            if week_risk_level in {"High Risk", "Critical Risk"}:
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
