# Image Evaluation Framework
An LLM-as-Judge pipeline that scores AI image transformations — so you don't need a room full of human raters

## The punchline

Every AI image feature ships with the same blind spot: *"Is the output actually good?"* Human evaluation doesn't scale. Single-model scoring hallucinates. So the question isn't "can an LLM rate images?" — it's "can you trust the grade enough to block a release on it?"

## The core problem

Manual image evaluation has five pain points that don't go away with more headcount:

- **Speed** — Manual evaluations don't scale. Reviewing 14 styles across 50 images is 700 judgments. A human rater burns a full day; the framework finishes in minutes.
- **Consistency** — Results change based on who's reviewing, what order they see images, and whether it's before or after lunch. LLM judges don't have bad days.
- **Memory** — There's no durable benchmark. Last week's evaluation lives in someone's head or a one-off spreadsheet. The framework persists every score to a structured file so you can compare across builds.
- **Reusability** — You can't reuse results or track progress when evaluations are ad hoc conversations. Structured assertions and JSON output mean every evaluation is queryable and comparable.
- **Rigor** — "Looks good to me" isn't a quality gate. The framework provides systematic multi-LLM judging with structured rubrics, per-assertion evidence, and deterministic scoring.

## What it is

The Image Evaluation Framework takes any original image and its AI-transformed output, runs it through two LLM judges (Gemini for technical quality, Opus for creative preference), and produces a graded scorecard with per-assertion evidence. It works for style transfer, background removal, upscaling, inpainting — any task where you need to measure "did the AI do a good job?"

It's not a demo. It's a pipeline you can wire into CI, run across hundreds of image pairs, and use to catch regressions between builds.

## How ACRUE v3 scores work

The core design insight: **the LLM observes, code scores.** The model never picks a number. It answers structured questions and rates its own confidence. Local code does the math.

Getting here took three iterations:

**v1 — LLM scores directly (1-5).** You ask the model "rate this image's accuracy 1-5" and it gives you a number with a rationale. Simple, but the scores are hallucinated — the model picks a number that *sounds right* without grounding it in specific observations. Two runs on the same image can produce different scores.

**v2 — Binary assertions only.** Instead of scoring, the model answers Yes/No questions: *"Does the output exhibit watercolor textures?"* Code counts the pass rate and derives a score. Grounded in evidence, but you lose nuance — a confident Yes and a barely-Yes count the same.

**v3 — Hybrid (assertions + confidence).** The model answers Yes/No *and* rates its confidence 1-5 for each assertion, citing evidence. Code uses both the pass/fail result and the confidence level to compute weighted scores. This is the sweet spot: grounded like v2, nuanced like v1, but the LLM never touches the final number.

```
v1:  image -> LLM -> score                        (hallucination-prone)
v2:  image -> LLM -> Yes/No -> code -> score       (grounded, but binary)
v3:  image -> LLM -> Yes/No + confidence -> code -> score  (grounded AND nuanced)
```

## What it looks like

The framework has three entry points — you pick the one that fits your workflow. You can start with just a Gemini API key and two images.

- **"Score this image pair."** -> Runs 23 Yes/No assertions across 5 dimensions, returns a weighted grade with evidence for every assertion.
- **"Compare Gemini and Opus on these outputs."** -> Both models score independently, then a synthesis step produces a consensus ranking.
- **"Run a full benchmark across 14 styles and 3 images, compare to last week's baseline, flag regressions."** -> End-to-end pipeline: capture, evaluate, rank, synthesize, compare, persist to Excel.
- **"Just show me what it would check — don't call any APIs."** -> Plan-only mode displays the full assertion checklist without spending a token.

## Example workflow: Evaluate a Storybook restyle

Give it an original photo and the AI-restyled version. Get back a graded scorecard in seconds.

