#!/usr/bin/env python3
"""
ACRUE Image Evaluation Script for AI Restyle

Evaluates AI-restyled images against original inputs using the ACRUE rubric framework
specifically designed for style transfer evaluation (not pixel-level comparison).

Supports two versions:
- ACRUE v1: Direct rubric scoring (legacy)
- ACRUE v2: Assertion-backed scoring (default) - reduces hallucination with Yes/No grounding

Uses Google Gemini 2.0 Flash for LLM-as-Judge evaluation.

Usage:
    # v2 (assertion-backed, default)
    python run_acrue_eval.py --original path/to/original.jpg --restyled path/to/restyled.jpg --style "Storybook"

    # v2 with plan-only mode (shows eval plan, doesn't run)
    python run_acrue_eval.py --original img.jpg --restyled img_styled.jpg --style "Storybook" --plan-only

    # v1 (legacy rubric)
    python run_acrue_eval.py --original img.jpg --restyled img_styled.jpg --style "Anime" --legacy

    # Batch evaluation
    python run_acrue_eval.py --batch path/to/batch_config.json
"""

import argparse
import base64
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai package not installed.")
    print("Install with: pip install google-generativeai")
    sys.exit(1)


# ACRUE weights
WEIGHTS = {
    "accuracy": 1.0,
    "completeness": 1.0,
    "relevance": 0.5,
    "usefulness": 0.5,
    "exceptional_value": 2.0,
    # v2 uses "exceptional" key
    "exceptional": 2.0
}


