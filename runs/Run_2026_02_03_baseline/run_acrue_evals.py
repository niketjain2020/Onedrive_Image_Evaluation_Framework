"""
Run ACRUE v3 evaluations on all 9 restyled images using Gemini.
"""
import os
import json
import base64
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

# Configuration
RUN_DIR = os.path.dirname(os.path.abspath(__file__))
RESTYLE_TESTS_DIR = os.path.dirname(os.path.dirname(RUN_DIR))  # restyle_tests directory
STYLE_ASSERTIONS_PATH = os.path.join(RESTYLE_TESTS_DIR, "style_assertions.json")
ACRUE_PROMPT_PATH = os.path.join(RESTYLE_TESTS_DIR, "acrue_v3_prompt.md")

# Image pairs to evaluate
IMAGE_PAIRS = [
    ("img_001", "anime", "Anime"),
    ("img_001", "pop_art", "Pop Art"),
    ("img_001", "storybook", "Storybook"),
    ("img_002", "anime", "Anime"),
    ("img_002", "pop_art", "Pop Art"),
    ("img_002", "storybook", "Storybook"),
    ("img_003", "anime", "Anime"),
    ("img_003", "pop_art", "Pop Art"),
    ("img_003", "storybook", "Storybook"),
]

def load_style_assertions():
    """Load style-specific assertions from JSON."""
    with open(STYLE_ASSERTIONS_PATH, 'r') as f:
        return json.load(f)

def load_acrue_prompt():
    """Load the ACRUE v3 prompt template."""
    with open(ACRUE_PROMPT_PATH, 'r') as f:
        return f.read()

def build_prompt(style_name, assertions_data, prompt_template):
    """Build the complete ACRUE v3 prompt for a specific style."""
    style_data = assertions_data["styles"].get(style_name, {})
    description = style_data.get("description", f"{style_name} style transformation")
    assertions = style_data.get("assertions", {})

    # Format assertions for each dimension
    def format_assertions(assertion_list, prefix):
        return "\n".join([f"{prefix}{i+1}. {a}" for i, a in enumerate(assertion_list)])

    prompt = prompt_template.replace("{STYLE_NAME}", style_name)
    prompt = prompt.replace("{STYLE_DESCRIPTION}", description)
    prompt = prompt.replace("{ASSERTIONS_ACCURACY}", format_assertions(assertions.get("accuracy", []), "A"))
    prompt = prompt.replace("{ASSERTIONS_COMPLETENESS}", format_assertions(assertions.get("completeness", []), "C"))
    prompt = prompt.replace("{ASSERTIONS_RELEVANCE}", format_assertions(assertions.get("relevance", []), "R"))
    prompt = prompt.replace("{ASSERTIONS_USEFULNESS}", format_assertions(assertions.get("usefulness", []), "U"))
    prompt = prompt.replace("{ASSERTIONS_EXCEPTIONAL}", format_assertions(assertions.get("exceptional", []), "E"))

    return prompt

def load_image_as_base64(image_path):
    """Load an image and return as base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def evaluate_image(model, prompt, image_base64):
    """Call Gemini to evaluate an image."""
    import PIL.Image
    import io

    # Decode base64 to image
    image_data = base64.b64decode(image_base64)
    image = PIL.Image.open(io.BytesIO(image_data))

    # Call Gemini
    response = model.generate_content([prompt, image])

    # Extract JSON from response
    response_text = response.text.strip()

    # Try to find JSON in the response
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()

    return json.loads(response_text)

def main():
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Load templates
    print("Loading templates...")
    assertions_data = load_style_assertions()
    prompt_template = load_acrue_prompt()

    # Results storage
    results = []

    # Process each image
    for img_id, style_slug, style_name in IMAGE_PAIRS:
        restyled_path = os.path.join(RUN_DIR, "restyled", f"{img_id}_{style_slug}.png")

        print(f"\nEvaluating {img_id}_{style_slug}.png ({style_name})...")

        if not os.path.exists(restyled_path):
            print(f"  WARNING: File not found: {restyled_path}")
            continue

        # Build prompt
        prompt = build_prompt(style_name, assertions_data, prompt_template)

        # Load image
        image_b64 = load_image_as_base64(restyled_path)

        try:
            # Evaluate
            eval_result = evaluate_image(model, prompt, image_b64)

            # Add metadata
            eval_result["evaluation_id"] = f"{img_id}_{style_slug}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            eval_result["original"] = f"originals/{img_id}.png"
            eval_result["restyled"] = f"restyled/{img_id}_{style_slug}.png"
            eval_result["timestamp"] = datetime.now().isoformat()

            results.append(eval_result)

            print(f"  Grade: {eval_result.get('grade', 'N/A')} | Score: {eval_result.get('total', 'N/A')}/25 ({eval_result.get('percentage', 'N/A')}%)")

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            results.append({
                "evaluation_id": f"{img_id}_{style_slug}_error",
                "original": f"originals/{img_id}.png",
                "restyled": f"restyled/{img_id}_{style_slug}.png",
                "style": style_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    # Save results
    output_path = os.path.join(RUN_DIR, "acrue.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to: {output_path}")
    print(f"Total evaluations: {len(results)}")

    # Summary
    print("\n=== SUMMARY ===")
    for r in results:
        if "error" not in r:
            print(f"{r.get('restyled', 'N/A'):40} | {r.get('style', 'N/A'):12} | {r.get('grade', 'N/A'):3} | {r.get('total', 0):.1f}/25")

if __name__ == "__main__":
    main()
