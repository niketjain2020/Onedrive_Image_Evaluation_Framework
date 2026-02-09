# Image Evaluation Framework

Measure AI image transformation quality using LLM judges (Gemini + Opus) and the ACRUE v3 scoring rubric. No human raters needed.

## What This Does

You have an AI that transforms images — style transfer, background removal, upscaling, inpainting, generation from prompt. How do you measure whether the output is actually good? This framework uses **LLM-as-Judge** evaluation with structured assertions and confidence scores to produce repeatable quality grades.

Give it an original image, a transformed image, and a description of what the transformation should have done. It returns a graded scorecard with per-assertion evidence.

## Use Cases

- **Style transfer** — did the Anime filter actually produce anime-style output?
- **Background removal / replacement** — is the subject intact, are edges clean?
- **Image upscaling** — is detail preserved without hallucinated artifacts?
- **Inpainting / object removal** — is the fill seamless and coherent?
- **Image generation QA** — does the output match the prompt?

## Three Ways to Use This

You don't need the full pipeline. Pick the entry point that fits your workflow:

| | What | Command | You Need |
|---|------|---------|----------|
| **Start here** | Evaluate any image pair | `run_acrue_v3.py` | Gemini API key + two images |
| Dual-LLM | Gemini + Opus side-by-side scoring | `run_dual_llm_pipeline.py` | Both API keys + images |
| Full pipeline | Capture, evaluate, compare, track | `benchmark_orchestrator.py` | Full setup ([guide](GETTING_STARTED.md)) |

---

### Option 1: Standalone ACRUE v3 Evaluation (start here)

The fastest way to get a quality score. You need a Gemini API key and two images.

```bash
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
A - Accuracy: 4/5 passed | Avg Confidence: 4.2/5
  A1. [Y] ##### Does output exhibit anime-style cel-shading?
       -> Colors are more vibrant than original, clear cel-shading in background
  A2. [Y] ##### Is the subject recognizable from the original?
       -> Subject is clearly still identifiable
  A3. [N] ##--- Are facial proportions adjusted in anime style?
       -> Proportions remain photographic, not stylized

SCORE BREAKDOWN
Dimension         Passed     Conf    Score    Weight    Weighted
Accuracy            4/5    4.2/5    3.8/5       1.0        3.80
Completeness        5/5    4.6/5    4.6/5       1.0        4.60
Relevance           3/4    4.0/5    3.5/5       0.5        1.75
Usefulness          4/4    4.5/5    4.5/5       0.5        2.25
Exceptional         4/5    3.8/5    3.6/5       2.0        7.20

FINAL RESULT
  Weighted Score:   19.60 / 25.0
  Percentage:       78.4%
  Grade:            B
```

### Option 2: Dual-LLM Evaluation

Run both Gemini (feasibility scoring) and Opus (preference ranking) on the same images. Produces a DOCX report with side-by-side before/after images and scores from both judges.

```bash
python run_dual_llm_pipeline.py \
    --original portrait.jpg \
    --styled storybook.png toymodel.png \
    --styles "Storybook" "Toy Model"
```

Requires both `GEMINI_API_KEY` and `ANTHROPIC_API_KEY`.

### Option 3: Full Pipeline

End-to-end benchmark with browser automation (Playwright + Claude Code), ACRUE evaluation, baseline comparison, and Excel tracking across runs.

```
CAPTURE  ->  EVALUATE  ->  RANK  ->  SYNTHESIZE  ->  COMPARE  ->  PERSIST
Playwright     ACRUE v3    Gemini     Weighted       Baseline     Excel
+ Claude       via Gemini  + Opus     synthesis      deltas       tracker
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full 7-phase setup.

---

## How ACRUE v3 Works

**ACRUE** stands for **A**ccuracy, **C**ompleteness, **R**elevance, **U**sefulness, **E**xceptional value — five dimensions weighted to produce a score out of 25.

The key insight: direct LLM rubric scoring hallucinates. ACRUE v3 forces the judge to answer concrete Yes/No assertions with confidence scores *before* it can assign a number:

```
v1:  Rubric -> Score                          (hallucination-prone)
v2:  Rubric -> Yes/No Assertions -> Score     (grounded, but binary)
v3:  Rubric -> Assertions + Confidence -> Score  (grounded AND nuanced)
```

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **A** - Accuracy | 1.0 | Does the transformation match the target style? |
| **C** - Completeness | 1.0 | Is the transformation applied to the entire image? |
| **R** - Relevance | 0.5 | Is the output appropriate for the requested task? |
| **U** - Usefulness | 0.5 | Is it practically usable (shareable, printable, etc.)? |
| **E** - Exceptional Value | 2.0 | Does it exceed expectations — the "wow" factor? |

Grades: A+ (90%+), A (80%+), B (70%+), C (60%+), F (<60%)

## Customizing Assertions

The built-in assertions cover 14 style-transfer presets, but you can define assertions for **any** image transformation task. Add your own in `rubrics/style_assertions.json`:

```json
{
  "styles": {
    "Background Removal": {
      "description": "Remove background, keep subject on transparent/white",
      "assertions": {
        "accuracy": [
          "Is the subject fully preserved with no cropped edges?",
          "Are fine details (hair, fur, transparent objects) cleanly separated?",
          "Is the background completely removed with no residual patches?"
        ],
        "completeness": [
          "Are all foreground elements retained?",
          "Is the mask edge smooth without jagged artifacts?"
        ],
        "relevance": [
          "Is the output suitable for compositing onto a new background?",
          "Does the subject look natural without the original background?"
        ],
        "usefulness": [
          "Is the resolution preserved from the original?",
          "Is the output free of halo effects around the subject?"
        ],
        "exceptional": [
          "Would this pass for a professional cutout?",
          "Are semi-transparent areas (glass, smoke) handled correctly?"
        ]
      }
    }
  }
}
```

Then evaluate:
```bash
python run_acrue_v3.py -o photo.jpg -r cutout.png -s "Background Removal"
```

For styles not in the assertions file, the framework auto-generates generic assertions.

## Baseline Comparison

Compare any two runs to flag regressions:

```bash
python compare_runs.py --current Run_2026_02_09 --baseline Run_2026_02_03

# Output:
#   Anime            31.9% ->  45.2%  (+13.3%)  IMPROVED
#   Pop Art          92.0% ->  90.1%  (-1.9%)   REGRESSION
#   Storybook        86.7% ->  88.0%  (+1.3%)   IMPROVED
#   VERDICT: 2 improved, 1 regressed, 0 unchanged

python compare_runs.py --history   # View all runs
```

## Built-in Style Presets

14 presets with pre-defined assertions: Movie Poster, Plush Toy, Anime, Chibi Sticker, Caricature, Superhero, Toy Model, Graffiti, Crochet Art, Doodle, Pencil Portrait, Storybook, Photo Booth, Pop Art

These ship as examples. Add your own for any transformation task.

## Project Structure

```
config.py                  # Shared paths & constants
run_acrue_v3.py            # ACRUE v3 evaluation engine (start here)
run_acrue_eval.py          # ACRUE v1/v2 evaluation (legacy)
run_dual_llm_pipeline.py   # Dual-LLM (Gemini + Opus) pipeline
benchmark_orchestrator.py  # Full pipeline orchestrator
compare_runs.py            # Baseline comparison CLI
restyle_agent.py           # Playwright automation agent
parallel_runner.py         # Parallel agent runner
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
- Windows 10+ (tested on Windows 11)

## Getting Started

For the full pipeline setup (Playwright, OneDrive auth, run configuration), see [GETTING_STARTED.md](GETTING_STARTED.md).