def load_style_definitions() -> dict:
    """Load style definitions for context injection."""
    style_path = Path(__file__).parent / "rubrics" / "style_definitions.json"

    if not style_path.exists():
        return {"styles": {}, "default_context": {}}

    with open(style_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_style_assertions() -> dict:
    """Load style-specific assertions for ACRUE v2."""
    assertions_path = Path(__file__).parent / "rubrics" / "style_assertions.json"

    if not assertions_path.exists():
        return {"styles": {}}

    with open(assertions_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_style_assertions(style_name: str) -> dict:
    """Get assertions for a specific style.

    Returns:
        dict with keys: description, assertions (accuracy, completeness, relevance, usefulness, exceptional)
    """
    data = load_style_assertions()
    styles = data.get("styles", {})

    # Case-insensitive lookup
    for key, value in styles.items():
        if key.lower() == style_name.lower():
            return value

    # Return empty if not found
    return {
        "description": f"Generic evaluation for {style_name} style",
        "assertions": {
            "accuracy": [
                "Is the subject recognizable as the same person/scene from the original?",
                "Does the output authentically represent the target style?",
                "Are pose, framing, and spatial relationships preserved?",
                "Are style-appropriate elements tasteful and not distracting?",
                "Does the rendering match professional quality for this style?"
            ],
            "completeness": [
                "Is the style applied to the entire image (no untransformed patches)?",
                "Does the background complement the styled subject?",
                "Are all subjects structurally intact (no broken limbs, warped faces)?",
                "Is the style saturation appropriate (not too subtle, not overdone)?",
                "Are all elements stylistically consistent?"
            ],
            "relevance": [
                "Does the output clearly represent the requested style?",
                "Does the emotional tone fit the style expectation?",
                "Does the mood align with what users expect from this style?",
                "Does it avoid elements inconsistent with the style?"
            ],
            "usefulness": [
                "Would this be suitable for sharing on social media?",
                "Is the image free of obvious digital artifacts or glitches?",
                "Is the subject clearly visible and recognizable?",
                "Is the resolution sufficient for intended use?"
            ],
            "exceptional": [
                "Does it look like professional work in this style?",
                "Does the transformation add artistic value to the original?",
                "Would users be excited to share this?",
                "Does it have standout quality compared to typical AI outputs?",
                "Does it evoke the intended emotional response?"
            ]
        }
    }


def format_assertions_for_prompt(assertions: list, prefix: str) -> str:
    """Format assertions as numbered list for prompt injection."""
    lines = []
    for i, assertion in enumerate(assertions, 1):
        lines.append(f"{prefix}{i}. {assertion}")
    return "\n".join(lines)


def display_evaluation_plan(style_name: str, style_data: dict) -> None:
    """Display the evaluation plan for user confirmation."""
    assertions = style_data.get("assertions", {})
    description = style_data.get("description", "")

    total_assertions = sum(len(a) for a in assertions.values())

    print("\n" + "=" * 70)
    print(f"         ACRUE v2 EVALUATION PLAN: {style_name.upper()}")
    print("=" * 70)
    print(f"\nStyle Description: {description}")
    print("\n" + "-" * 70)
    print("WEIGHTS (Max Score: 25.0)")
    print("-" * 70)
    print(f"  {'Dimension':<20} {'Weight':>10} {'Max Points':>15}")
    print(f"  {'-'*20} {'-'*10} {'-'*15}")
    print(f"  {'Accuracy':<20} {'1.0':>10} {'5.0':>15}")
    print(f"  {'Completeness':<20} {'1.0':>10} {'5.0':>15}")
    print(f"  {'Relevance':<20} {'0.5':>10} {'2.5':>15}")
    print(f"  {'Usefulness':<20} {'0.5':>10} {'2.5':>15}")
    print(f"  {'Exceptional':<20} {'2.0':>10} {'10.0':>15}")

    print("\n" + "-" * 70)
    print(f"ASSERTIONS ({total_assertions} total)")
    print("-" * 70)

    dimension_names = {
        "accuracy": "A - Accuracy",
        "completeness": "C - Completeness",
        "relevance": "R - Relevance",
        "usefulness": "U - Usefulness",
        "exceptional": "E - Exceptional"
    }

    prefixes = {
        "accuracy": "A",
        "completeness": "C",
        "relevance": "R",
        "usefulness": "U",
        "exceptional": "E"
    }

    for dim_key, dim_name in dimension_names.items():
        dim_assertions = assertions.get(dim_key, [])
        print(f"\n{dim_name} ({len(dim_assertions)} assertions)")
        for i, assertion in enumerate(dim_assertions, 1):
            print(f"  {prefixes[dim_key]}{i}. {assertion}")

    print("\n" + "=" * 70)


def get_style_context(style_name: str) -> str:
    """Get style-specific evaluation context for the prompt."""
    definitions = load_style_definitions()
    styles = definitions.get("styles", {})
    default = definitions.get("default_context", {})

    # Find the style (case-insensitive match)
    style_data = None
    for key, value in styles.items():
        if key.lower() == style_name.lower():
            style_data = value
            break

    if not style_data:
        style_data = default

    # Build context string
    context_parts = []

    if style_data.get("description"):
        context_parts.append(f"**Style Description:** {style_data['description']}")

    if style_data.get("expected_transformations"):
        context_parts.append("\n**Expected Transformations (DO expect these changes):**")
        for item in style_data["expected_transformations"]:
            context_parts.append(f"- {item}")

    if style_data.get("acceptable_additions"):
        context_parts.append("\n**Acceptable Style Additions (DO NOT penalize these):**")
        for item in style_data["acceptable_additions"]:
            context_parts.append(f"- {item}")

    if style_data.get("quality_indicators"):
        context_parts.append("\n**Quality Indicators (Ask yourself):**")
        for item in style_data["quality_indicators"]:
            context_parts.append(f"- {item}")

    if style_data.get("common_issues_to_avoid"):
        context_parts.append("\n**Common Issues to Watch For:**")
        for item in style_data["common_issues_to_avoid"]:
            context_parts.append(f"- {item}")

    return "\n".join(context_parts)

# Grade thresholds
def get_grade(percentage: float) -> str:
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    else:
        return "F"


def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime_type(image_path: str) -> str:
    """Get MIME type based on file extension."""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp"
    }
    return mime_types.get(ext, "image/jpeg")


def load_evaluation_prompt(style_name: str, use_legacy: bool = False, use_v2: bool = False) -> str:
    """Load the ACRUE evaluation prompt template.

    Args:
        style_name: The style being evaluated
        use_legacy: If True, use the original generic rubric (v1)
        use_v2: If True, use assertion-backed ACRUE v2 prompt

    Returns:
        The evaluation prompt with style context injected
    """
    # Choose prompt file based on mode
    if use_legacy:
        prompt_file = "acrue_evaluation_prompt.md"
    elif use_v2:
        prompt_file = "acrue_restyle_prompt_v2.md"
    else:
        prompt_file = "acrue_restyle_prompt.md"

    prompt_path = Path(__file__).parent / "rubrics" / prompt_file

    # Fall back to v1 restyle if v2 doesn't exist
    if use_v2 and not prompt_path.exists():
        prompt_path = Path(__file__).parent / "rubrics" / "acrue_restyle_prompt.md"
        use_v2 = False

    # Fall back to legacy if new prompt doesn't exist
    if not prompt_path.exists():
        prompt_path = Path(__file__).parent / "rubrics" / "acrue_evaluation_prompt.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Evaluation prompt not found at: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()

    # Replace style placeholder
    prompt = prompt.replace("{STYLE_NAME}", style_name)

    # For v2: inject style-specific assertions
    if use_v2:
        style_data = get_style_assertions(style_name)
        assertions = style_data.get("assertions", {})
        description = style_data.get("description", "")

        # Inject style description
        prompt = prompt.replace("{STYLE_DESCRIPTION}", description)

        # Inject assertions for each dimension
        for dim_key in ["accuracy", "completeness", "relevance", "usefulness", "exceptional"]:
            dim_assertions = assertions.get(dim_key, [])
            prefix = dim_key[0].upper()  # A, C, R, U, E
            formatted = format_assertions_for_prompt(dim_assertions, prefix)
            prompt = prompt.replace(f"{{ASSERTIONS_{dim_key.upper()}}}", formatted)
            prompt = prompt.replace(f"{{{dim_key.upper()}_COUNT}}", str(len(dim_assertions)))

        # Calculate total assertions
        total = sum(len(a) for a in assertions.values())
        prompt = prompt.replace("{TOTAL_ASSERTIONS}", str(total))

    # Inject style-specific context (for v1 restyle prompt)
    elif not use_legacy and "{STYLE_CONTEXT}" in prompt:
        style_context = get_style_context(style_name)
        prompt = prompt.replace("{STYLE_CONTEXT}", style_context)
    else:
        # Remove placeholder if not using style context
        prompt = prompt.replace("{STYLE_CONTEXT}", "")

    return prompt


def calculate_dimension_scores(scores_data: dict) -> dict:
    """Calculate dimension averages and weighted scores (v1 format)."""
    result = {}

    for dimension, weight in WEIGHTS.items():
        if dimension == "exceptional":
            continue  # Skip duplicate key
        dim_data = scores_data.get(dimension, {})
        sub_scores = dim_data.get("sub_scores", {})

        if sub_scores:
            # Calculate average of sub-scores
            score_values = [s.get("score", 0) for s in sub_scores.values()]
            dimension_score = sum(score_values) / len(score_values) if score_values else 0
        else:
            dimension_score = 0

        result[dimension] = {
            "weight": weight,
            "sub_scores": sub_scores,
            "dimension_score": round(dimension_score, 2),
            "weighted_score": round(dimension_score * weight, 2)
        }

    return result


def calculate_v2_scores(assertions_data: dict) -> dict:
    """Calculate scores from ACRUE v2 assertion-backed response."""
    result = {}

    dimension_weights = {
        "accuracy": 1.0,
        "completeness": 1.0,
        "relevance": 0.5,
        "usefulness": 0.5,
        "exceptional": 2.0
    }

    for dimension, weight in dimension_weights.items():
        dim_data = assertions_data.get(dimension, {})

        # Get assertion results
        assertion_results = dim_data.get("results", [])
        pass_rate_str = dim_data.get("pass_rate", "0/0")
        score = dim_data.get("score", 0)
        reason = dim_data.get("reason", "")

        # Parse pass rate
        try:
            passed, total = pass_rate_str.split("/")
            passed = int(passed)
            total = int(total)
        except (ValueError, AttributeError):
            passed = 0
            total = len(assertion_results)

        result[dimension] = {
            "weight": weight,
            "assertions": assertion_results,
            "passed": passed,
            "total": total,
            "pass_rate": pass_rate_str,
            "dimension_score": score,
            "weighted_score": round(score * weight, 2),
            "reason": reason
        }

    return result


def calculate_v2_summary(scores: dict) -> dict:
    """Calculate final summary for ACRUE v2 results."""
    weighted_total = sum(s.get("weighted_score", 0) for s in scores.values())
    max_score = 25.0
    percentage = (weighted_total / max_score) * 100

    total_passed = sum(s.get("passed", 0) for s in scores.values())
    total_assertions = sum(s.get("total", 0) for s in scores.values())

    return {
        "total_assertions": total_assertions,
        "total_passed": total_passed,
        "overall_pass_rate": f"{total_passed}/{total_assertions}",
        "weighted_total": round(weighted_total, 2),
        "max_score": max_score,
        "percentage": round(percentage, 1),
        "grade": get_grade(percentage)
    }


def calculate_summary(scores: dict) -> dict:
    """Calculate final summary with weighted total and grade."""
    weighted_total = sum(s.get("weighted_score", 0) for s in scores.values())
    max_score = 25.0
    percentage = (weighted_total / max_score) * 100

    return {
        "weighted_total": round(weighted_total, 2),
        "max_score": max_score,
        "percentage": round(percentage, 1),
        "grade": get_grade(percentage)
    }


def evaluate_images(
    original_path: str,
    restyled_path: str,
    style_name: str,
    api_key: str = None,
    use_legacy: bool = False,
    use_v2: bool = True,
    plan_only: bool = False
) -> dict:
    """
    Evaluate a restyled image against its original using Gemini.

    Args:
        original_path: Path to the original image
        restyled_path: Path to the restyled image
        style_name: Name of the style applied (e.g., "Storybook")
        api_key: Gemini API key (uses env var if not provided)
        use_legacy: If True, use the original generic rubric (v1)
        use_v2: If True, use assertion-backed ACRUE v2 (default)
        plan_only: If True, only display the evaluation plan without running

    Returns:
        dict: Complete evaluation results with ACRUE scores
    """
    # Validate image paths
    if not Path(original_path).exists():
        raise FileNotFoundError(f"Original image not found: {original_path}")
    if not Path(restyled_path).exists():
        raise FileNotFoundError(f"Restyled image not found: {restyled_path}")

    # For v2, display evaluation plan
    if use_v2 and not use_legacy:
        style_data = get_style_assertions(style_name)
        display_evaluation_plan(style_name, style_data)

        if plan_only:
            return {
                "evaluation_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "original_image": str(original_path),
                "restyled_image": str(restyled_path),
                "style": style_name,
                "rubric_version": "acrue-v2",
                "plan_only": True,
                "style_data": style_data
            }

    # Get API key
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Set it as an environment variable or pass via --api-key"
        )

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Load evaluation prompt
    evaluation_prompt = load_evaluation_prompt(style_name, use_legacy=use_legacy, use_v2=use_v2)

    if use_legacy:
        rubric_type = "legacy (generic)"
    elif use_v2:
        rubric_type = "ACRUE v2 (assertion-backed)"
    else:
        rubric_type = "restyle-optimized v1"

    print(f"Using {rubric_type} rubric...")

    # Prepare images for Gemini
    original_data = encode_image_to_base64(original_path)
    restyled_data = encode_image_to_base64(restyled_path)

    original_mime = get_mime_type(original_path)
    restyled_mime = get_mime_type(restyled_path)

    # Build the prompt with images
    content = [
        "I am providing you with two images for evaluation:",
        "\n\n**IMAGE 1 - ORIGINAL IMAGE:**\n",
        {
            "mime_type": original_mime,
            "data": original_data
        },
        "\n\n**IMAGE 2 - RESTYLED IMAGE (Style: " + style_name + "):**\n",
        {
            "mime_type": restyled_mime,
            "data": restyled_data
        },
        "\n\n---\n\n",
        evaluation_prompt,
        "\n\nNow evaluate the restyled image and respond with ONLY the JSON output as specified above."
    ]

    # Call Gemini
    print(f"Calling Gemini 2.0 Flash to evaluate {style_name} style...")
    response = model.generate_content(content)

    # Parse response
    response_text = response.text.strip()

    # Extract JSON from response (handle markdown code blocks)
    if response_text.startswith("```"):
        # Remove markdown code block
        lines = response_text.split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.startswith("```json"):
                in_json = True
                continue
            elif line.startswith("```"):
                in_json = False
                continue
            if in_json:
                json_lines.append(line)
        response_text = "\n".join(json_lines)

    try:
        gemini_response = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse Gemini response as JSON: {e}")
        print(f"Raw response:\n{response_text[:500]}...")
        # Return error result
        return {
            "evaluation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "original_image": str(original_path),
            "restyled_image": str(restyled_path),
            "style": style_name,
            "error": f"Failed to parse response: {str(e)}",
            "raw_response": response_text[:1000]
        }

    # Calculate scores based on version
    if use_v2 and not use_legacy:
        # ACRUE v2: assertion-backed
        assertions_data = gemini_response.get("assertions", {})
        calculated_scores = calculate_v2_scores(assertions_data)
        summary = calculate_v2_summary(calculated_scores)
        rubric_version = "acrue-v2"
    else:
        # ACRUE v1: direct scoring
        scores_data = gemini_response.get("scores", {})
        calculated_scores = calculate_dimension_scores(scores_data)
        summary = calculate_summary(calculated_scores)
        rubric_version = "legacy" if use_legacy else "restyle-v1"

    # Build final result
    result = {
        "evaluation_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "original_image": str(Path(original_path).absolute()),
        "restyled_image": str(Path(restyled_path).absolute()),
        "style": style_name,
        "rubric_version": rubric_version,
        "scores": calculated_scores,
        "summary": summary,
        "overall_assessment": gemini_response.get("overall_assessment", "")
    }

    return result


