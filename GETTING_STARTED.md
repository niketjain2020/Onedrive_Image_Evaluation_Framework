# AI Restyle Benchmark Framework - Getting Started

Automated quality evaluation pipeline for the OneDrive Photos AI Restyle feature.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Windows | 10+ | Tested on Windows 11 |
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | For Playwright MCP server |
| Microsoft Edge | Latest | Playwright browser target |
| OneDrive account | - | With Photos + AI Restyle enabled |
| Gemini API key | - | [Get one here](https://aistudio.google.com/apikey) |
| Anthropic API key | - | Optional, for Opus preference judge |

## 1. Clone & Install

```bash
git clone <repo-url> restyle_tests
cd restyle_tests
pip install -r requirements.txt
playwright install
```

## 2. Environment Setup

Copy the example files and add your keys:

```bash
# Copy environment template
copy .env.example .env

# Edit .env and add your API keys
notepad .env
```

Your `.env` should look like:
```
GEMINI_API_KEY=AIzaSy...your-key-here
ANTHROPIC_API_KEY=sk-ant-...your-key-here   # optional
GEMINI_MODEL=gemini-2.0-flash
```

Load environment variables before running:
```bash
# PowerShell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }

# Or set them individually
set GEMINI_API_KEY=your-key-here
```

## 3. MCP Setup (for Claude Code integration)

```bash
copy .mcp.json.example .mcp.json
# Edit .mcp.json and replace ${GEMINI_API_KEY} with your actual key
```

## 4. OneDrive Auth

The first time you run the Playwright-based capture phase, you'll need to log in interactively. The browser state is saved to `auth_state.json` (git-ignored) for subsequent runs.

## 5. Running a Benchmark

### Full Pipeline (7 phases)

Edit `run_spec.json` to configure your run:

```json
{
  "schema_version": "1.0.0",
  "run_id": "Run_2026_02_09_mytest",
  "pipeline_version": "1.0.0",
  "acrue_version": "v3",
  "baseline_run_id": null,
  "styles": ["Anime", "Pop Art", "Storybook"],
  "image_count": 3,
  "image_selection": {
    "source": "onedrive_photos",
    "criteria": "diverse_people"
  },
  "judges": {
    "feasibility": {"model": "gemini-2.0-flash", "version": "2.0"},
    "preference": {"model": "claude-opus-4-5", "version": "20251101"}
  },
  "synthesis": {
    "feasibility_weight": 0.5,
    "preference_weight": 0.5
  },
  "output_dir": "runs/Run_2026_02_09_mytest"
}
```

Then run each phase:

```bash
# Phase 1: VALIDATE - check all preconditions
python benchmark_orchestrator.py validate

# Phase 2: INIT - create output directory structure
python benchmark_orchestrator.py init

# Phase 3: CAPTURE - use Claude Code + Playwright MCP to capture screenshots
#   (This phase is driven interactively by Claude Code)

# Phase 4: EVALUATE - run ACRUE v3 evaluations via Gemini
python run_acrue_v3.py --batch runs/Run_2026_02_09_mytest/batch_config.json \
    --output runs/Run_2026_02_09_mytest/acrue.json

# Phase 5: RANK - compute feasibility rankings + run Opus preference
python benchmark_orchestrator.py compute-rankings
#   (Opus rankings are provided by Claude Code or via API)

# Phase 6: SYNTHESIZE - combine judges + auto-compare to baseline
python benchmark_orchestrator.py synthesize

# Phase 7: PERSIST - save to Excel tracker
python benchmark_orchestrator.py persist
```

### Single ACRUE Evaluation

```bash
# Evaluate one image pair
python run_acrue_v3.py -o original.jpg -r restyled.png -s "Storybook"

# Preview evaluation plan without running
python run_acrue_v3.py -o original.jpg -r restyled.png -s "Storybook" --plan-only
```

## 6. Comparing to Baseline

Set `baseline_run_id` in `run_spec.json` to auto-compare during synthesis.

Or compare manually:

```bash
# Compare two specific runs
python compare_runs.py --current Run_2026_02_09_mytest --baseline Run_2026_02_03_baseline

# View all runs chronologically
python compare_runs.py --history
```

Output:
```
=== COMPARISON vs Run_2026_02_03_baseline ===
  Anime            31.9% ->  45.2%  (+13.3%)  IMPROVED
  Pop Art          92.0% ->  90.1%  (-1.9%)   REGRESSION
  Storybook        86.7% ->  88.0%  (+1.3%)   IMPROVED

  VERDICT: 2 improved, 1 regressed, 0 unchanged
```

## 7. Generating Reports

DOCX reports with images, scores, and comparison data:

```bash
cd reports
python create_benchmark_docx.py
```

## 8. Directory Structure

```
restyle_tests/
  config.py                 # Shared paths & constants
  compare_runs.py           # Baseline comparison CLI
  benchmark_orchestrator.py # Pipeline orchestrator (validate/init/synthesize/persist/compare)
  run_acrue_v3.py           # ACRUE v3 evaluation engine
  run_dual_llm_pipeline.py  # Dual-LLM (Gemini + Opus) pipeline
  restyle_agent.py          # Playwright automation agent
  parallel_runner.py        # Parallel agent runner
  style_assertions.json     # Style-specific ACRUE assertions
  style_definitions.json    # Style evaluation context
  acrue_v3_prompt.md        # ACRUE v3 prompt template
  run_spec.json             # Current run configuration
  requirements.txt          # Python dependencies
  .env.example              # Environment variable template
  .mcp.json.example         # MCP server config template
  reports/                  # Report generators (DOCX, PPTX)
  results/                  # Generated reports, presentations
  runs/                     # Per-run output (one dir per benchmark run)
  lt_demo/                  # Leadership presentation materials
```

## 9. Troubleshooting

### "GEMINI_API_KEY not set"
Ensure your `.env` is loaded or the environment variable is set in your terminal session.

### Excel "OLE2" format error
The pipeline auto-detects corrupted `.xls` files masquerading as `.xlsx`. It backs up the old file and creates a fresh one. Check for `ai_restyle_benchmark.xls.bak`.

### Playwright browser not found
Run `playwright install` to download browser binaries.

### ACRUE evaluation returns invalid JSON
Gemini occasionally returns malformed JSON (~1 in 40 calls). The pipeline handles this gracefully and logs the error. Re-run the failed evaluation.

### Comparison shows "No baseline run found"
This is normal for the first run. After the second run, comparisons work automatically.