```
ACRUE v3 HYBRID EVALUATION: STORYBOOK

A - Accuracy: 4/5 passed | Avg Confidence: 4.6/5
  A1. [Y] ##### Does output exhibit soft, watercolor-like textures?
       -> Clear watercolor wash effects with visible brushstroke simulation
  A2. [Y] ##### Is the subject recognizable from the original?
       -> Subject is clearly identifiable, pose and composition preserved
  A3. [N] ##--- Are facial proportions adjusted in storybook style?
       -> Proportions remain photographic, not stylized

SCORE BREAKDOWN
Dimension         Passed     Conf    Score    Weight    Weighted
Accuracy            4/5    4.6/5    3.8/5       1.0        3.80
Completeness        5/5    4.8/5    4.6/5       1.0        4.60
Relevance           3/4    4.0/5    3.5/5       0.5        1.75
Usefulness          4/4    4.5/5    4.5/5       0.5        2.25
Exceptional         4/5    3.8/5    3.6/5       2.0        7.20

FINAL RESULT
  Weighted Score:   19.60 / 25.0
  Percentage:       78.4%
  Grade:            B
```

Every assertion has a Yes/No answer, a 1-5 confidence score, and cited evidence. The grade is computed deterministically from assertions — the LLM doesn't pick the number.

## Why two judges, not one

A single LLM judge has blind spots. This framework uses two models that evaluate from complementary angles, then synthesizes a verdict.

**Gemini** is the technical eye. It's the best vision model in the industry right now — it sees pixel-level detail, catches artifacts, identifies whether style markers are actually present, and flags structural errors like warped faces or broken limbs. It answers: *"Is this technically correct?"*

**Opus** is the taste judge. Strong reasoning, holistic quality assessment. It catches the outputs that pass every technical check but still feel *off* — the uncanny valley of AI image transformation. It answers: *"Would a real user actually pick this one?"*

Each judge scores independently using the same ACRUE rubric. Neither sees the other's output. The synthesis step combines their rankings:

```
final_score = (feasibility_weight x gemini_rank) + (preference_weight x opus_rank)
```

Configurable weights (default 50/50). Shift toward technical rigor (70/30) for engineering QA. Shift toward preference (30/70) for consumer-facing decisions.

**The architecture is model-agnostic.** As new vision models enter the market — GPT-5V, Gemini Ultra, whatever ships next — you swap the judge, not the rubric. Change one environment variable and the same assertions, the same scoring, the same comparison pipeline works with a different model underneath.

## The ACRUE dimensions

**ACRUE** stands for **A**ccuracy, **C**ompleteness, **R**elevance, **U**sefulness, **E**xceptional value. Five dimensions, weighted to reflect real-world importance:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **A** - Accuracy | 1.0 | Does the transformation match the target style? |
| **C** - Completeness | 1.0 | Is the transformation applied to the entire image? |
| **R** - Relevance | 0.5 | Is the output appropriate for the requested task? |
| **U** - Usefulness | 0.5 | Is it practically usable (shareable, printable)? |
| **E** - Exceptional Value | 2.0 | Does it exceed expectations — the "wow" factor? |

Each dimension has 4-5 assertions. For each assertion, the LLM returns a Yes/No answer, a 1-5 confidence score, and cited evidence. The dimension score is computed deterministically:

```
dimension_score = pass_rate × avg_confidence × weight
```

Total: 25 points. The "Exceptional" dimension is double-weighted because that's what separates good from great in consumer AI — users don't share technically correct images, they share ones that make them say *"I want to frame this."*

Grade thresholds are fixed: 90-100% = A+, 80-89% = A, 70-79% = B, 60-69% = C, below 60% = F.

## What makes this different

- **Assertion-grounded**: the LLM proves its score before assigning it. Every grade traces back to specific Yes/No evidence.
- **Dual-judge consensus**: two models with different strengths, combined with configurable weights. Neither alone sees the full picture.
- **Customizable for any task**: define your own assertions for background removal, upscaling, inpainting — anything. The rubric adapts; the pipeline stays the same.
- **Regression detection built in**: every run auto-compares to baseline. You see which styles improved, which regressed, and by how much.
- **Plan-only mode**: preview the full evaluation plan (every assertion that will be checked) without spending a single API token.
- **Model-agnostic**: swap judges as better models ship. The rubric and assertions are the contract; the model is a replaceable part.

## Customization: bring your own task

The 14 built-in style presets (Anime, Storybook, Pop Art, etc.) are examples. You define assertions for *your* image transformation task by adding entries to a JSON file:

```json
{
  "Background Removal": {
    "description": "Remove background, keep subject on transparent/white",
    "assertions": {
      "accuracy": [
        "Is the subject fully preserved with no cropped edges?",
        "Are fine details (hair, fur) cleanly separated?"
      ],
      "completeness": [
        "Is the mask edge smooth without jagged artifacts?"
      ],
      "exceptional": [
        "Are semi-transparent areas (glass, smoke) handled correctly?"
      ]
    }
  }
}
```

