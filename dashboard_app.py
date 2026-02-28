import streamlit as st
import streamlit.components.v1 as components

import base64
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

import ai.engine as ai_engine
from ai.engine import (
    build_engine_summary,
    build_peak_contributors,
    call_ai_intelligence,
    generate_plan_with_ai,
    simulate_shift,
    strategy_simulation,
)
from parser.syllabus_parser import parse_syllabi
from planner.weekly_planner import generate_weekly_plan

import plotly.graph_objects as go


RISK_LEVEL_ORDER = {
    "Normal": 0,
    "Elevated": 1,
    "High Risk": 2,
    "Critical Risk": 3,
}

RISK_COLOR = {
    "Normal": "#2DD4BF",
    "Elevated": "#F59E0B",
    "High Risk": "#FB7185",
    "Critical Risk": "#EF4444",
}

NEON_CHART_COLORS = [
    "#66F2FF",
    "#7E8BFF",
    "#58FFD6",
    "#FF7BE6",
    "#B3FF74",
    "#FFB85C",
    "#57A6FF",
    "#4CE1FF",
    "#B88BFF",
    "#FFE56A",
]


def _week_sort_key(week_label: str) -> int:
    parts = week_label.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


def _parse_due_date(date_str: str):
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


@lru_cache(maxsize=1)
def _load_background_svg_base64() -> Tuple[str, str]:
    assets_dir = Path(__file__).resolve().parent / "assets"
    light_svg = (assets_dir / "wallpaper.svg").read_bytes()
    dark_svg = (assets_dir / "wallpaper_dark.svg").read_bytes()
    return (
        base64.b64encode(light_svg).decode("ascii"),
        base64.b64encode(dark_svg).decode("ascii"),
    )


