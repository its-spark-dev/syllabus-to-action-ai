import re
from typing import Dict, List, Optional, Tuple


HOMEWORK_KEYWORDS = (
    "assignment",
    "homework",
    "hw",
    "lab",
    "problem set",
    "pset",
    "worksheet",
)

PROJECT_KEYWORDS = (
    "project",
    "paper",
    "essay",
    "report",
    "presentation",
    "capstone",
    "memo",
)

EXAM_STRONG_KEYWORDS = (
    "exam",
    "test",
    "quiz",
)

EXAM_SECONDARY_KEYWORDS = (
    "midterm",
    "final",
)

PARTICIPATION_KEYWORDS = (
    "participation",
    "attendance",
)

ASSESSMENT_KEYWORDS = (
    *HOMEWORK_KEYWORDS,
    *PROJECT_KEYWORDS,
    *EXAM_STRONG_KEYWORDS,
    *EXAM_SECONDARY_KEYWORDS,
    *PARTICIPATION_KEYWORDS,
)

DATE_PATTERNS = [
    # Month name dates like "March 5" or "Mar 5"
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b",
    # Numeric dates like "03/05" or "03/05/2026"
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    # ISO dates like "2026-03-05"
    r"\b\d{4}-\d{2}-\d{2}\b",
]

COURSE_CODE_PATTERN = re.compile(r"\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b")
# Weight extraction uses percentage forms like "25%" or "25.5%".
WEIGHT_EXTRACT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# Grading breakdown lines like "Homework - 20% (weekly)".
GRADING_CATEGORY_PATTERN = re.compile(
    r"^(?P<label>.+?)\s*[:\-]\s*(?P<percent>\d+(?:\.\d+)?)\s*%(?:\s*\([^)]*\))?\s*$",
    flags=re.IGNORECASE,
)


def normalize_syllabus_text(text: str) -> str:
    normalized_lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.replace("–", "-").replace("—", "-")
        line = re.sub(r"(\d+(?:\.\d+)?)\s+%", r"\1%", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        normalized_lines.append(line)
    return "\n".join(normalized_lines)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_dates(text: str) -> List[str]:
    dates = []
    for pattern in DATE_PATTERNS:
        dates.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return dates


def _extract_first_date(text: str) -> Optional[str]:
    matches: List[Tuple[int, str]] = []
    for pattern in DATE_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            matches.append((match.start(), match.group(0)))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def _extract_course(text: str) -> Optional[str]:
    return get_course_name(text.splitlines())


def get_course_name(lines: List[str]) -> Optional[str]:
    for line in lines:
        line_clean = _normalize(line)
        if not line_clean:
            continue
        header_match = re.match(r"^course\s*:\s*(.+)$", line_clean, flags=re.IGNORECASE)
        if header_match:
            course_value = _normalize(header_match.group(1))
            if course_value:
                return course_value
            continue
        lowered = line_clean.lower()
        has_assessment = any(
            keyword in lowered for keyword in ("midterm", "final", "quiz", "project")
        )
        has_date = _extract_first_date(line_clean) is not None
        if has_assessment or has_date:
            return "Unnamed Course"
        return line_clean
    return None


def _extract_weight(text: str) -> Optional[float]:
    match = WEIGHT_EXTRACT_PATTERN.search(text)
    if match:
        return float(match.group(1))
    return None


def _extract_grading_category(text: str) -> Optional[Tuple[str, float]]:
    match = GRADING_CATEGORY_PATTERN.match(text)
    if not match:
        return None
    label = re.sub(r"\s*\([^)]*\)", "", match.group("label"))
    label = _normalize(label)
    if not label:
        return None
    return label, float(match.group("percent"))


def _classify_kind(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in EXAM_STRONG_KEYWORDS):
        return "exam"
    if any(keyword in lowered for keyword in EXAM_SECONDARY_KEYWORDS):
        return "exam"
    if "quiz" in lowered:
        return "quiz"
    if any(keyword in lowered for keyword in PROJECT_KEYWORDS):
        return "project"
    if any(keyword in lowered for keyword in HOMEWORK_KEYWORDS):
        return "homework"
    if any(keyword in lowered for keyword in PARTICIPATION_KEYWORDS):
        return "participation"
    return "other"


def _has_assessment_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ASSESSMENT_KEYWORDS)


def _title_from_line(text: str) -> str:
    cleaned = WEIGHT_EXTRACT_PATTERN.sub("", text)
    cleaned = re.sub(r"\b(?:worth|accounts\s+for|accounting\s+for)\b", "", cleaned, flags=re.IGNORECASE)
    for pattern in DATE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(due|due on)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[()]+", "", cleaned)
    if ":" in cleaned:
        cleaned = cleaned.split(":", 1)[0]
    cleaned = re.sub(r"\s*[-|]\s*$", "", cleaned)
    cleaned = re.sub(r"[-\s]+$", "", cleaned)
    return _normalize(cleaned)