def save_results(results: dict, output_path: str = None) -> str:
    """Save evaluation results to JSON file."""
    if output_path is None:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        output_path = results_dir / "acrue_scores.json"

    output_path = Path(output_path)

    # Load existing results if file exists
    existing_results = []
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing_results = data
                else:
                    existing_results = [data]
        except (json.JSONDecodeError, IOError):
            existing_results = []

    # Append new result
    existing_results.append(results)

    # Save updated results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing_results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_path}")
    return str(output_path)


def print_results_summary(results: dict):
    """Print a formatted summary of the evaluation results."""
    # Check if plan-only
    if results.get("plan_only"):
        print("\n[Plan-only mode - evaluation not executed]")
        return

    rubric = results.get('rubric_version', 'unknown')

    # Use v2 display for ACRUE v2
    if rubric == "acrue-v2":
        print_v2_results(results)
        return

    # v1 display
    print("\n" + "="*60)
    print("ACRUE EVALUATION RESULTS")
    print("="*60)
    print(f"Style: {results.get('style', 'Unknown')}")
    rubric_display = "Restyle-Optimized v1" if rubric == "restyle-v1" else "Legacy (Generic)"
    print(f"Rubric: {rubric_display}")
    print(f"Evaluation ID: {results.get('evaluation_id', 'N/A')}")
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")
    print("-"*60)

    scores = results.get("scores", {})

    print("\nDimension Scores:")
    print("-"*40)
    for dimension, data in scores.items():
        dim_score = data.get("dimension_score", 0)
        weighted = data.get("weighted_score", 0)
        weight = data.get("weight", 0)
        print(f"  {dimension.upper():<20} {dim_score:.1f}/5.0  (×{weight} = {weighted:.2f})")

    print("-"*40)

    summary = results.get("summary", {})
    print(f"\nWEIGHTED TOTAL: {summary.get('weighted_total', 0):.2f} / {summary.get('max_score', 25):.1f}")
    print(f"PERCENTAGE: {summary.get('percentage', 0):.1f}%")
    print(f"GRADE: {summary.get('grade', 'N/A')}")

    assessment = results.get("overall_assessment", "")
    if assessment:
        print(f"\nOverall Assessment:\n{assessment}")

    print("="*60 + "\n")


