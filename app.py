import streamlit as st

from datetime import date, datetime

import ai.engine as ai_engine
from ai.engine import generate_plan_with_ai
from parser.syllabus_parser import parse_syllabi
from planner.weekly_planner import generate_weekly_plan


def render_header():
    st.title("Syllabus-to-Action AI")
    st.write("AI-powered weekly to-do & study guide generator")


def render_syllabus_inputs():
    st.subheader("Course Syllabi")

    def set_sample_syllabi():
        st.session_state["course_count"] = 2
        st.session_state["syllabus_0"] = (
            "CSE 2331 – Data Structures (Spring 2026)\n"
            "Instructor: Dr. Alana Ruiz\n"
            "Location: Dreese Lab 101\n"
            "Course Description: This course covers algorithmic techniques, data structures,\n"
            "and performance analysis. Late policy: 10% per day, max 3 days.\n"
            "\n"
            "Grading Breakdown\n"
            "Homework: 25%\n"
            "Quizzes: 10%\n"
            "Midterm: 20%\n"
            "Project: 25%\n"
            "Final Exam: 20%\n"
            "\n"
            "Homework 1: Arrays and Big-O — due January 19\n"
            "Homework 2: Stacks & Queues — due January 26\n"
            "Homework 3: Trees — due February 2\n"
            "Homework 4: Hash Tables — due February 9\n"
            "Homework 5: Graphs — due February 23\n"
            "\n"
            "Quiz 1: February 5\n"
            "Quiz 2: March 5\n"
            "Midterm Exam: February 19 (20%)\n"
            "\n"
            "Project Milestone 1: Proposal — due February 12 (5%)\n"
            "Project Milestone 2: Prototype — due March 12 (10%)\n"
            "Project Submission — due April 2 (10%)\n"
            "\n"
            "Final Exam: April 29 (20%)"
        )
        st.session_state["syllabus_1"] = (
            "ECON 1011 – Principles of Microeconomics (Spring 2026)\n"
            "Instructor: Dr. Michael Huang\n"
            "Location: Thompson Hall 210\n"
            "Course Description: Introduces supply and demand, consumer choice,\n"
            "and market structures. Office Hours: Tue 2-4pm.\n"
            "\n"
            "Grading Breakdown\n"
            "Homework: 20%\n"
            "Quizzes: 10%\n"
            "Midterm: 25%\n"
            "Project: 15%\n"
            "Final Exam: 30%\n"
            "\n"
            "Homework 1: Demand Analysis — due January 21\n"
            "Homework 2: Elasticity — due February 4\n"
            "Homework 3: Consumer Choice — due February 18\n"
            "Homework 4: Costs — due March 4\n"
            "\n"
            "Quiz 1: February 6\n"
            "Quiz 2: March 6\n"
            "Midterm Exam: March 11 (25%)\n"
            "\n"
            "Project Milestone 1: Topic Proposal — due February 20 (5%)\n"
            "Project Milestone 2: Draft Report — due March 27 (5%)\n"
            "Project Submission — due April 17 (5%)\n"
            "\n"
            "Final Exam: May 2 (30%)"
        )

    st.button("Sample syllabus", on_click=set_sample_syllabi)

    course_count = st.number_input(
        "Number of courses",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
        key="course_count",
    )

    syllabus_inputs = []
    for index in range(int(course_count)):
        syllabus_inputs.append(
            st.text_area(
                f"Course {index + 1} syllabus",
                placeholder="Paste syllabus here...",
                key=f"syllabus_{index}",
                height=180,
            )
        )

    return syllabus_inputs


def render_generate_button():
    return st.button("Generate Plan")


def render_outputs():
    st.subheader("Weekly To-Do Lists")
    weekly_todo_placeholder = st.empty()

    st.subheader("Study Guide")
    study_guide_placeholder = st.empty()

    return weekly_todo_placeholder, study_guide_placeholder


def _week_sort_key(week_label: str) -> int:
    parts = week_label.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


def _parse_due_date(date_str):
    if not date_str:
        return None
    formats = (
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d",
        "%B %d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%m/%d",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt).date()
            if "%Y" not in fmt:
                return parsed.replace(year=date.today().year)
            return parsed
        except ValueError:
            continue
    return None


def _priority_rank(priority: str) -> int:
    if priority == "High":
        return 0
    if priority == "Med":
        return 1
    return 2


