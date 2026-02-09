"""
Dual-LLM ACRUE v2 Evaluation - Gemini + Summary
"""
import google.generativeai as genai
import base64
import json
import os
from datetime import datetime
from pathlib import Path

# Configure Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

ACRUE_PROMPT = """
You are evaluating an AI-restyled image using the ACRUE v2 framework.

STYLE: {style}

For each dimension, answer the Yes/No assertions and provide evidence.
Then calculate scores based on pass rates.

## ACRUE Dimensions (Total: 25 points)

### A - Accuracy (Weight: 1.0, Max: 5 points)
- A1: Does the output exhibit the expected style textures/characteristics?
- A2: Is the subject recognizable from the original?
- A3: Does the color palette match the style expectations?
- A4: Are expressions and poses preserved?
- A5: Does rendering match professional quality for this style?

### C - Completeness (Weight: 1.0, Max: 5 points)
- C1: Is style applied to the entire image (no photo patches)?
- C2: Does background complement the styled subject?
- C3: Are all subjects structurally intact (no broken limbs)?
- C4: Is style saturation appropriate?
- C5: Are all elements stylistically consistent?

### R - Relevance (Weight: 0.5, Max: 2.5 points)
- R1: Does output clearly represent the requested style?
- R2: Does emotional tone fit style expectations?
- R3: Does mood align with what users expect?
- R4: Does it avoid inconsistent elements?

### U - Usefulness (Weight: 0.5, Max: 2.5 points)
- U1: Is it suitable for intended use (sharing, printing)?
- U2: Is it free of obvious digital artifacts?
- U3: Is subject clearly visible?
- U4: Is resolution sufficient?

### E - Exceptional (Weight: 2.0, Max: 10 points)
- E1: Does it look like professional work?
- E2: Does transformation add artistic value?
- E3: Would users be excited to share this?
- E4: Does it have standout quality?
- E5: Does it evoke positive emotional response?

## Scoring Rules
- All assertions pass: 5/5 score
- 1 failure: 4/5 score
- 2 failures: 3/5 score
- 3+ failures: 2/5 or lower

Return a JSON object with this structure:
{{
  "style": "{style}",
  "dimensions": {{
    "accuracy": {{"passed": X, "total": 5, "score": X, "evidence": "..."}},
    "completeness": {{"passed": X, "total": 5, "score": X, "evidence": "..."}},
    "relevance": {{"passed": X, "total": 4, "score": X, "evidence": "..."}},
    "usefulness": {{"passed": X, "total": 4, "score": X, "evidence": "..."}},
    "exceptional": {{"passed": X, "total": 5, "score": X, "evidence": "..."}}
  }},
  "weighted_total": X.X,
  "percentage": X.X,
  "grade": "A+/A/B/C/F",
  "summary": "Brief overall assessment"
}}
"""

def evaluate_image(image_path, style):
    """Evaluate a single image with Gemini"""
    print(f"\nEvaluating {style} style...")

    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    # Create prompt
    prompt = ACRUE_PROMPT.format(style=style)

    # Call Gemini
    response = model.generate_content([
        prompt,
        {"mime_type": "image/png", "data": image_data}
    ])

    # Parse response
    text = response.text
    # Try to extract JSON
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]

    try:
        result = json.loads(text)
    except:
        result = {"raw_response": text, "parse_error": True}

    return result

def main():
    results = {
        "evaluation_id": "dual-llm-2026-02-03",
        "timestamp": datetime.now().isoformat(),
        "evaluator": "Gemini 2.0 Flash",
        "evaluations": []
    }

    # Image paths
    base_path = Path(__file__).resolve().parent.parent.parent / 'gemini-mcp' / '.playwright-mcp'
    storybook_path = str(base_path / 'img1_storybook_styled.png')
    toymodel_path = str(base_path / 'img1_toymodel_styled.png')

    # Evaluate Storybook
    storybook_result = evaluate_image(storybook_path, "Storybook")
    results["evaluations"].append({
        "image": "img1_storybook_styled.png",
        "style": "Storybook",
        "result": storybook_result
    })
    print(f"Storybook: {storybook_result.get('grade', 'N/A')} - {storybook_result.get('weighted_total', 'N/A')}/25")

    # Evaluate Toy Model
    toymodel_result = evaluate_image(toymodel_path, "Toy Model")
    results["evaluations"].append({
        "image": "img1_toymodel_styled.png",
        "style": "Toy Model",
        "result": toymodel_result
    })
    print(f"Toy Model: {toymodel_result.get('grade', 'N/A')} - {toymodel_result.get('weighted_total', 'N/A')}/25")

    # Save results
    output_path = str(Path(__file__).resolve().parent / 'gemini_dual_eval.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    return results

if __name__ == "__main__":
    main()