def print_v2_results(results: dict):
    """Print formatted ACRUE v2 results with assertion details."""
    print("\n" + "=" * 70)
    print("            ACRUE v2 EVALUATION RESULTS")
    print("=" * 70)
    print(f"Style: {results.get('style', 'Unknown')}")
    print(f"Rubric: ACRUE v2 (Assertion-Backed)")
    print(f"Evaluation ID: {results.get('evaluation_id', 'N/A')}")
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")

    scores = results.get("scores", {})

    print("\n" + "-" * 70)
    print("ASSERTION RESULTS")
    print("-" * 70)

    dimension_names = {
        "accuracy": "A - Accuracy",
        "completeness": "C - Completeness",
        "relevance": "R - Relevance",
        "usefulness": "U - Usefulness",
        "exceptional": "E - Exceptional"
    }

    prefixes = {
        "accuracy": "A",
        "completeness": "C",
        "relevance": "R",
        "usefulness": "U",
        "exceptional": "E"
    }

    for dim_key, dim_name in dimension_names.items():
        dim_data = scores.get(dim_key, {})
        pass_rate = dim_data.get("pass_rate", "0/0")
        assertions = dim_data.get("assertions", [])

        print(f"\n{dim_name}: {pass_rate} passed")

        for i, assertion in enumerate(assertions, 1):
            if isinstance(assertion, dict):
                question = assertion.get("question", "")
                answer = assertion.get("answer", "")
                evidence = assertion.get("evidence", "")
                marker = "Y" if answer.lower() == "yes" else "N"
                print(f"  {prefixes[dim_key]}{i}. [{marker}] {question[:50]}...")
                if evidence:
                    print(f"       -> {evidence[:60]}...")

    print("\n" + "-" * 70)
    print("DIMENSION SCORES")
    print("-" * 70)
    print(f"{'Dimension':<18} {'Passed':>10} {'Score':>8} {'Weighted':>10} {'Reason':<30}")
    print(f"{'-'*18} {'-'*10} {'-'*8} {'-'*10} {'-'*30}")

    for dim_key, dim_name in dimension_names.items():
        dim_data = scores.get(dim_key, {})
        pass_rate = dim_data.get("pass_rate", "0/0")
        score = dim_data.get("dimension_score", 0)
        weighted = dim_data.get("weighted_score", 0)
        reason = dim_data.get("reason", "")[:30]
        print(f"{dim_key.capitalize():<18} {pass_rate:>10} {score:>5}/5   {weighted:>10.2f} {reason:<30}")

    print("-" * 70)

    summary = results.get("summary", {})
    print(f"\nFINAL RESULT")
    print(f"  Total Assertions: {summary.get('overall_pass_rate', 'N/A')} passed")
    print(f"  Weighted Score:   {summary.get('weighted_total', 0):.2f} / {summary.get('max_score', 25):.1f}")
    print(f"  Percentage:       {summary.get('percentage', 0):.1f}%")
    print(f"  Grade:            {summary.get('grade', 'N/A')}")

    assessment = results.get("overall_assessment", "")
    if assessment:
        print(f"\nOverall Assessment:\n  {assessment}")

    print("=" * 70 + "\n")