def _inject_styles() -> None:
    light_bg_b64, dark_bg_b64 = _load_background_svg_base64()
    st.markdown(
        f"""
        <style>
            :root {{
                --bg-img-light: url("data:image/svg+xml;base64,{light_bg_b64}");
                --bg-img-dark: url("data:image/svg+xml;base64,{dark_bg_b64}");
                --bg-img: var(--bg-img-dark);
                --bg-overlay-1: rgba(18, 102, 255, 0.83);
                --bg-overlay-2: rgba(2, 47, 168, 0.74);
                --vignette: radial-gradient(ellipse 100% 42% at 50% 100%, rgba(0, 10, 40, 0.35) 0%, rgba(0, 0, 30, 0.22) 25%, rgba(0, 0, 0, 0.10) 40%, rgba(0, 0, 0, 0.00) 60%);
                --font-family: "SF Pro Text", "SF Pro Display", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                --font-h1: 42px;
                --font-section: 19px;
                --font-card-title: 17px;
                --font-caption: 12.5px;
                --space-1: 0.375rem;
                --space-2: 0.625rem;
                --space-3: 1rem;
                --space-4: 1.4rem;
                --space-5: 1.8rem;
                --radius-card: 18px;
                --radius-pill: 999px;
                --blur-card: 16px;
                --card-padding: 20px;
                --card-bg: rgba(10, 20, 45, 0.42);
                --card-bg-strong: rgba(13, 27, 60, 0.48);
                --card-bg-soft: rgba(8, 16, 38, 0.38);
                --card-border: rgba(255, 255, 255, 0.10);
                --card-shadow-1: 0 20px 50px rgba(0, 0, 0, 0.35);
                --card-shadow-2: 0 4px 12px rgba(0, 0, 0, 0.25);
                --text-primary: rgba(246, 250, 255, 0.98);
                --text-secondary: rgba(209, 222, 246, 0.84);
                --chip-bg: linear-gradient(135deg, rgba(0, 120, 255, 0.25), rgba(80, 0, 255, 0.25));
                --chip-border: rgba(0, 180, 255, 0.4);
                --chip-text: #bfe9ff;
                --focus-ring: rgba(154, 202, 255, 0.68);
                --sidebar-text-primary: rgba(238, 246, 255, 0.96);
                --sidebar-text-secondary: rgba(214, 226, 246, 0.90);
                --sidebar-input-bg: rgba(12, 24, 52, 0.42);
                --sidebar-input-border: var(--card-border);
                --sidebar-button-bg: rgba(255, 255, 255, 0.09);
                --sidebar-button-text: var(--sidebar-text-primary);
            }}
            html[data-theme="light"] {{
                --bg-img: var(--bg-img-light);
                --bg-overlay-1: rgba(110, 170, 255, 0.66);
                --bg-overlay-2: rgba(56, 128, 232, 0.65);
                --vignette: none;
                --text-primary: rgba(248, 251, 255, 0.98);
                --text-secondary: rgba(227, 236, 252, 0.84);
                --focus-ring: rgba(132, 180, 242, 0.64);
                --sidebar-text-primary: rgba(28, 40, 62, 0.95);
                --sidebar-text-secondary: rgba(67, 84, 112, 0.88);
                --sidebar-input-bg: rgba(255, 255, 255, 0.72);
                --sidebar-input-border: rgba(106, 128, 164, 0.45);
                --sidebar-button-bg: rgba(255, 255, 255, 0.82);
                --sidebar-button-text: rgba(23, 36, 60, 0.94);
            }}
            html[data-theme="dark"] {{
                --bg-img: var(--bg-img-dark);
                --bg-overlay-1: rgba(18, 102, 255, 0.83);
                --bg-overlay-2: rgba(2, 47, 168, 0.74);
                --vignette: radial-gradient(ellipse 100% 42% at 50% 100%, rgba(0, 10, 40, 0.35) 0%, rgba(0, 0, 30, 0.22) 25%, rgba(0, 0, 0, 0.10) 40%, rgba(0, 0, 0, 0.00) 60%);
                --text-primary: rgba(246, 250, 255, 0.98);
                --text-secondary: rgba(209, 222, 246, 0.84);
                --focus-ring: rgba(154, 202, 255, 0.68);
            }}
            html:not([data-theme]) {{
                --bg-img: var(--bg-img-dark);
            }}
            @media (prefers-color-scheme: light) {{
                html:not([data-theme]) {{
                    --bg-img: var(--bg-img-light);
                    --bg-overlay-1: rgba(110, 170, 255, 0.66);
                    --bg-overlay-2: rgba(56, 128, 232, 0.65);
                    --vignette: none;
                    --text-primary: rgba(248, 251, 255, 0.98);
                    --text-secondary: rgba(227, 236, 252, 0.84);
                    --focus-ring: rgba(132, 180, 242, 0.64);
                    --sidebar-text-primary: rgba(28, 40, 62, 0.95);
                    --sidebar-text-secondary: rgba(67, 84, 112, 0.88);
                    --sidebar-input-bg: rgba(255, 255, 255, 0.72);
                    --sidebar-input-border: rgba(106, 128, 164, 0.45);
                    --sidebar-button-bg: rgba(255, 255, 255, 0.82);
                    --sidebar-button-text: rgba(23, 36, 60, 0.94);
                }}
            }}
            @media (prefers-color-scheme: dark) {{
                html:not([data-theme]) {{
                    --bg-img: var(--bg-img-dark);
                    --bg-overlay-1: rgba(18, 102, 255, 0.83);
                    --bg-overlay-2: rgba(2, 47, 168, 0.74);
                    --vignette: radial-gradient(ellipse 100% 42% at 50% 100%, rgba(0, 10, 40, 0.35) 0%, rgba(0, 0, 30, 0.22) 25%, rgba(0, 0, 0, 0.10) 40%, rgba(0, 0, 0, 0.00) 60%);
                    --text-primary: rgba(246, 250, 255, 0.98);
                    --text-secondary: rgba(209, 222, 246, 0.84);
                    --focus-ring: rgba(154, 202, 255, 0.68);
                }}
            }}
            html, body {{
                background: transparent !important;
                color: var(--text-primary);
            }}
            body {{
                font-family: var(--font-family);
            }}
            body::before {{
                content: "";
                position: fixed;
                inset: 0;
                z-index: -3;
                pointer-events: none;
                background-image: var(--bg-img);
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
                filter: saturate(110%) contrast(105%);
            }}
            [data-testid="stAppViewContainer"] {{
                position: relative;
                z-index: 1;
                isolation: isolate;
                min-height: 100vh;
                background: transparent !important;
            }}
            [data-testid="stAppViewContainer"]::before {{
                content: "";
                position: fixed;
                inset: 0;
                z-index: 0;
                pointer-events: none;
                background: linear-gradient(115deg, var(--bg-overlay-1) 0%, var(--bg-overlay-2) 62%, rgba(0, 76, 214, 0.65) 100%);
            }}
            [data-testid="stAppViewContainer"]::after {{
                content: "";
                position: fixed;
                left: 0;
                right: 0;
                bottom: 0;
                height: 44vh;
                z-index: 1;
                pointer-events: none;
                background: var(--vignette);
                background-repeat: no-repeat;
                background-position: center bottom;
                background-size: 100% 44vh;
            }}
            [data-testid="stAppViewContainer"] > .main,
            [data-testid="stHeader"],
            [data-testid="stSidebar"] {{
                position: relative;
                z-index: 2;
            }}
            .stApp {{
                background: transparent !important;
                color: var(--text-primary);
                font-family: var(--font-family);
                font-weight: 400;
            }}
            .stApp p,
            .stApp li,
            .stApp label {{
                color: var(--text-secondary);
            }}
            [data-testid="stSidebar"] {{
                color: var(--sidebar-text-primary);
            }}
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] li,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] .stMarkdown p,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
                color: var(--sidebar-text-secondary) !important;
            }}
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] strong {{
                color: var(--sidebar-text-primary) !important;
            }}
            [data-testid="stHeader"] {{
                background: rgba(0, 0, 0, 0);
            }}
            .block-container {{
                max-width: 1240px;
                padding-top: 1.25rem;
                padding-bottom: 2.1rem;
                gap: var(--space-5);
            }}
            [data-testid="stHorizontalBlock"] {{
                gap: var(--space-5);
                align-items: stretch;
            }}
            div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] {{
                display: flex !important;
                flex-wrap: nowrap !important;
                gap: 18px;
                align-items: stretch;
                width: 100%;
            }}
            div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                min-width: 0 !important;
                width: auto !important;
                flex: 1 1 0 !important;
            }}
            div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] > [data-testid="column"] > div {{
                width: 100%;
                min-width: 0;
                height: 100%;
            }}
            div[class*="st-key-card_ai_intelligence"] [data-testid="stHorizontalBlock"] {{
                display: flex !important;
                flex-wrap: nowrap !important;
                align-items: stretch !important;
                gap: 18px;
                width: 100%;
            }}
            div[class*="st-key-card_ai_intelligence"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                min-width: 0 !important;
                width: auto !important;
                flex: 1 1 0 !important;
            }}
            div[class*="st-key-card_ai_intelligence"] [data-testid="stMetric"] {{
                min-width: 0;
            }}
            .hero-header {{
                position: relative;
                padding: 1.2rem 1.35rem 1.28rem;
                margin-bottom: 1.45rem;
            }}
            .hero-header::before {{
                content: "";
                position: absolute;
                inset: -24px -10px auto -10px;
                height: 176px;
                border-radius: 34px;
                background: radial-gradient(ellipse at center, rgba(126, 188, 255, 0.30) 0%, rgba(109, 157, 255, 0.08) 56%, transparent 80%);
                filter: blur(14px);
                z-index: 0;
                pointer-events: none;
            }}
            .hero-header > * {{
                position: relative;
                z-index: 1;
            }}
            .glass-card,
            div[class*="st-key-card_"],
            [data-testid="stExpander"] {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: var(--radius-card);
                backdrop-filter: blur(16px) saturate(160%);
                -webkit-backdrop-filter: blur(16px) saturate(160%);
                box-shadow:
                    var(--card-shadow-1),
                    var(--card-shadow-2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.08),
                    0 0 80px rgba(0, 120, 255, 0.08);
                padding: var(--card-padding);
                margin-bottom: 1.15rem;
                transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
                overflow: hidden;
                transform: translateZ(0);
                will-change: transform;
            }}
            div[class*="st-key-card_workload_chart"],
            div[class*="st-key-card_grading_chart"],
            div[class*="st-key-card_ai_insight"],
            div[class*="st-key-card_ai_strategy"] {{
                background: var(--card-bg-strong);
            }}
            div[class*="st-key-card_ai_intelligence"],
            div[class*="st-key-card_detail_week_"],
            [data-testid="stExpander"] {{
                background: var(--card-bg-soft);
            }}
            div[class*="st-key-card_"]:hover,
            div[class*="st-key-card_"]:focus-within,
            [data-testid="stExpander"]:hover,
            [data-testid="stExpander"]:focus-within {{
                transform: translateY(-2px);
                border-color: rgba(255, 255, 255, 0.16);
                box-shadow:
                    0 24px 58px rgba(0, 0, 0, 0.40),
                    0 8px 16px rgba(0, 0, 0, 0.28),
                    inset 0 1px 0 rgba(255, 255, 255, 0.12),
                    0 0 96px rgba(0, 140, 255, 0.10);
            }}
            div[class*="st-key-card_"][class*="risk-red"] {{
                border-color: rgba(255, 127, 127, 0.34);
                box-shadow:
                    0 22px 56px rgba(25, 8, 10, 0.42),
                    0 8px 16px rgba(20, 8, 10, 0.28),
                    inset 0 1px 0 rgba(255, 224, 224, 0.12),
                    0 0 86px rgba(255, 88, 88, 0.09);
            }}
            div[class*="st-key-card_kpi_"] {{
                min-height: 146px;
                height: 100%;
                width: 100%;
                min-width: 0;
                display: block;
                grid-column: auto !important;
                grid-row: auto !important;
                writing-mode: horizontal-tb !important;
                white-space: normal !important;
                word-break: normal !important;
                overflow-wrap: break-word !important;
                padding: 1.25rem;
            }}
            div[class*="st-key-card_kpi_"][class*="risk-red"] {{
                position: relative;
                border: 1px solid rgba(255, 80, 80, 0.5);
                box-shadow:
                    0 0 25px rgba(255, 50, 80, 0.25),
                    0 20px 50px rgba(0, 0, 0, 0.35),
                    inset 0 1px 0 rgba(255, 255, 255, 0.10);
            }}
            div[class*="st-key-card_kpi_"][class*="risk-red"]::after {{
                content: "";
                position: absolute;
                left: 16px;
                right: 16px;
                bottom: 8px;
                height: 2px;
                border-radius: 999px;
                background: linear-gradient(90deg, rgba(255, 95, 95, 0), rgba(255, 95, 95, 0.38), rgba(255, 95, 95, 0));
                pointer-events: none;
            }}
            div[class*="st-key-card_workload_chart"] {{
                display: flex;
                flex-direction: column;
            }}
            .workload-content {{
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
            }}
            div[class*="st-key-card_kpi_"] .stMarkdown {{
                margin: 0 0 0.34rem 0 !important;
                white-space: normal !important;
                word-break: normal !important;
                overflow-wrap: break-word !important;
            }}
            div[class*="st-key-card_kpi_"] .stMarkdown:last-child {{
                margin-bottom: 0 !important;
            }}
            div[class*="st-key-card_kpi_"] .stMarkdown p {{
                margin: 0 !important;
                padding: 0 !important;
                white-space: normal !important;
                word-break: normal !important;
                overflow-wrap: break-word !important;
            }}
            .ai-section-header {{
                display: flex;
                align-items: center;
                gap: var(--space-2);
                flex-wrap: wrap;
                margin-bottom: 0.7rem;
            }}
            .ai-section-header .section-title {{
                margin-bottom: 0;
            }}
            .ai-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.36rem;
                font-size: 10px;
                letter-spacing: 1px;
                text-transform: uppercase;
                font-weight: 700;
                line-height: 1.1;
                color: #bfe9ff;
                background: linear-gradient(135deg, rgba(0, 120, 255, 0.25), rgba(80, 0, 255, 0.25));
                border: 1px solid rgba(0, 180, 255, 0.4);
                border-radius: 999px;
                padding: 4px 10px;
                backdrop-filter: blur(6px);
                -webkit-backdrop-filter: blur(6px);
                white-space: nowrap;
                animation: aiBadgeFadeIn 0.28s ease both;
            }}
            .ai-badge::before {{
                content: "";
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: #ff4a4a;
                box-shadow: 0 0 0 1px rgba(255, 120, 120, 0.42), 0 0 8px rgba(255, 74, 74, 0.32);
                flex-shrink: 0;
                animation: aiLiveDot 1s ease-in-out infinite;
            }}
            .ai-insight-chip {{
                position: relative;
                display: inline-block;
                border-radius: 999px;
                border: 1px solid rgba(170, 210, 255, 0.36);
                background:
                    radial-gradient(circle at 50% 42%, rgba(193, 236, 255, 0.16), transparent 56%),
                    linear-gradient(135deg, rgba(19, 66, 168, 0.54), rgba(56, 94, 188, 0.34));
                color: rgba(225, 242, 255, 0.95);
                font-size: 10px;
                letter-spacing: 0.9px;
                text-transform: uppercase;
                font-weight: 700;
                padding: 0.22rem 0.55rem;
                margin-bottom: 0.4rem;
                backdrop-filter: blur(6px);
                -webkit-backdrop-filter: blur(6px);
                overflow: hidden;
                box-shadow:
                    inset 0 1px 0 rgba(218, 240, 255, 0.22),
                    0 0 14px rgba(78, 150, 255, 0.22);
                animation: aiInsightAura 3.2s ease-in-out infinite;
            }}
            .ai-insight-chip::before {{
                content: "";
                position: absolute;
                inset: -36%;
                background:
                    linear-gradient(
                        120deg,
                        rgba(255, 255, 255, 0) 26%,
                        rgba(197, 244, 255, 0.16) 47%,
                        rgba(255, 255, 255, 0.44) 50%,
                        rgba(183, 242, 255, 0.14) 54%,
                        rgba(255, 255, 255, 0) 72%
                    );
                transform: translateX(-132%) rotate(8deg);
                animation: aiInsightSweep 3.9s cubic-bezier(0.2, 0.72, 0.2, 1) infinite;
                pointer-events: none;
            }}
            .kpi-label {{
                color: var(--text-secondary);
                letter-spacing: 0.04em;
                font-size: 0.76rem;
                text-transform: uppercase;
                margin-bottom: 4.8px;
                font-weight: 500;
            }}
            .kpi-value {{
                color: var(--text-primary);
                font-size: 1.86rem;
                font-weight: 600;
                line-height: 1.2;
                margin-bottom: 3.2px;
                text-shadow: 0 0 18px rgba(0, 140, 255, 0.35);
            }}
            .kpi-sub {{
                color: var(--text-secondary);
                font-size: 0.82rem;
                margin-bottom: 0.25rem;
                opacity: 0.9;
            }}
            .kpi-ai {{
                color: var(--text-secondary);
                font-size: 0.8rem;
                margin-top: 3.68px;
                margin-bottom: 16px;
                line-height: 1.4;
                opacity: 0.92;
            }}
            .kpi-stack {{
                display: flow-root;
            }}
            .kpi-stack > * {{
                margin-top: 0;
                margin-bottom: 0;
            }}
            .kpi-stack > .ai-insight-chip {{
                margin-bottom: 0.4rem;
            }}
            .kpi-stack > .kpi-label {{
                margin-bottom: 4.8px;
            }}
            .kpi-stack > .kpi-value {{
                margin-bottom: 3.2px;
            }}
            .kpi-stack > .kpi-sub {{
                margin-bottom: 0.25rem;
            }}
            .kpi-stack > .kpi-ai {{
                margin-top: 3.68px;
                margin-bottom: 14px;
            }}
            .chart-kicker,
            .chart-caption,
            .stCaptionContainer p {{
                font-size: var(--font-caption);
                color: var(--text-secondary) !important;
                opacity: 0.76;
            }}
            .chart-kicker {{
                margin-bottom: 0.25rem;
            }}
            .chart-caption {{
                margin-top: 0.1rem;
                margin-bottom: 0.2rem;
            }}
            .risk-signal-bar {{
                height: 0.42rem;
                border-radius: var(--radius-pill);
                background: linear-gradient(90deg, rgba(239, 68, 68, 0.65), rgba(239, 68, 68, 0.07));
                margin-bottom: 0.7rem;
            }}
            .section-title {{
                font-size: var(--font-section);
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 0.62rem;
                letter-spacing: -0.01em;
                line-height: 1.2;
            }}
            div[class*="st-key-card_"] h3,
            div[class*="st-key-card_"] h4 {{
                font-size: var(--font-card-title);
                font-weight: 600;
                color: var(--text-primary);
                letter-spacing: -0.01em;
            }}
            .app-title {{
                font-size: 42px;
                color: var(--text-primary);
                font-weight: 700;
                line-height: 1.06;
                margin-bottom: 0.28rem;
                letter-spacing: -0.5px;
            }}
            .app-subtitle {{
                color: var(--text-secondary);
                margin-bottom: 0;
                font-size: 1rem;
                opacity: 0.86;
            }}
            .stTextArea textarea,
            .stTextInput input,
            .stNumberInput input,
            div[data-baseweb="select"] > div,
            div[data-baseweb="slider"] {{
                background: rgba(12, 24, 52, 0.42) !important;
                color: var(--text-primary) !important;
                border: 1px solid var(--card-border) !important;
                border-radius: 14px !important;
                backdrop-filter: blur(12px) saturate(150%);
                -webkit-backdrop-filter: blur(12px) saturate(150%);
            }}
            [data-testid="stSidebar"] .stTextArea textarea,
            [data-testid="stSidebar"] .stTextInput input,
            [data-testid="stSidebar"] .stNumberInput input,
            [data-testid="stSidebar"] div[data-baseweb="select"] > div,
            [data-testid="stSidebar"] div[data-baseweb="slider"] {{
                background: var(--sidebar-input-bg) !important;
                color: var(--sidebar-text-primary) !important;
                border-color: var(--sidebar-input-border) !important;
            }}
            [data-testid="stSidebar"] .stTextArea textarea::placeholder,
            [data-testid="stSidebar"] .stTextInput input::placeholder {{
                color: var(--sidebar-text-secondary) !important;
                opacity: 0.84;
            }}
            .stButton button {{
                border-radius: 14px;
                border: 1px solid var(--card-border);
                background: rgba(255, 255, 255, 0.09);
                color: var(--text-primary);
                transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
            }}
            [data-testid="stSidebar"] .stButton button {{
                background: var(--sidebar-button-bg);
                color: var(--sidebar-button-text);
                border-color: var(--sidebar-input-border);
            }}
            .stButton button:hover {{
                transform: translateY(-1px);
                border-color: rgba(219, 236, 255, 0.3);
                box-shadow: 0 12px 22px rgba(4, 16, 45, 0.24);
            }}
            :where(button, input, textarea, select, [role="slider"]):focus-visible,
            [data-baseweb="slider"] [role="slider"]:focus-visible {{
                outline: none !important;
                box-shadow: 0 0 0 3px var(--focus-ring) !important;
                border-color: rgba(191, 221, 255, 0.7) !important;
            }}
            div[data-testid="stTable"] table tbody tr:hover td,
            div[data-testid="stDataFrame"] [role="row"]:hover {{
                background: rgba(255, 255, 255, 0.05) !important;
            }}
            #icloud-theme-toggle {{
                position: fixed;
                top: 0.68rem;
                right: 0.86rem;
                z-index: 1000;
                display: inline-flex;
                gap: 0.34rem;
                padding: 0.26rem;
                border-radius: var(--radius-pill);
                background: rgba(10, 20, 45, 0.42);
                border: 1px solid rgba(255, 255, 255, 0.10);
                box-shadow: 0 14px 34px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.12);
                backdrop-filter: blur(14px) saturate(155%);
                -webkit-backdrop-filter: blur(14px) saturate(155%);
            }}
            #icloud-theme-toggle .theme-btn {{
                border: 0;
                border-radius: var(--radius-pill);
                font-size: 11px;
                line-height: 1;
                padding: 0.37rem 0.64rem;
                color: var(--text-secondary);
                background: transparent;
                cursor: pointer;
                transition: background-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
            }}
            #icloud-theme-toggle .theme-btn:hover {{
                background: rgba(157, 193, 255, 0.18);
                color: var(--text-primary);
            }}
            #icloud-theme-toggle .theme-btn.active {{
                background: rgba(132, 174, 255, 0.36);
                color: var(--text-primary);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
            }}
            .js-plotly-plot .slice path {{
                transform-origin: center center;
                transition: transform 0.18s ease, filter 0.18s ease;
            }}
            .js-plotly-plot .slice path:hover {{
                transform: scale(1.06);
                filter: drop-shadow(0 0 10px rgba(129, 198, 255, 0.5));
            }}
            .js-plotly-plot .hoverlayer .hovertext {{
                filter: drop-shadow(0 0 10px rgba(95, 155, 255, 0.22));
            }}
            @keyframes peakPulse {{
                0% {{ transform: scale(1.0); filter: drop-shadow(0 0 3px rgba(166, 242, 255, 0.25)); }}
                50% {{ transform: scale(1.055); filter: drop-shadow(0 0 7px rgba(166, 242, 255, 0.38)); }}
                100% {{ transform: scale(1.0); filter: drop-shadow(0 0 3px rgba(166, 242, 255, 0.25)); }}
            }}
            @keyframes aiBadgeFadeIn {{
                from {{ opacity: 0; transform: translateY(2px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            @keyframes aiLiveDot {{
                0%, 100% {{
                    opacity: 0.35;
                    transform: scale(0.88);
                    box-shadow: 0 0 0 1px rgba(255, 120, 120, 0.35), 0 0 4px rgba(255, 74, 74, 0.2);
                }}
                50% {{
                    opacity: 1;
                    transform: scale(1.06);
                    box-shadow: 0 0 0 1px rgba(255, 144, 144, 0.5), 0 0 11px rgba(255, 74, 74, 0.58);
                }}
            }}
            @keyframes aiInsightAura {{
                0%, 100% {{
                    border-color: rgba(170, 210, 255, 0.36);
                    box-shadow:
                        inset 0 1px 0 rgba(218, 240, 255, 0.18),
                        0 0 10px rgba(78, 150, 255, 0.18);
                    filter: saturate(100%);
                }}
                50% {{
                    border-color: rgba(199, 235, 255, 0.58);
                    box-shadow:
                        inset 0 1px 0 rgba(230, 248, 255, 0.32),
                        0 0 20px rgba(120, 205, 255, 0.36);
                    filter: saturate(122%);
                }}
            }}
            @keyframes aiInsightSweep {{
                0%, 14% {{ transform: translateX(-134%) rotate(8deg); opacity: 0; }}
                28% {{ opacity: 1; }}
                52% {{ transform: translateX(118%) rotate(8deg); opacity: 0.98; }}
                100% {{ transform: translateX(134%) rotate(8deg); opacity: 0; }}
            }}
            .js-plotly-plot .scatterlayer .trace:last-child path {{
                transform-box: fill-box;
                transform-origin: center;
                animation: peakPulse 3.8s ease-in-out infinite;
            }}
            @media (prefers-reduced-motion: reduce) {{
                .ai-insight-chip,
                .ai-insight-chip::before {{
                    animation: none !important;
                }}
            }}
            @media (max-width: 1100px) {{
                div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] {{
                    flex-wrap: wrap !important;
                }}
                div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                    flex: 0 0 calc((100% - 18px) / 2) !important;
                    width: calc((100% - 18px) / 2) !important;
                }}
            }}
            @media (max-width: 980px) {{
                .block-container {{
                    padding-left: 0.95rem;
                    padding-right: 0.95rem;
                    padding-bottom: 1.4rem;
                    gap: 1rem;
                }}
                [data-testid="stHorizontalBlock"] {{
                    flex-direction: column;
                    gap: 1rem;
                }}
                [data-testid="column"] {{
                    width: 100% !important;
                    flex: 1 1 100% !important;
                }}
                div[class*="st-key-card_"],
                [data-testid="stExpander"] {{
                    border-radius: 16px;
                    padding: 16px;
                }}
                [data-testid="stAppViewContainer"]::after {{
                    height: 36vh;
                    background-size: 100% 36vh;
                }}
                .app-title {{
                    font-size: 34px;
                }}
                #icloud-theme-toggle {{
                    top: 0.58rem;
                    right: 0.58rem;
                    gap: 0.2rem;
                    padding: 0.22rem;
                }}
                #icloud-theme-toggle .theme-btn {{
                    font-size: 10px;
                    padding: 0.32rem 0.5rem;
                }}
            }}
            @media (max-width: 640px) {{
                div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] {{
                    flex-wrap: wrap !important;
                }}
                div[class*="st-key-kpi_row"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                    flex: 0 0 100% !important;
                    width: 100% !important;
                }}
            }}
        </style>
        <div id="icloud-theme-toggle" aria-label="Theme Toggle">
            <button type="button" class="theme-btn" data-theme="system">System</button>
            <button type="button" class="theme-btn" data-theme="light">Light</button>
            <button type="button" class="theme-btn" data-theme="dark">Dark</button>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        """
        <script>
            (function () {
                const doc = window.parent.document;
                const root = doc.documentElement;
                const key = "theme";

                function applyTheme(theme) {
                    if (theme === "light" || theme === "dark") {
                        root.setAttribute("data-theme", theme);
                    } else {
                        root.removeAttribute("data-theme");
                    }
                    try {
                        window.parent.localStorage.setItem(key, theme);
                    } catch (e) {}
                    const toggle = doc.getElementById("icloud-theme-toggle");
                    if (!toggle) return;
                    toggle.querySelectorAll(".theme-btn").forEach((btn) => {
                        const btnTheme = btn.getAttribute("data-theme");
                        btn.classList.toggle("active", btnTheme === theme);
                    });
                }

                function initTheme() {
                    let saved = "dark";
                    try {
                        saved = window.parent.localStorage.getItem(key) || "dark";
                    } catch (e) {}
                    applyTheme(saved);
                }

                function bindToggle() {
                    const toggle = doc.getElementById("icloud-theme-toggle");
                    if (!toggle || toggle.dataset.bound === "1") return;
                    toggle.dataset.bound = "1";
                    toggle.addEventListener("click", (event) => {
                        const btn = event.target.closest(".theme-btn");
                        if (!btn) return;
                        const nextTheme = btn.getAttribute("data-theme");
                        applyTheme(nextTheme);
                    });
                }

                initTheme();
                bindToggle();
            })();
        </script>
        """,
        height=0,
        width=0,
    )


def _set_sample_syllabi() -> None:
    st.session_state["course_count"] = 2
    st.session_state["syllabus_0"] = (
        "CSE 2331 - Data Structures (Spring 2026)\n"
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
        "Homework 1: Arrays and Big-O - due January 19\n"
        "Homework 2: Stacks & Queues - due January 26\n"
        "Homework 3: Trees - due February 2\n"
        "Homework 4: Hash Tables - due February 9\n"
        "Homework 5: Graphs - due February 23\n"
        "\n"
        "Quiz 1: February 5\n"
        "Quiz 2: March 5\n"
        "Midterm Exam: February 19 (20%)\n"
        "\n"
        "Project Milestone 1: Proposal - due February 12 (5%)\n"
        "Project Milestone 2: Prototype - due March 12 (10%)\n"
        "Project Submission - due April 2 (10%)\n"
        "\n"
        "Final Exam: April 29 (20%)"
    )
    st.session_state["syllabus_1"] = (
        "ECON 1011 - Principles of Microeconomics (Spring 2026)\n"
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
        "Homework 1: Demand Analysis - due January 21\n"
        "Homework 2: Elasticity - due February 4\n"
        "Homework 3: Consumer Choice - due February 18\n"
        "Homework 4: Costs - due March 4\n"
        "\n"
        "Quiz 1: February 6\n"
        "Quiz 2: March 6\n"
        "Midterm Exam: March 11 (25%)\n"
        "\n"
        "Project Milestone 1: Topic Proposal - due February 20 (5%)\n"
        "Project Milestone 2: Draft Report - due March 27 (5%)\n"
        "Project Submission - due April 17 (5%)\n"
        "\n"
        "Final Exam: May 2 (30%)"
    )


def _render_input_panel() -> Tuple[List[str], bool, bool]:
    syllabus_inputs: List[str] = []
    with st.sidebar:
        st.markdown("### Input")
        st.button("Load Sample Syllabi", on_click=_set_sample_syllabi, width="stretch")
        course_count = st.number_input(
            "Number of courses",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
            key="course_count",
        )
        for index in range(int(course_count)):
            syllabus_inputs.append(
                st.text_area(
                    f"Course {index + 1} syllabus",
                    placeholder="Paste syllabus here...",
                    key=f"syllabus_{index}",
                    height=160,
                )
            )
        use_ai = st.checkbox("Use IBM AI for refinement", value=False)
        generate_clicked = st.button("Generate Dashboard", width="stretch")

    return syllabus_inputs, use_ai, generate_clicked


def _aggregate_weekly_risk_and_stress(
    study_guide: Dict[str, Dict[str, object]],
) -> Tuple[Dict[str, int], Dict[str, str]]:
    stress_score_by_week: Dict[str, int] = {}
    risk_rank_by_week: Dict[str, int] = {}
    risk_by_week: Dict[str, str] = {}

    for info in study_guide.values():
        weekly_metrics = info.get("weekly_metrics", {})
        if not isinstance(weekly_metrics, dict):
            continue
        for week, metrics in weekly_metrics.items():
            if not isinstance(metrics, dict):
                continue
            stress = int(metrics.get("weekly_stress_score") or 0)
            risk = str(metrics.get("risk_level") or "Normal")
            stress_score_by_week[week] = stress_score_by_week.get(week, 0) + stress

            candidate_rank = RISK_LEVEL_ORDER.get(risk, 0)
            current_rank = risk_rank_by_week.get(week, -1)
            if candidate_rank > current_rank:
                risk_rank_by_week[week] = candidate_rank
                risk_by_week[week] = risk

    return stress_score_by_week, risk_by_week


def _weekly_metrics_to_stress_risk(
    weekly_metrics: Dict[str, Dict[str, object]],
) -> Tuple[Dict[str, int], Dict[str, str]]:
    stress_score_by_week: Dict[str, int] = {}
    risk_by_week: Dict[str, str] = {}
    for week, metrics in weekly_metrics.items():
        if not isinstance(metrics, dict):
            continue
        stress_score_by_week[str(week)] = int(float(metrics.get("weekly_stress_score") or 0.0))
        risk_by_week[str(week)] = str(metrics.get("risk_level") or "Normal")
    return stress_score_by_week, risk_by_week


def _render_peak_breakdown(contributors: List[Dict[str, object]], peak_week: str) -> None:
    with st.container(key="card_peak_breakdown"):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<div class="section-title">Peak Breakdown</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if not contributors:
            st.info("No peak-week contributors detected.")
            return

        st.caption(f"Top contributors for {peak_week}")
        rows = []
        for item in contributors:
            rows.append(
                {
                    "Task": item.get("task", ""),
                    "Course": item.get("course", ""),
                    "Kind": item.get("kind", ""),
                    "Stress Min": item.get("stress_contribution", 0),
                    "Weight": f"{float(item.get('weight_effective') or 0.0):.1f}%",
                }
            )
        st.table(rows)


def _render_simulation_results(
    shift_result: Dict[str, object],
    strategy_result: Dict[str, object],
) -> None:
    with st.container(key="card_what_if_results"):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<div class="section-title">What-if Results</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        shift_error = shift_result.get("error") if isinstance(shift_result, dict) else None
        strategy_error = strategy_result.get("error") if isinstance(strategy_result, dict) else None

        left, right = st.columns(2)
        with left:
            st.markdown("**Shift Simulation**")
            if shift_error:
                st.caption(f"Unavailable: {shift_error}")
            else:
                st.write(
                    f"Peak: {shift_result.get('peak_before', {}).get('week', 'N/A')} -> "
                    f"{shift_result.get('peak_after', {}).get('week', 'N/A')}"
                )
                st.write(f"Delta: {float(shift_result.get('delta_percent') or 0.0):.1f}%")
                st.write(f"Weeks changed: {int(shift_result.get('changed_week_count') or 0)}")

        with right:
            st.markdown("**Strategy Simulation**")
            if strategy_error:
                st.caption(f"Unavailable: {strategy_error}")
            else:
                st.write(
                    f"Peak: {strategy_result.get('peak_before', {}).get('week', 'N/A')} -> "
                    f"{strategy_result.get('peak_after', {}).get('week', 'N/A')}"
                )
                st.write(f"Delta: {float(strategy_result.get('delta_percent') or 0.0):.1f}%")
                st.write(f"Weeks changed: {int(strategy_result.get('changed_week_count') or 0)}")



def _render_ai_intelligence_card(ai_payload: Dict[str, object]) -> None:
    with st.container(key="card_ai_intelligence"):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<span class="ai-badge">AI GENERATED</span>'
                '<div class="section-title">AI Intelligence Explanation</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if not isinstance(ai_payload, dict):
            st.info("AI intelligence is unavailable.")
            return

        kpis = ai_payload.get("kpis", {})
        why_risky = ai_payload.get("why_risky", [])
        simulation_narrative = str(ai_payload.get("simulation_narrative") or "")
        allocation = ai_payload.get("time_allocation_strategy", {})

        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.metric("Burnout %", f"{float(kpis.get('burnout_probability_percent') or 0.0):.1f}")
        with kpi_cols[1]:
            st.metric("Acceleration Index", f"{float(kpis.get('stress_acceleration_index') or 0.0):.1f}")
        with kpi_cols[2]:
            st.metric("Compression Risk", f"{float(kpis.get('compression_risk_score') or 0.0):.1f}")

        if isinstance(why_risky, list) and why_risky:
            st.markdown("**Why risky**")
            for item in why_risky[:4]:
                st.write(f"- {item}")

        if simulation_narrative:
            st.markdown("**Simulation Narrative**")
            st.write(simulation_narrative)

        if isinstance(allocation, dict):
            st.markdown(
                "**Recommended Time Allocation** "
                f"(Exam {float(allocation.get('exam_prep') or 0.0):.1f}% / "
                f"Projects {float(allocation.get('projects') or 0.0):.1f}% / "
                f"Homework {float(allocation.get('homework') or 0.0):.1f}%)"
            )


def _collect_upcoming_exam_weight(study_guide: Dict[str, Dict[str, object]]) -> float:
    today = date.today()
    candidates: List[Tuple[date, float]] = []
    for info in study_guide.values():
        for assessment in info.get("upcoming_assessments", []):
            if not isinstance(assessment, dict):
                continue
            kind = str(assessment.get("kind") or "").lower()
            if kind != "exam":
                continue
            due_date = _parse_due_date(assessment.get("date"))
            weight = assessment.get("weight_percent")
            if due_date and due_date >= today and isinstance(weight, (int, float)):
                candidates.append((due_date, float(weight)))
    if not candidates:
        return 0.0
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _render_kpis(
    weekly_plan: Dict[str, List[Dict[str, object]]],
    stress_score_by_week: Dict[str, int],
    risk_by_week: Dict[str, str],
    study_guide: Dict[str, Dict[str, object]],
) -> None:
    weeks_sorted = sorted(stress_score_by_week.keys(), key=_week_sort_key)
    total_stress = sum(stress_score_by_week.values())
    avg_stress = (total_stress / len(stress_score_by_week)) if stress_score_by_week else 0
    peak_week = max(weeks_sorted, key=lambda w: stress_score_by_week.get(w, 0)) if weeks_sorted else "N/A"
    peak_stress = stress_score_by_week.get(peak_week, 0) if weeks_sorted else 0
    upcoming_exam_weight = _collect_upcoming_exam_weight(study_guide)

    burnout_risk = "Normal"
    if risk_by_week:
        burnout_risk = max(
            risk_by_week.values(),
            key=lambda item: RISK_LEVEL_ORDER.get(item, 0),
        )

    if avg_stress >= 560:
        stress_ai = "AI signal: sustained overload likely. Shift prep to earlier weeks."
    elif avg_stress >= 360:
        stress_ai = "AI signal: moderate pressure. Keep task batching tight."
    else:
        stress_ai = "AI signal: manageable pace. Protect consistency."

    if peak_stress >= 650:
        peak_ai = "AI signal: severe spike. Add recovery buffers before this week."
    elif peak_stress >= 420:
        peak_ai = "AI signal: concentrated workload. Pre-load key deliverables."
    else:
        peak_ai = "AI signal: peak is controlled with current sequencing."

    if upcoming_exam_weight >= 30:
        exam_ai = "AI signal: high-stakes exam incoming. Bias effort toward exam prep."
    elif upcoming_exam_weight >= 20:
        exam_ai = "AI signal: meaningful assessment ahead. Keep revision cadence active."
    else:
        exam_ai = "AI signal: no immediate heavy exam load detected."

    if burnout_risk == "Critical Risk":
        burnout_ai = "AI signal: burnout risk is critical. Reduce context switching now."
    elif burnout_risk == "High Risk":
        burnout_ai = "AI signal: burnout trend elevated. Protect sleep and focus blocks."
    else:
        burnout_ai = "AI signal: resilience level stable. Maintain current tempo."

    kpi_data = [
        ("AI Stress Intelligence", f"{avg_stress:.0f}", "Avg weekly stress score", stress_ai, False),
        ("AI Peak Forecast", peak_week, f"Peak load: {peak_stress}", peak_ai, False),
        ("AI Exam Pressure", f"{upcoming_exam_weight:.0f}%", "Nearest upcoming exam", exam_ai, False),
        ("AI Burnout Risk", burnout_risk, f"{len(weekly_plan)} weeks scheduled", burnout_ai, burnout_risk in {"High Risk", "Critical Risk"}),
    ]
    with st.container(key="kpi_row"):
        cols = st.columns(4)
        for idx, (label, value, sub, ai_text, is_risk) in enumerate(kpi_data):
            card_key = f"card_kpi_{idx}_risk-red" if is_risk else f"card_kpi_{idx}"
            with cols[idx]:
                with st.container(key=card_key):
                    st.markdown(
                        (
                            '<div class="kpi-stack">'
                            '<span class="ai-insight-chip">AI Insight</span>'
                            f'<div class="kpi-label">{label}</div>'
                            f'<div class="kpi-value">{value}</div>'
                            f'<div class="kpi-sub">{sub}</div>'
                            f'<div class="kpi-ai">{ai_text}</div>'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )


def render_workload_chart(
    stress_score_by_week: Dict[str, int],
    risk_by_week: Dict[str, str],
) -> None:
    with st.container(key="card_workload_chart"):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<div class="section-title">Weekly Workload</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if not stress_score_by_week:
            st.info("No weekly stress data available yet.")
            return

        weeks = sorted(stress_score_by_week.keys(), key=_week_sort_key)
        values = [stress_score_by_week.get(week, 0) for week in weeks]
        if not weeks:
            st.info("No weekly labels available.")
            return

        x_vals = list(range(len(weeks)))
        avg_stress = sum(values) / len(values)
        sustainable_limit = max(300.0, avg_stress * 1.15)

        def _risk_state(week: str, value: float) -> str:
            risk = str(risk_by_week.get(week, "Normal"))
            if risk == "Critical Risk" or value >= sustainable_limit * 1.14:
                return "high"
            if risk == "High Risk" or value >= sustainable_limit * 0.94:
                return "elevated"
            return "normal"

        state_colors = {
            "normal": "#3FF5FF",
            "elevated": "#FFA235",
            "high": "#FF3E56",
        }
        states = [_risk_state(week, value) for week, value in zip(weeks, values)]

        peak_index = max(range(len(values)), key=lambda idx: values[idx])
        peak_week = weeks[peak_index]
        peak_value = values[peak_index]
        peak_x = x_vals[peak_index]

        accel_threshold = max(28.0, avg_stress * 0.17)
        accel_points = [
            index
            for index in range(1, len(values))
            if (values[index] - values[index - 1]) >= accel_threshold
        ]

        fig = go.Figure()
        # Edge fade for a cinematic glass look.
        if x_vals:
            fig.add_vrect(
                x0=-0.5,
                x1=0.22,
                fillcolor="rgba(7, 15, 34, 0.46)",
                line_width=0,
                layer="above",
            )
            fig.add_vrect(
                x0=x_vals[-1] - 0.22,
                x1=x_vals[-1] + 0.5,
                fillcolor="rgba(7, 15, 34, 0.46)",
                line_width=0,
                layer="above",
            )

            # Overload zone around peak week.
            fig.add_shape(
                type="rect",
                xref="x",
                yref="paper",
                x0=peak_x - 0.45,
                x1=peak_x + 0.45,
                y0=0.0,
                y1=1.0,
                fillcolor="rgba(255, 92, 102, 0.22)",
                line=dict(width=0),
                layer="below",
            )
            # Faint top fade accent for overload band.
            fig.add_shape(
                type="rect",
                xref="x",
                yref="paper",
                x0=peak_x - 0.45,
                x1=peak_x + 0.45,
                y0=0.78,
                y1=1.0,
                fillcolor="rgba(255, 92, 102, 0.14)",
                line=dict(width=0),
                layer="below",
            )
            fig.add_shape(
                type="rect",
                xref="x",
                yref="paper",
                x0=peak_x - 0.45,
                x1=peak_x + 0.45,
                y0=0.90,
                y1=1.0,
                fillcolor="rgba(255, 92, 102, 0.18)",
                line=dict(width=0),
                layer="below",
            )
            fig.add_annotation(
                x=peak_x,
                y=1.0,
                yref="paper",
                text="Overload Zone",
                showarrow=False,
                font=dict(color="#FFC0C6", size=11),
            )

            # Gradient area fill using layered low-opacity fills.
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=values,
                    mode="lines",
                    line=dict(width=0),
                    fill="tozeroy",
                    fillcolor="rgba(95, 184, 255, 0.15)",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=[value * 0.62 for value in values],
                    mode="lines",
                    line=dict(width=0),
                    fill="tozeroy",
                    fillcolor="rgba(81, 148, 255, 0.08)",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # 3-layer line system: base glow, semi-glow, sharp top stroke.
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=values,
                    mode="lines",
                    line=dict(color="rgba(112, 237, 255, 0.19)", width=30, shape="spline", smoothing=1.25),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=values,
                    mode="lines",
                    line=dict(color="rgba(102, 226, 255, 0.34)", width=16, shape="spline", smoothing=1.25),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            for state, label in (("normal", "Normal"), ("elevated", "Elevated"), ("high", "High Risk")):
                y_state = [value if state_name == state else None for value, state_name in zip(values, states)]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_state,
                        mode="lines+markers",
                        connectgaps=False,
                        line=dict(color=state_colors[state], width=5.3, shape="spline", smoothing=1.25),
                        marker=dict(
                            size=9,
                            color=state_colors[state],
                            line=dict(color="rgba(255,255,255,0.38)", width=1),
                        ),
                        customdata=[[week] for week in weeks],
                        hovertemplate="%{customdata[0]}<br>Stress: %{y:.0f}<extra>" + label + "</extra>",
                        name=label,
                    )
                )

            # Acceleration arrows where stress ramps rapidly.
            if accel_points:
                fig.add_trace(
                    go.Scatter(
                        x=[x_vals[idx] for idx in accel_points],
                        y=[values[idx] + max(8.0, values[idx] * 0.04) for idx in accel_points],
                        mode="markers",
                        marker=dict(
                            symbol="triangle-up",
                            size=10,
                            color="#FFD27D",
                            line=dict(color="#FFEAC2", width=1),
                        ),
                        customdata=[[weeks[idx], values[idx] - values[idx - 1]] for idx in accel_points],
                        hovertemplate="%{customdata[0]}<br>Stress acceleration: +%{customdata[1]:.0f}<extra></extra>",
                        name="Acceleration",
                    )
                )

            # Sustainable threshold line.
            fig.add_hline(
                y=sustainable_limit,
                line=dict(color="rgba(136, 188, 255, 0.46)", width=0.9, dash="dot"),
                annotation_text="Sustainable Limit",
                annotation_position="top left",
                annotation_font=dict(color="#C8DDFF", size=11),
            )

            # Peak highlight with pulse-like layered markers.
            fig.add_trace(
                go.Scatter(
                    x=[peak_x],
                    y=[peak_value],
                    mode="markers",
                    marker=dict(size=42, color="rgba(145, 246, 255, 0.16)", line=dict(width=0)),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[peak_x],
                    y=[peak_value],
                    mode="markers",
                    marker=dict(size=24, color="rgba(157, 247, 255, 0.34)", line=dict(width=0)),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[peak_x],
                    y=[peak_value],
                    mode="markers",
                    marker=dict(size=12, color="#D8FBFF", line=dict(color="#FFFFFF", width=2.0)),
                    showlegend=False,
                    customdata=[[peak_week]],
                    hovertemplate="Peak week: %{customdata[0]}<br>Stress: %{y:.0f}<extra></extra>",
                )
            )
            fig.add_annotation(
                x=peak_x,
                y=peak_value,
                text=f"Peak: {peak_week} ({peak_value})",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1,
                arrowcolor="rgba(177, 216, 255, 0.62)",
                ax=0,
                ay=-52,
                font=dict(color="#E8F6FF", size=12),
                bgcolor="rgba(14, 28, 58, 0.82)",
                bordercolor="rgba(169, 206, 255, 0.45)",
                borderwidth=1,
                borderpad=6,
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=8, r=10, t=16, b=8),
                height=350,
                yaxis_title="Stress / Load Score",
                xaxis_title="Week",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0, borderwidth=0),
                font=dict(color="#DDE9FF"),
                hoverlabel=dict(
                    bgcolor="rgba(12, 24, 54, 0.92)",
                    bordercolor="rgba(136, 188, 255, 0.44)",
                    font=dict(color="#E8F4FF", size=12),
                ),
            )
            fig.update_yaxes(
                gridcolor="rgba(160, 196, 255, 0.11)",
                griddash="dot",
                zeroline=False,
                gridwidth=1,
            )
            fig.update_xaxes(
                tickmode="array",
                tickvals=x_vals,
                ticktext=weeks,
                gridcolor="rgba(160, 196, 255, 0.08)",
                griddash="dot",
                zeroline=False,
            )
        st.markdown('<div class="chart-kicker">AI Structural Load Analysis</div>', unsafe_allow_html=True)
        st.markdown('<div class="workload-content">', unsafe_allow_html=True)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
        st.markdown('<div class="chart-caption">AI detected stress acceleration before peak.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_grading_chart(study_guide: Dict[str, Dict[str, object]]) -> None:
    with st.container(key="card_grading_chart"):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<div class="section-title">Grading Distribution by Course</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        course_distributions: Dict[str, Dict[str, float]] = {}
        for course_name, info in study_guide.items():
            grading_breakdown = info.get("grading_breakdown", {})
            if not isinstance(grading_breakdown, dict):
                continue
            clean = {
                str(label).strip() or "Other": float(weight)
                for label, weight in grading_breakdown.items()
                if isinstance(weight, (int, float)) and float(weight) > 0
            }
            if clean:
                course_distributions[course_name] = clean

        if not course_distributions:
            st.info("No grading distribution data available.")
            return

        st.caption("AI Weight Sensitivity Model")
        course_names = list(course_distributions.keys())
        selected_course = st.selectbox(
            "Course",
            course_names,
            label_visibility="collapsed",
            key="grading_course_selector",
        )
        distribution = course_distributions[selected_course]
        labels = list(distribution.keys())
        values = list(distribution.values())
        total_weight = sum(values)
        max_weight = max(values) if values else 1.0
        impact_scores = [(value / max_weight) * 100.0 for value in values]
        customdata = [[value, impact] for value, impact in zip(values, impact_scores)]
        colors = [NEON_CHART_COLORS[i % len(NEON_CHART_COLORS)] for i in range(len(labels))]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.68,
                    textinfo="percent",
                    textposition="inside",
                    insidetextfont=dict(size=12, color="#F4FAFF"),
                    marker=dict(colors=colors, line=dict(color="rgba(11,22,44,0.96)", width=2)),
                    sort=False,
                    pull=[0.014] * len(labels),
                    customdata=customdata,
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Weight: %{customdata[0]:.1f}%<br>"
                        "Relative Impact: %{customdata[1]:.0f}<extra></extra>"
                    ),
                )
            ]
        )
        # Soft radial glow + subtle lighting layers behind donut.
        fig.add_shape(
            type="circle",
            xref="paper",
            yref="paper",
            x0=0.13,
            y0=0.13,
            x1=0.87,
            y1=0.87,
            fillcolor="rgba(92, 150, 255, 0.066)",
            line=dict(width=0),
            layer="below",
        )
        fig.add_shape(
            type="circle",
            xref="paper",
            yref="paper",
            x0=0.21,
            y0=0.21,
            x1=0.79,
            y1=0.79,
            fillcolor="rgba(138, 196, 255, 0.03)",
            line=dict(width=0),
            layer="below",
        )
        fig.add_annotation(
            text=f"<b>{selected_course}</b><br>Total Weight {total_weight:.0f}%",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#EAF4FF", size=12),
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=16, b=10),
            height=340,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.12,
                xanchor="center",
                x=0.5,
                font=dict(color="#CFE0FF", size=11),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
            ),
            font=dict(color="#DDE9FF"),
            transition=dict(duration=420, easing="cubic-in-out"),
            hoverlabel=dict(
                bgcolor="rgba(12, 24, 54, 0.92)",
                bordercolor="rgba(160, 204, 255, 0.38)",
                font=dict(color="#E8F4FF", size=12),
            ),
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )


def _render_ai_strategy_card(
    weekly_plan: Dict[str, List[Dict[str, object]]],
    stress_score_by_week: Dict[str, int],
    risk_by_week: Dict[str, str],
    study_guide: Dict[str, Dict[str, object]],
) -> None:
    with st.container(key="card_ai_strategy"):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<span class="ai-badge">AI GENERATED</span>'
                '<div class="section-title">AI Strategy</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        weeks_sorted = sorted(stress_score_by_week.keys(), key=_week_sort_key)
        peak_week = max(weeks_sorted, key=lambda w: stress_score_by_week.get(w, 0)) if weeks_sorted else None
        peak_risk = risk_by_week.get(peak_week, "Normal") if peak_week else "Normal"

        tactics: List[str] = []
        warnings: List[str] = []
        for info in study_guide.values():
            tactics.extend([str(item) for item in info.get("tactical_tips", []) if isinstance(item, str)])
            warnings.extend([str(item) for item in info.get("warnings", []) if isinstance(item, str)])

        tactic_text = " ".join(tactics[:2]) if tactics else "Focus first on the nearest high-weight assessments."
        warning_text = warnings[0] if warnings else "No immediate structural grading issues detected."

        st.markdown(
            (
                f"**Execution focus:** Prioritize tasks in **{peak_week or 'the earliest active week'}** "
                f"where risk is **{peak_risk}**. Maintain daily progress on high-priority tasks and "
                f"avoid deferring exam preparation to the last week."
            )
        )
        st.markdown(f"**Tactical note:** {tactic_text}")
        st.markdown(f"**Guardrail:** {warning_text}")
        st.markdown(f"**Plan coverage:** {sum(len(tasks) for tasks in weekly_plan.values())} scheduled tasks.")


def _render_ai_insight_panel(
    weekly_plan: Dict[str, List[Dict[str, object]]],
    stress_score_by_week: Dict[str, int],
    risk_by_week: Dict[str, str],
    study_guide: Dict[str, Dict[str, object]],
) -> None:
    with st.container(key="card_ai_insight_risk-red"):
        weeks_sorted = sorted(stress_score_by_week.keys(), key=_week_sort_key)
        burnout_risk = "Normal"
        if risk_by_week:
            burnout_risk = max(risk_by_week.values(), key=lambda item: RISK_LEVEL_ORDER.get(item, 0))
        hot_weeks = sum(1 for risk in risk_by_week.values() if risk in {"Elevated", "High Risk", "Critical Risk"})
        total_tasks = sum(len(tasks) for tasks in weekly_plan.values())
        max_stress = max(stress_score_by_week.values()) if stress_score_by_week else 0
        peak_week = max(weeks_sorted, key=lambda w: stress_score_by_week.get(w, 0)) if weeks_sorted else "N/A"

        upcoming_exam_weight = _collect_upcoming_exam_weight(study_guide)
        strategic_move = "Maintain steady execution across weekly priorities."
        if burnout_risk == "Critical Risk":
            strategic_move = "Aggressively front-load exam prep and reduce parallel project load."
        elif burnout_risk == "High Risk":
            strategic_move = "Create workload buffers before the peak week and lock deep-work blocks."
        elif upcoming_exam_weight >= 25:
            strategic_move = "Reallocate study time toward high-weight exam preparation now."

        st.markdown(
            (
                '<div class="ai-section-header">'
                '<span class="ai-badge">AI GENERATED</span>'
                '<div class="section-title">AI Workload Signal</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if burnout_risk in {"High Risk", "Critical Risk"}:
            st.markdown('<div class="risk-signal-bar"></div>', unsafe_allow_html=True)
        st.markdown(
            (
                f"**Risk posture:** {burnout_risk} across **{len(stress_score_by_week)} active weeks** "
                f"with **{hot_weeks} high-pressure weeks** detected."
            )
        )
        st.markdown(
            f"**Peak stress event:** {peak_week} at **{max_stress} stress points** across **{total_tasks} scheduled tasks**."
        )
        st.markdown(f"**Recommended AI move:** {strategic_move}")


def _render_raw_outputs(
    weekly_plan: Dict[str, List[Dict[str, object]]],
    study_guide: Dict[str, Dict[str, object]],
) -> None:
    with st.expander("Detailed Weekly Plan", expanded=False):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<span class="ai-badge">AI GENERATED</span>'
                '<div class="section-title">Detailed Weekly Plan</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        for index, week in enumerate(sorted(weekly_plan.keys(), key=_week_sort_key)):
            rows = []
            for task in weekly_plan[week]:
                rows.append(
                    {
                        "Course": task.get("course", ""),
                        "Task": task.get("task", ""),
                        "Priority": task.get("priority", ""),
                        "Due": task.get("due") or "",
                        "Est. minutes": task.get("estimated_minutes", ""),
                    }
                )
            if rows:
                with st.container(key=f"card_detail_week_{index}"):
                    st.markdown(f"**{week}**")
                    st.table(rows)
    with st.expander("Study Guide Detail", expanded=False):
        st.markdown(
            (
                '<div class="ai-section-header">'
                '<span class="ai-badge">AI GENERATED</span>'
                '<div class="section-title">Study Guide Detail</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.json(study_guide)


def main() -> None:
    st.set_page_config(page_title="Syllabus-to-Action Dashboard", page_icon=":bar_chart:", layout="wide")
    _inject_styles()

    st.markdown(
        """
        <div class="hero-header">
            <div class="app-title">Syllabus-to-Action Dashboard</div>
            <div class="app-subtitle">
                Academic workload intelligence combining deterministic structure with AI-powered stress simulation.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    syllabus_inputs, use_ai, generate_clicked = _render_input_panel()

    if not generate_clicked:
        st.info("Paste syllabus text in the sidebar and click Generate Dashboard.")
        return

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
    base_stress_score_by_week, base_risk_by_week = _aggregate_weekly_risk_and_stress(study_guide)
    engine_summary = build_engine_summary(result)
    peak_contributors = build_peak_contributors(result, limit=5)

    with st.sidebar:
        st.markdown("### Strategy Controls")
        task_options = [
            str(item.get("task") or "")
            for item in peak_contributors
            if isinstance(item, dict) and item.get("task")
        ]
        selected_task = st.selectbox(
            "Shift Target",
            task_options if task_options else ["(no peak tasks)"],
            key="shift_target_task",
        )
        shift_days = st.slider("Shift days", min_value=-14, max_value=14, value=0, step=1)
        exam_target = st.slider("Target % exam prep", min_value=10, max_value=70, value=38, step=1)
        project_target = st.slider("Target % projects", min_value=10, max_value=70, value=34, step=1)
        homework_target = max(5, 100 - exam_target - project_target)
        st.caption(f"Target % homework: {homework_target}")
        scenario_view = st.radio(
            "Chart Scenario",
            ("Baseline", "Shift", "Strategy"),
            horizontal=False,
        )

    shift_result: Dict[str, object]
    if task_options and selected_task != "(no peak tasks)":
        shift_result = simulate_shift(result, selected_task, int(shift_days))
    else:
        shift_result = {"error": "task_not_found"}

    strategy_result = strategy_simulation(
        result,
        {
            "exam_prep": float(exam_target),
            "projects": float(project_target),
            "homework": float(homework_target),
        },
    )

    active_stress_by_week = base_stress_score_by_week
    active_risk_by_week = base_risk_by_week
    if scenario_view == "Shift" and isinstance(shift_result, dict) and "error" not in shift_result:
        active_weekly_metrics = shift_result.get("weekly_metrics_after", {})
        if isinstance(active_weekly_metrics, dict):
            active_stress_by_week, active_risk_by_week = _weekly_metrics_to_stress_risk(active_weekly_metrics)
    elif scenario_view == "Strategy" and isinstance(strategy_result, dict) and "error" not in strategy_result:
        active_weekly_metrics = strategy_result.get("weekly_metrics_after", {})
        if isinstance(active_weekly_metrics, dict):
            active_stress_by_week, active_risk_by_week = _weekly_metrics_to_stress_risk(active_weekly_metrics)

    ai_intelligence = call_ai_intelligence(
        engine_summary,
        metrics=result,
        simulation_results={
            "shift": shift_result,
            "strategy": strategy_result,
            "active_scenario": scenario_view,
        },
    )

    _render_kpis(weekly_plan, active_stress_by_week, active_risk_by_week, study_guide)
    chart_col_1, chart_col_2 = st.columns(2, gap="large")
    with chart_col_1:
        render_workload_chart(active_stress_by_week, active_risk_by_week)
    with chart_col_2:
        render_grading_chart(study_guide)
    _render_peak_breakdown(peak_contributors, str(engine_summary.get("peak_week") or "N/A"))
    _render_simulation_results(shift_result, strategy_result)
    _render_ai_insight_panel(weekly_plan, active_stress_by_week, active_risk_by_week, study_guide)
    _render_ai_intelligence_card(ai_intelligence)
    _render_ai_strategy_card(weekly_plan, active_stress_by_week, active_risk_by_week, study_guide)
    _render_raw_outputs(weekly_plan, study_guide)


if __name__ == "__main__":
    main()