def parse_syllabi(syllabi_texts: List[str]) -> List[Dict[str, object]]:
    """
    Parse multiple syllabus texts into structured assessment items.

    Returns a list of dicts shaped like:
    [
        {
            "course": "CSE 2331",
            "title": "Midterm 1",
            "kind": "exam",
            "date": "March 5",
            "weight_percent": 25.0,
        },
        ...
    ]
    """
    results: List[Dict[str, object]] = []

    for course_index, syllabus_text in enumerate(syllabi_texts, start=1):
        if not syllabus_text:
            continue
        syllabus_text = normalize_syllabus_text(syllabus_text)

        course_id = f"course_{course_index}"
        course = _extract_course(syllabus_text) or "Unknown Course"
        in_grading_breakdown = False
        grading_categories: Dict[str, float] = {}

        for line in syllabus_text.splitlines():
            line_clean = _normalize(line)
            if not line_clean:
                in_grading_breakdown = False
                continue
            lowered = line_clean.lower()
            if lowered.startswith("instructor:"):
                continue
            if lowered.startswith("office hours:"):
                continue
            if lowered.startswith("location:"):
                continue
            if lowered.startswith("course description:"):
                continue
            if lowered.startswith("important notes:"):
                continue
            if any(phrase in lowered for phrase in ("covers", "late homework", "must be completed", "per day")):
                continue

            if lowered.strip().startswith("grading breakdown"):
                in_grading_breakdown = True
                continue

            date = _extract_first_date(line_clean)
            weight = _extract_weight(line_clean)
            has_keyword = _has_assessment_keyword(line_clean)

            # Capture grading breakdown categories without creating tasks.
            if in_grading_breakdown and not date:
                category = _extract_grading_category(line_clean)
                if category:
                    label, percent = category
                    grading_categories[label] = percent
                    continue
            if (
                weight is not None
                and not date
                and any(token in lowered for token in ("total", "breakdown", "grading"))
            ):
                continue

            # Only create tasks with a date, or weight + assessment keyword.
            if date or (weight is not None and has_keyword):
                title = _title_from_line(line_clean) or line_clean
                task = {
                    "course_id": course_id,
                    "course": course,
                    "title": title,
                    "kind": _classify_kind(title),
                    "date": date,
                    "weight_percent": weight,
                }
                results.append(task)
        _append_grading_categories(results, course_id, course, grading_categories)

    return results


# Append grading breakdown categories as a special meta record per course.
def _append_grading_categories(
    results: List[Dict[str, object]],
    course_id: str,
    course: str,
    categories: Dict[str, float],
) -> None:
    if not categories:
        return
    results.append(
        {
            "course_id": course_id,
            "course": course,
            "title": "__GRADING_CATEGORIES__",
            "kind": "meta",
            "date": None,
            "weight_percent": None,
            "categories": categories,
        }
    )


# Example: parse_syllabi(["CSE 2331\nMidterm 1: March 5 (25%)"])
# -> [{'course': 'CSE 2331', 'title': 'Midterm 1', 'kind': 'exam', 'date': 'March 5', 'weight_percent': 25.0}]
# Example: parse_syllabi(["BIO 101\nFinal Exam: April 30 (30%)"])
# -> [{'course': 'BIO 101', 'title': 'Final Exam', 'kind': 'exam', 'date': 'April 30', 'weight_percent': 30.0}]
# Example: parse_syllabi(["MATH 200\nHomework assignments weekly (20%)"])
# -> [{'course': 'MATH 200', 'title': 'Homework assignments weekly', 'kind': 'homework', 'date': None, 'weight_percent': 20.0}]
# Example: parse_syllabi(["STAT 300\nGrading: Homework 20%, Quizzes 10%, Project 30%, Final 40%"])
# -> [{'course': 'STAT 300', 'title': 'Homework', 'kind': 'homework', 'date': None, 'weight_percent': 20.0}, ...]
# Example: parse_syllabi(["CSE 101\nProject proposal due April 12"])
# -> [{'course': 'CSE 101', 'title': 'Project proposal due', 'kind': 'project', 'date': 'April 12', 'weight_percent': None}]
# Example: parse_syllabi(["ENG 210\nMidterm exam in class"])
# -> [{'course': 'ENG 210', 'title': 'Midterm exam in class', 'kind': 'exam', 'date': None, 'weight_percent': None}]