Then: `python run_acrue_v3.py -o photo.jpg -r cutout.png -s "Background Removal"`

Same pipeline. Same scoring. Same regression tracking. Different assertions.

## Architecture (end-to-end)

Two major components:

1. **Python evaluation engine**: image pair in -> base64 encode -> build ACRUE prompt with style-specific assertions -> send to Gemini with both images -> parse structured JSON response -> compute weighted scores deterministically -> grade.

2. **Pipeline orchestrator**: 7-phase benchmark runner (validate -> init -> capture -> evaluate -> rank -> synthesize -> persist) that wires together Playwright for browser automation, Gemini for feasibility, Opus for preference, and Excel for longitudinal tracking.

## The evaluation pipeline

- An image pair arrives (original + transformed).
- Style-specific assertions are loaded from `rubrics/style_assertions.json`. If the style isn't defined, generic assertions are auto-generated.
- The ACRUE v3 prompt template is populated with the assertions and style context.
- Both images are base64-encoded and sent to Gemini along with the prompt.
- Gemini returns structured JSON: for each assertion, a Yes/No answer, 1-5 confidence, and evidence.
- Local code computes dimension scores from assertion pass rates and confidence.
- Weighted scores are summed. A grade is assigned deterministically.
- Results are appended to a JSON file for comparison and reporting.

## The "boring" problems it solved

- **LLM score hallucination**: direct rubric-to-score prompting is unreliable. Forcing assertions first grounds the evaluation in observable evidence.
- **Style-transfer evaluation is not pixel comparison**: the original rubric penalized images for looking different from the original — which is literally the point of style transfer. ACRUE was redesigned around "what should stay the same" vs "what should change."
- **Gemini returns invalid JSON ~1 in 40 calls**: the pipeline handles this gracefully, logs the error, and continues the batch.
- **Assertion mismatch**: anime assertions expect eyes and faces, but a botanical illustration has none. The framework auto-generates generic assertions for styles without pre-defined ones, and flags mismatches in scoring anomalies.
- **Score overflow**: early versions allowed dimension scores to exceed 5.0 when confidence was high, producing percentages above 100%. Now capped deterministically.

## Regression detection

Every benchmark run can auto-compare to a baseline:

```
=== COMPARISON vs Run_2026_02_03 ===
  Anime            31.9% ->  45.2%  (+13.3%)  IMPROVED
  Pop Art          92.0% ->  90.1%  (-1.9%)   REGRESSION
  Storybook        86.7% ->  88.0%  (+1.3%)   IMPROVED

  VERDICT: 2 improved, 1 regressed, 0 unchanged
```

This is the CI gate story: run the benchmark before and after a model change. If regressions exceed a threshold, the run is flagged. Over time, the Excel tracker builds a longitudinal view of quality across builds.

## How can I try this?

The framework is open source: [Onedrive_Image_Evaluation_Framework](https://github.com/niketjain2020/Onedrive_Image_Evaluation_Framework)

What's in the repo:

- ACRUE v3 hybrid rubric (assertions + confidence scoring)
- Pre-defined assertions for 14 styles (Anime, Storybook, Pop Art, etc.)
- Batch evaluation across multiple image pairs
- Dual-judge support (Gemini + Opus)
- Regression detection and Excel benchmarking
- Plan-only mode (preview assertions without API calls)

Quick start:

```bash
git clone https://github.com/niketjain2020/Onedrive_Image_Evaluation_Framework.git
cd Onedrive_Image_Evaluation_Framework
pip install google-generativeai python-docx
set GEMINI_API_KEY=your_key_here
python run_acrue_v3.py -o photo.jpg -r styled.png -s "Storybook"
```

You'll have a graded scorecard in under 30 seconds.

## Next steps

There's more to build — extending the judge panel beyond two models, adding cross-image consistency checks (does Anime look consistent across 10 different photos?), integrating directly into CI/CD pipelines as a quality gate, and supporting video frame evaluation for AI video features.

The framework is designed to grow. The rubric is the stable contract. The judges, the assertions, and the pipeline phases are all swappable. The goal is simple: automated image quality evaluation you can trust enough to ship on.