def run_batch_evaluation(
    config_path: str,
    api_key: str = None,
    use_legacy: bool = False,
    use_v2: bool = True
) -> list:
    """Run batch evaluation from a configuration file."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    evaluations = config.get("evaluations", [])
    results = []

    for i, eval_config in enumerate(evaluations, 1):
        print(f"\n[{i}/{len(evaluations)}] Evaluating: {eval_config.get('style', 'Unknown')}")

        try:
            result = evaluate_images(
                original_path=eval_config["original"],
                restyled_path=eval_config["restyled"],
                style_name=eval_config["style"],
                api_key=api_key,
                use_legacy=use_legacy,
                use_v2=use_v2
            )
            results.append(result)
            print_results_summary(result)
        except Exception as e:
            print(f"  Error: {str(e)}")
            results.append({
                "error": str(e),
                "config": eval_config
            })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate AI-restyled images using the ACRUE framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ACRUE v2 (default, assertion-backed)
  python run_acrue_eval.py -o photo.jpg -r styled.png -s "Storybook"

  # Show evaluation plan only (don't run)
  python run_acrue_eval.py -o photo.jpg -r styled.png -s "Storybook" --plan-only

  # Use v1 restyle-optimized rubric
  python run_acrue_eval.py -o photo.jpg -r styled.png -s "Anime" --v1

  # Use legacy generic rubric
  python run_acrue_eval.py -o photo.jpg -r styled.png -s "Anime" --legacy

  # Batch evaluation
  python run_acrue_eval.py --batch batch_config.json
        """
    )

    parser.add_argument(
        "--original", "-o",
        help="Path to the original image"
    )
    parser.add_argument(
        "--restyled", "-r",
        help="Path to the restyled image"
    )
    parser.add_argument(
        "--style", "-s",
        help="Name of the style applied (e.g., 'Storybook', 'Neon Cyberpunk')"
    )
    parser.add_argument(
        "--batch", "-b",
        help="Path to batch configuration JSON file"
    )
    parser.add_argument(
        "--output", "-out",
        help="Output path for results JSON (default: restyle_tests/results/acrue_v2_scores.json)"
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key (default: uses GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use the original generic rubric (v0)"
    )
    parser.add_argument(
        "--v1",
        action="store_true",
        help="Use ACRUE v1 (restyle-optimized, direct scoring)"
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Display evaluation plan without running the evaluation"
    )

    args = parser.parse_args()

    # Determine rubric version
    use_legacy = args.legacy
    use_v2 = not args.v1 and not args.legacy  # Default to v2 unless --v1 or --legacy specified

    # Set default output path based on version
    if args.output is None:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        if use_v2:
            args.output = str(results_dir / "acrue_v2_scores.json")
        else:
            args.output = str(results_dir / "acrue_scores.json")

    # Validate arguments
    if args.batch:
        # Batch mode
        results = run_batch_evaluation(
            args.batch,
            args.api_key,
            use_legacy=use_legacy,
            use_v2=use_v2
        )
        for result in results:
            if "error" not in result and not result.get("plan_only"):
                save_results(result, args.output)
    else:
        # Single evaluation mode
        if not all([args.original, args.restyled, args.style]):
            parser.error("--original, --restyled, and --style are required for single evaluation")

        result = evaluate_images(
            original_path=args.original,
            restyled_path=args.restyled,
            style_name=args.style,
            api_key=args.api_key,
            use_legacy=use_legacy,
            use_v2=use_v2,
            plan_only=args.plan_only
        )

        print_results_summary(result)

        if not result.get("plan_only"):
            save_results(result, args.output)


if __name__ == "__main__":
    main()
