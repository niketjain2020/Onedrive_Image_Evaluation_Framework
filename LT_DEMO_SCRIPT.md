# AI Restyle Automated Testing with Claude Code
## LT Demo Script

---

## NARRATIVE (2 min)

### The Problem
"Testing our AI Restyle feature manually is time-consuming. We have 14 style presets, and each generation takes 60-90 seconds. Testing one image across all styles takes ~20 minutes. Testing multiple images? Hours of manual clicking and waiting."

### The Solution
"Claude Code with Playwright MCP gives us AI-powered automated testing. Instead of writing complex test scripts, I simply describe what I want to test in natural language, and Claude executes it - navigating the UI, clicking buttons, waiting for AI generation, and capturing results."

### Key Benefits
1. **Natural Language Testing** - No need to write Selenium/Playwright code
2. **Intelligent Waiting** - Claude understands when generation is complete
3. **Automatic Screenshots** - Captures results for review
4. **Scalable** - Can run multiple instances in parallel
5. **Adaptable** - If UI changes, just update the description

---

## LIVE DEMO FLOW (5-7 min)

### Setup (30 sec)
- Show VS Code with Claude Code running
- "I have Claude Code connected to a browser via Playwright"

### Step 1: Navigate to OneDrive Photos (30 sec)
Say to Claude:
```
Navigate to https://onedrive.live.com/?view=8
```
- Show browser opening and navigating
- "Claude is controlling a real browser, just like a user would"

### Step 2: Open an Image (30 sec)
Say to Claude:
```
Click on the first image in the Photos gallery
```
- Show image viewer opening
- "It understands the UI structure and finds the right element"

### Step 3: Test AI Restyle (3-4 min)
Say to Claude:
```
Click on Restyle with AI, then select Movie Poster style and click Send. Wait for generation to complete and take a screenshot.
```
- Show the restyle panel opening
- Show style being selected
- **While waiting for generation:** Explain parallel capability
- Show screenshot being captured

### Step 4: Show Results (30 sec)
```
Show me the screenshot you took
```
- Display the generated image
- "Complete test cycle - navigation, interaction, wait, capture"

---

## TALKING POINTS

### For Technical Leaders
- "Uses Playwright under the hood - industry standard"
- "Claude handles the complexity of waits and selectors"
- "Can be extended to full regression suites"

### For Product Leaders
- "Reduces manual testing time by 80%"
- "Catches visual regressions automatically"
- "Frees QA to focus on edge cases"

### For Executives
- "AI testing AI features - meta but practical"
- "Natural language = lower barrier to entry"
- "Scales with the product"

---

## BACKUP: If Demo Fails

Have these screenshots ready from previous runs:
- `results/image_1/movie_poster.png`
- `results/image_1/plush_toy.png`
- `results/image_1/anime.png`

Say: "Let me show you results from an earlier run while we troubleshoot"

---

## Q&A PREP

**Q: How is this different from Selenium?**
A: No code required. Describe tests in plain English. Claude adapts to UI changes.

**Q: Can it run in CI/CD?**
A: Yes, Claude Code can run headless in pipelines.

**Q: What about parallel testing?**
A: Multiple Claude Code instances can run simultaneously, each with its own browser.

**Q: Cost?**
A: Claude API usage. Typically pennies per test run.

**Q: Can it test other features?**
A: Yes - any web UI. File operations, sharing, editing - all testable.

---

## DEMO CHECKLIST

Before demo:
- [ ] Claude Code running in VS Code
- [ ] Logged into OneDrive in browser
- [ ] Results folder exists
- [ ] Backup screenshots ready
- [ ] Network is stable

---

## ONE-LINER SUMMARY

"We're using AI to test AI - Claude Code automates our Restyle feature testing, turning hours of manual work into minutes of natural language commands."