def render_summary(weekly_plan, study_guide):
    st.subheader("Summary")

    all_tasks = []
    for tasks in weekly_plan.values():
        for task in tasks:
            due_date = _parse_due_date(task.get("due"))
            all_tasks.append(
                {
                    "task": task,
                    "priority_rank": _priority_rank(task.get("priority", "Low")),
                    "due_date": due_date or date.max,
                }
            )

    all_tasks.sort(key=lambda item: (item["priority_rank"], item["due_date"]))
    focus_tasks = [item["task"] for item in all_tasks[:3]]

    st.write("This week’s focus:")
    if focus_tasks:
        for task in focus_tasks:
            st.write(
                f"{task.get('course', '')}: {task.get('task', '')} "
                f"({task.get('priority', 'Low')})"
            )
    else:
        st.write("No tasks generated yet.")

    upcoming = []
    for course, info in study_guide.items():
        for item in info.get("upcoming_assessments", []):
            due_date = _parse_due_date(item.get("date"))
            weight = item.get("weight_percent") or 0
            upcoming.append(
                {
                    "course": course,
                    "title": item.get("title"),
                    "date": item.get("date"),
                    "weight": weight,
                    "due_date": due_date or date.max,
                }
            )

    upcoming.sort(key=lambda item: (-item["weight"], item["due_date"]))
    high_stakes = upcoming[:3]
    st.write("High-stakes assessments coming up:")
    if high_stakes:
        for item in high_stakes:
            st.write(
                f"{item.get('course', '')}: {item.get('title', '')} "
                f"({item.get('weight', 0)}%, {item.get('date', '')})"
            )
    else:
        st.write("No upcoming assessments detected.")


def render_weekly_plan(placeholder, weekly_plan):
    with placeholder.container():
        if not weekly_plan:
            return

        for week_label in sorted(weekly_plan.keys(), key=_week_sort_key):
            st.subheader(week_label)
            tasks = weekly_plan[week_label]
            rows = []
            for task in tasks:
                rows.append(
                    {
                        "Course": task.get("course", ""),
                        "Task": task.get("task", ""),
                        "Priority": task.get("priority", ""),
                        "Reason": task.get("reason", ""),
                        "Est. minutes": task.get("estimated_minutes", ""),
                        "Due": task.get("due") or "",
                    }
                )
            if rows:
                st.table(rows)


def render_study_guide(placeholder, study_guide):
    with placeholder.container():
        if not study_guide:
            return

        for course, info in study_guide.items():
            st.subheader(course)
            grading_breakdown = info.get("grading_breakdown", {})
            if grading_breakdown:
                for title, weight in grading_breakdown.items():
                    st.write(f"{title}: {weight}%")
                st.write(f"Total weight detected: {info.get('total_weight_detected', 0)}%")
                tactical_tips = info.get("tactical_tips", [])
                if tactical_tips:
                    st.write("Tactical tips:")
                    for tip in tactical_tips:
                        st.write(tip)
                upcoming = info.get("upcoming_assessments", [])
                if upcoming:
                    st.write("Upcoming assessments:")
                    for item in upcoming[:5]:
                        weight = item.get("weight_percent")
                        if isinstance(weight, (int, float)):
                            st.write(
                                f"{item.get('title', '')} "
                                f"({item.get('date', '')}, {weight}%)"
                            )
                        else:
                            st.write(
                                f"{item.get('title', '')} "
                                f"({item.get('date', '')})"
                            )
                risk_analysis = info.get("risk_analysis", [])
                if risk_analysis:
                    st.markdown("### Risk Analysis")
                    for warning in risk_analysis:
                        st.warning(warning)
            else:
                st.write("No grading weights detected.")


def main():
    render_header()
    syllabus_inputs = render_syllabus_inputs()
    use_ai = st.checkbox("Use IBM AI for refinement", value=False)
    generate_clicked = render_generate_button()
    weekly_todo_placeholder, study_guide_placeholder = render_outputs()

    if generate_clicked:
        ai_engine.USE_REAL_AI = use_ai
        parsed_syllabi = parse_syllabi([text for text in syllabus_inputs if text.strip()])
        weekly_plan = generate_weekly_plan(parsed_syllabi)
        anchor_date = date.today()
        result = generate_plan_with_ai(
            parsed_syllabi,
            weekly_plan,
            anchor_date=anchor_date,
        )
        weekly_plan = result.get("weekly_plan", {})
        study_guide = result.get("study_guide", {})

        render_summary(weekly_plan, study_guide)
        render_weekly_plan(weekly_todo_placeholder, weekly_plan)
        render_study_guide(study_guide_placeholder, study_guide)


if __name__ == "__main__":
    main()
