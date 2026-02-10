# Image Evaluation Framework

An LLM-as-Judge pipeline that scores AI image transformations — so you don't need a room full of human raters.

## The core problem

Every AI image feature ships with the same blind spot: *"Is the output actually good?"* Manual evaluation has five pain points that don't go away with more headcount:

- **Speed** — Reviewing 14 styles across 50 images is 700 judgments. A human rater burns a full day; the framework finishes in minutes.
- **Consistency** — Results change based on who's reviewing, what order they see images, and whether it's before or after lunch. LLM judges don't have bad days.
- **Memory** — There's no durable benchmark. Last week's evaluation lives in someone's head or a one-off spreadsheet. The framework persists every score to a structured file so you can compare across builds.
- **Reusability** — You can't reuse results or track progress when evaluations are ad hoc conversations. Structured assertions and JSON output mean every evaluation is queryable and comparable.
- **Rigor** — "Looks good to me" isn't a quality gate. The framework provides systematic multi-LLM judging with structured rubrics, per-assertion evidence, and deterministic scoring.

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

## Quick start

You need a Gemini API key and two images. That's it.

```bash
git clone https://github.com/niketjain2020/Image_Evaluation_Framework.git
cd Image_Evaluation_Framework
pip install -r requirements.txt
set GEMINI_API_KEY=your-key-here

# Evaluate one image pair
python run_acrue_v3.py -o original.jpg -r transformed.png -s "Anime"

# Preview what assertions will be checked (no API call)
python run_acrue_v3.py -o original.jpg -r transformed.png -s "Anime" --plan-only

# Batch evaluate multiple pairs
python run_acrue_v3.py --batch examples/batch_eval_config.json
```

Example output:

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

## The ACRUE dimensions

**ACRUE** stands for **A**ccuracy, **C**ompleteness, **R**elevance, **U**sefulness, **E**xceptional value. Five dimensions, weighted to reflect real-world importance:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **A** - Accuracy | 1.0 | Does the transformation match the target style? |
| **C** - Completeness | 1.0 | Is the transformation applied to the entire image? |
| **R** - Relevance | 0.5 | Is the output appropriate for the requested task? |
| **U** - Usefulness | 0.5 | Is it practically usable (shareable, printable)? |
| **E** - Exceptional Value | 2.0 | Does it exceed expectations — the "wow" factor? |

Each dimension has 4-5 assertions. The dimension score is computed deterministically:

```
dimension_score = pass_rate × avg_confidence × weight
```

Total: 25 points. The "Exceptional" dimension is double-weighted because that's what separates good from great in consumer AI — users don't share technically correct images, they share ones that make them say *"I want to frame this."*

Grade thresholds: 90-100% = A+, 80-89% = A, 70-79% = B, 60-69% = C, below 60% = F.

## Three ways to use this

| | What | Command | You Need |
|---|------|---------|----------|
| **Start here** | Evaluate any image pair | `run_acrue_v3.py` | Gemini API key + two images |
| Dual-LLM | Gemini + Opus side-by-side scoring | `run_dual_llm_pipeline.py` | Both API keys + images |
| Full pipeline | Capture, evaluate, compare, track | `benchmark_orchestrator.py` | Full setup ([guide](GETTING_STARTED.md)) |

### Dual-LLM evaluation

A single LLM judge has blind spots. This framework uses two models that evaluate from complementary angles, then synthesizes a verdict.

| | Gemini (Feasibility) | Opus (Preference) |
|---|---|---|
| **Strength** | Best-in-class vision — sees pixel-level detail | Strong reasoning — evaluates holistic quality and taste |
| **Asks** | "Is the style technically correct?" | "Would a user actually pick this one?" |
| **Catches** | Artifacts, structural errors, incomplete transforms | Uncanny outputs that pass technical checks but feel wrong |

Each judge scores independently using the same ACRUE rubric. Neither sees the other's output. The synthesis step combines their rankings:

```
final_score = (feasibility_weight × gemini_rank) + (preference_weight × opus_rank)
```

Configurable weights (default 50/50). Shift toward technical rigor (70/30) for engineering QA. Shift toward preference (30/70) for consumer-facing decisions.

```bash
python run_dual_llm_pipeline.py \
    --original portrait.jpg \
    --styled storybook.png toymodel.png \
    --styles "Storybook" "Toy Model"
```

**The architecture is model-agnostic.** As new vision models ship, you swap the judge, not the rubric. Change one environment variable and the same assertions, scoring, and comparison pipeline works with a different model underneath.

### Full pipeline

End-to-end benchmark with browser automation (Playwright + Claude Code), ACRUE evaluation, baseline comparison, and Excel tracking across runs.

```
CAPTURE  ->  EVALUATE  ->  RANK  ->  SYNTHESIZE  ->  COMPARE  ->  PERSIST
Playwright     ACRUE v3    Gemini     Weighted       Baseline     Excel
+ Claude       via Gemini  + Opus     synthesis      deltas       tracker
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full 7-phase setup.

## Customization: bring your own task

The 14 built-in style presets (Anime, Storybook, Pop Art, etc.) are examples. You define assertions for *your* image transformation task by adding entries to `rubrics/style_assertions.json`:

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

## Baseline comparison

Every benchmark run can auto-compare to a baseline:

```bash
python compare_runs.py --current Run_2026_02_09 --baseline Run_2026_02_03

# Output:
#   Anime            31.9% ->  45.2%  (+13.3%)  IMPROVED
#   Pop Art          92.0% ->  90.1%  (-1.9%)   REGRESSION
#   Storybook        86.7% ->  88.0%  (+1.3%)   IMPROVED
#   VERDICT: 2 improved, 1 regressed, 0 unchanged

python compare_runs.py --history   # View all runs
```

This is the CI gate story: run the benchmark before and after a model change. If regressions exceed a threshold, the run is flagged. Over time, the Excel tracker builds a longitudinal view of quality across builds.

## Project structure

```
run_acrue_v3.py            # ACRUE v3 evaluation engine (start here)
run_acrue_eval.py          # ACRUE v1/v2 evaluation (legacy)
run_dual_llm_pipeline.py   # Dual-LLM (Gemini + Opus) pipeline
benchmark_orchestrator.py  # Full pipeline orchestrator
compare_runs.py            # Baseline comparison CLI
config.py                  # Shared paths & constants
run_spec.json              # Run configuration
rubrics/                   # Evaluation rubrics, prompts & assertions
agents/                    # Agent instruction files
examples/                  # Sample configs & demo data
reports/                   # Report generators (DOCX, PPTX)
results/                   # Evaluation output
runs/                      # Per-run output directories
```

## Requirements

- Python 3.10+
- Gemini API key ([get one](https://aistudio.google.com/apikey)) — minimum for standalone evaluation
- Anthropic API key (optional, for Opus preference judge)
- Node.js 18+ (optional, for Playwright automation in full pipeline)

## Further reading

For the full narrative — design decisions, problems solved, architecture details — see [Image_Evaluation_Framework_Writeup.md](Image_Evaluation_Framework_Writeup.md).
