#!/usr/bin/env python3
"""
ACRUE v3 Hybrid Evaluation Script for AI Restyle

Evaluates AI-restyled images using the ACRUE v3 hybrid framework which combines:
- Yes/No assertions for grounded binary checks
- 1-5 confidence scores for nuanced quality assessment

Uses Google Gemini 2.0 Flash for LLM-as-Judge evaluation.

Usage:
    # Single evaluation
    python run_acrue_v3.py --original photo.jpg --restyled styled.png --style "Storybook"

    # Plan-only mode (shows assertions without running)
    python run_acrue_v3.py --original photo.jpg --restyled styled.png --style "Storybook" --plan-only

    # Batch evaluation
    python run_acrue_v3.py --batch batch_config.json

    # Generate report after evaluation
    python run_acrue_v3.py --original photo.jpg --restyled styled.png --style "Storybook" --report
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


# ACRUE v3 dimension weights
WEIGHTS = {
    "accuracy": 1.0,
    "completeness": 1.0,
    "relevance": 0.5,
    "usefulness": 0.5,
    "exceptional": 2.0
}

MAX_SCORE = 25.0


def load_style_assertions() -> dict:
    """Load style-specific assertions from JSON file."""
    assertions_path = Path(__file__).parent / "style_assertions.json"

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

    # Return generic assertions if style not found
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
    """Display the evaluation plan for user review."""
    assertions = style_data.get("assertions", {})
    description = style_data.get("description", "")

    total_assertions = sum(len(a) for a in assertions.values())

    print("\n" + "=" * 70)
    print(f"         ACRUE v3 HYBRID EVALUATION PLAN: {style_name.upper()}")
    print("=" * 70)
    print(f"\nStyle Description: {description}")
    print("\n" + "-" * 70)
    print("SCORING MODEL: Hybrid (Assertions + Confidence)")
    print("-" * 70)
    print("Each assertion is answered with:")
    print("  - Yes/No binary answer (grounding)")
    print("  - 1-5 confidence score (nuance)")
    print("  - Evidence supporting the answer")
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


def get_grade(percentage: float) -> str:
    """Get letter grade from percentage."""
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


def load_evaluation_prompt(style_name: str, style_data: dict) -> str:
    """Load and populate the ACRUE v3 evaluation prompt template."""
    prompt_path = Path(__file__).parent / "acrue_v3_prompt.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"ACRUE v3 prompt not found at: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()

    # Replace style placeholders
    prompt = prompt.replace("{STYLE_NAME}", style_name)
    prompt = prompt.replace("{STYLE_DESCRIPTION}", style_data.get("description", ""))

    # Inject assertions for each dimension
    assertions = style_data.get("assertions", {})
    for dim_key in ["accuracy", "completeness", "relevance", "usefulness", "exceptional"]:
        dim_assertions = assertions.get(dim_key, [])
        prefix = dim_key[0].upper()  # A, C, R, U, E
        formatted = format_assertions_for_prompt(dim_assertions, prefix)
        prompt = prompt.replace(f"{{ASSERTIONS_{dim_key.upper()}}}", formatted)

    return prompt


def calculate_v3_scores(dimensions_data: dict) -> dict:
    """Calculate weighted scores from ACRUE v3 response."""
    result = {}

    for dimension, weight in WEIGHTS.items():
        dim_data = dimensions_data.get(dimension, {})

        passed = dim_data.get("passed", 0)
        total = dim_data.get("total", 1)
        avg_confidence = dim_data.get("avg_confidence", 0)
        dimension_score = dim_data.get("dimension_score", 0)

        # Weighted score = dimension_score * weight
        weighted_score = dimension_score * weight

        result[dimension] = {
            "weight": weight,
            "passed": passed,
            "total": total,
            "pass_rate": f"{passed}/{total}",
            "avg_confidence": round(avg_confidence, 2),
            "dimension_score": round(dimension_score, 2),
            "weighted_score": round(weighted_score, 2),
            "assertions": dim_data.get("assertions", [])
        }

    return result


def calculate_v3_summary(scores: dict) -> dict:
    """Calculate final summary for ACRUE v3 results."""
    weighted_total = sum(s.get("weighted_score", 0) for s in scores.values())
    percentage = (weighted_total / MAX_SCORE) * 100

    total_passed = sum(s.get("passed", 0) for s in scores.values())
    total_assertions = sum(s.get("total", 0) for s in scores.values())

    # Calculate overall average confidence
    all_confidences = []
    for dim_data in scores.values():
        for assertion in dim_data.get("assertions", []):
            if isinstance(assertion, dict) and "confidence" in assertion:
                all_confidences.append(assertion["confidence"])

    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

    return {
        "total_assertions": total_assertions,
        "total_passed": total_passed,
        "overall_pass_rate": f"{total_passed}/{total_assertions}",
        "overall_avg_confidence": round(avg_confidence, 2),
        "weighted_total": round(weighted_total, 2),
        "max_score": MAX_SCORE,
        "percentage": round(percentage, 1),
        "grade": get_grade(percentage)
    }


def evaluate_images(
    original_path: str,
    restyled_path: str,
    style_name: str,
    api_key: str = None,
    plan_only: bool = False
) -> dict:
    """
    Evaluate a restyled image using ACRUE v3 hybrid framework.

    Args:
        original_path: Path to the original image
        restyled_path: Path to the restyled image
        style_name: Name of the style applied (e.g., "Storybook")
        api_key: Gemini API key (uses env var if not provided)
        plan_only: If True, only display the evaluation plan without running

    Returns:
        dict: Complete evaluation results with ACRUE v3 scores
    """
    # Validate image paths
    if not Path(original_path).exists():
        raise FileNotFoundError(f"Original image not found: {original_path}")
    if not Path(restyled_path).exists():
        raise FileNotFoundError(f"Restyled image not found: {restyled_path}")

    # Get style assertions
    style_data = get_style_assertions(style_name)

    # Display evaluation plan
    display_evaluation_plan(style_name, style_data)

    if plan_only:
        return {
            "evaluation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "original_image": str(original_path),
            "restyled_image": str(restyled_path),
            "style": style_name,
            "rubric_version": "acrue-v3",
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
    model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))

    # Load evaluation prompt
    evaluation_prompt = load_evaluation_prompt(style_name, style_data)

    print("\nUsing ACRUE v3 (Hybrid: Assertions + Confidence) rubric...")

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
        return {
            "evaluation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "original_image": str(original_path),
            "restyled_image": str(restyled_path),
            "style": style_name,
            "rubric_version": "acrue-v3",
            "error": f"Failed to parse response: {str(e)}",
            "raw_response": response_text[:1000]
        }

    # Calculate scores from dimensions data
    dimensions_data = gemini_response.get("dimensions", {})
    calculated_scores = calculate_v3_scores(dimensions_data)
    summary = calculate_v3_summary(calculated_scores)

    # Build final result
    result = {
        "evaluation_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "original_image": str(Path(original_path).absolute()),
        "restyled_image": str(Path(restyled_path).absolute()),
        "style": style_name,
        "rubric_version": "acrue-v3",
        "dimensions": calculated_scores,
        "summary": summary,
        "overall_assessment": gemini_response.get("summary", "")
    }

    return result


def save_results(results: dict, output_path: str = None) -> str:
    """Save evaluation results to JSON file."""
    if output_path is None:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        output_path = results_dir / "acrue_v3_scores.json"

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
    """Print a formatted summary of the ACRUE v3 evaluation results."""
    # Check if plan-only
    if results.get("plan_only"):
        print("\n[Plan-only mode - evaluation not executed]")
        return

    # Check for errors
    if "error" in results:
        print(f"\nError: {results['error']}")
        return

    print("\n" + "=" * 75)
    print("               ACRUE v3 HYBRID EVALUATION RESULTS")
    print("=" * 75)
    print(f"Style: {results.get('style', 'Unknown')}")
    print(f"Rubric: ACRUE v3 (Hybrid: Assertions + Confidence)")
    print(f"Evaluation ID: {results.get('evaluation_id', 'N/A')}")
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")

    dimensions = results.get("dimensions", {})

    print("\n" + "-" * 75)
    print("ASSERTION RESULTS BY DIMENSION")
    print("-" * 75)

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
        dim_data = dimensions.get(dim_key, {})
        pass_rate = dim_data.get("pass_rate", "0/0")
        avg_conf = dim_data.get("avg_confidence", 0)
        assertions = dim_data.get("assertions", [])

        print(f"\n{dim_name}: {pass_rate} passed | Avg Confidence: {avg_conf}/5")

        for i, assertion in enumerate(assertions, 1):
            if isinstance(assertion, dict):
                question = assertion.get("question", "")
                answer = assertion.get("answer", "")
                confidence = assertion.get("confidence", 0)
                evidence = assertion.get("evidence", "")

                marker = "Y" if answer.lower() == "yes" else "N"
                # Use ASCII characters for Windows compatibility
                conf_bar = "#" * confidence + "-" * (5 - confidence)

                # Truncate question for display
                q_display = question[:45] + "..." if len(question) > 45 else question
                print(f"  {prefixes[dim_key]}{i}. [{marker}] {conf_bar} {q_display}")
                if evidence:
                    ev_display = evidence[:65] + "..." if len(evidence) > 65 else evidence
                    print(f"       -> {ev_display}")

    print("\n" + "-" * 75)
    print("SCORE BREAKDOWN")
    print("-" * 75)
    print(f"{'Dimension':<15} {'Passed':>8} {'Conf':>8} {'Score':>8} {'Weight':>8} {'Weighted':>10}")
    print(f"{'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for dim_key, dim_name in dimension_names.items():
        dim_data = dimensions.get(dim_key, {})
        pass_rate = dim_data.get("pass_rate", "0/0")
        avg_conf = dim_data.get("avg_confidence", 0)
        dim_score = dim_data.get("dimension_score", 0)
        weight = dim_data.get("weight", 0)
        weighted = dim_data.get("weighted_score", 0)

        print(f"{dim_key.capitalize():<15} {pass_rate:>8} {avg_conf:>6}/5 {dim_score:>6}/5 {weight:>8.1f} {weighted:>10.2f}")

    print("-" * 75)

    summary = results.get("summary", {})
    print(f"\nFINAL RESULT")
    print(f"  Assertions:       {summary.get('overall_pass_rate', 'N/A')} passed")
    print(f"  Avg Confidence:   {summary.get('overall_avg_confidence', 0)}/5")
    print(f"  Weighted Score:   {summary.get('weighted_total', 0):.2f} / {summary.get('max_score', 25):.1f}")
    print(f"  Percentage:       {summary.get('percentage', 0):.1f}%")
    print(f"  Grade:            {summary.get('grade', 'N/A')}")

    assessment = results.get("overall_assessment", "")
    if assessment:
        print(f"\nSummary:\n  {assessment}")

    print("=" * 75 + "\n")


def run_batch_evaluation(
    config_path: str,
    api_key: str = None
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
                api_key=api_key
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
        description="Evaluate AI-restyled images using the ACRUE v3 hybrid framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single evaluation
  python run_acrue_v3.py -o photo.jpg -r styled.png -s "Storybook"

  # Show evaluation plan only (don't run)
  python run_acrue_v3.py -o photo.jpg -r styled.png -s "Storybook" --plan-only

  # Batch evaluation
  python run_acrue_v3.py --batch batch_config.json
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
        help="Output path for results JSON (default: restyle_tests/results/acrue_v3_scores.json)"
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key (default: uses GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Display evaluation plan without running the evaluation"
    )

    args = parser.parse_args()

    # Set default output path
    if args.output is None:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        args.output = str(results_dir / "acrue_v3_scores.json")

    # Validate arguments
    if args.batch:
        # Batch mode
        results = run_batch_evaluation(args.batch, args.api_key)
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
            plan_only=args.plan_only
        )

        print_results_summary(result)

        if not result.get("plan_only"):
            save_results(result, args.output)


if __name__ == "__main__":
    main()
