#!/usr/bin/env python3
"""
Shared configuration for the AI Restyle Benchmark pipeline.

All paths are computed relative to this file's location (the project root).
Environment variables override defaults where applicable.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

RESULTS_DIR = PROJECT_ROOT / "results"
RUNS_DIR = PROJECT_ROOT / "runs"
REPORTS_DIR = PROJECT_ROOT / "reports"
LT_DEMO_DIR = PROJECT_ROOT / "lt_demo"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
RUBRICS_DIR = PROJECT_ROOT / "rubrics"
AGENTS_DIR = PROJECT_ROOT / "agents"
EXAMPLES_DIR = PROJECT_ROOT / "examples"

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------
STYLE_ASSERTIONS_PATH = PROJECT_ROOT / "rubrics" / "style_assertions.json"
STYLE_DEFINITIONS_PATH = PROJECT_ROOT / "rubrics" / "style_definitions.json"
ACRUE_V3_PROMPT_PATH = PROJECT_ROOT / "rubrics" / "acrue_v3_prompt.md"
RUN_SPEC_PATH = PROJECT_ROOT / "run_spec.json"
AUTH_STATE_PATH = PROJECT_ROOT / "auth_state.json"
EXCEL_PATH = PROJECT_ROOT / "ai_restyle_benchmark.xlsx"

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# ACRUE v3 constants
# ---------------------------------------------------------------------------
WEIGHTS = {
    "accuracy": 1.0,
    "completeness": 1.0,
    "relevance": 0.5,
    "usefulness": 0.5,
    "exceptional": 2.0,
}

MAX_SCORE = 25.0

GRADE_THRESHOLDS = {
    "A+": 90,
    "A": 80,
    "B": 70,
    "C": 60,
    "F": 0,
}

# ---------------------------------------------------------------------------
# Style presets
# ---------------------------------------------------------------------------
STYLE_PRESETS = [
    "Movie Poster", "Plush Toy", "Anime", "Chibi Sticker", "Caricature",
    "Superhero", "Toy Model", "Graffiti", "Crochet Art", "Doodle",
    "Pencil Portrait", "Storybook", "Photo Booth", "Pop Art",
]


def get_grade(percentage: float) -> str:
    """Return letter grade for a percentage score."""
    for grade, threshold in GRADE_THRESHOLDS.items():
        if percentage >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("AI Restyle Benchmark - config.py")
    print(f"  PROJECT_ROOT:          {PROJECT_ROOT}")
    print(f"  RESULTS_DIR:           {RESULTS_DIR}")
    print(f"  RUNS_DIR:              {RUNS_DIR}")
    print(f"  REPORTS_DIR:           {REPORTS_DIR}")
    print(f"  LT_DEMO_DIR:          {LT_DEMO_DIR}")
    print(f"  SCREENSHOTS_DIR:       {SCREENSHOTS_DIR}")
    print(f"  RUBRICS_DIR:           {RUBRICS_DIR}")
    print(f"  AGENTS_DIR:            {AGENTS_DIR}")
    print(f"  EXAMPLES_DIR:          {EXAMPLES_DIR}")
    print(f"  STYLE_ASSERTIONS_PATH: {STYLE_ASSERTIONS_PATH}")
    print(f"  STYLE_DEFINITIONS_PATH:{STYLE_DEFINITIONS_PATH}")
    print(f"  ACRUE_V3_PROMPT_PATH:  {ACRUE_V3_PROMPT_PATH}")
    print(f"  RUN_SPEC_PATH:         {RUN_SPEC_PATH}")
    print(f"  AUTH_STATE_PATH:       {AUTH_STATE_PATH}")
    print(f"  EXCEL_PATH:            {EXCEL_PATH}")
    print(f"  GEMINI_API_KEY:        {'(set)' if GEMINI_API_KEY else '(not set)'}")
    print(f"  GEMINI_MODEL:          {GEMINI_MODEL}")
    print(f"  ANTHROPIC_API_KEY:     {'(set)' if ANTHROPIC_API_KEY else '(not set)'}")
    print(f"  MAX_SCORE:             {MAX_SCORE}")
    print(f"  WEIGHTS:               {WEIGHTS}")
    print("All paths resolved OK.")
