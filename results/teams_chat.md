Hey all — been experimenting with something that might be useful for bug bashes and wanted to share in case others find it helpful.

**What it is:** Claude Code + Playwright — lets you test features using natural language instead of writing scripts.

**What it can do:**
- Run through your feature and take screenshots at each step
- Record video of the entire session
- Generate a Word doc with all findings and images embedded
- Create a PowerPoint summary
- Draft an email in Outlook with everything attached — ready to send

Basically: test → document → share, all in one go.

**Example prompt I used:**
> "Go to OneDrive Photos. Test AI Restyle. Try different styles. Check if Stop button works. Take screenshots. Generate a report and draft an email with findings."

It caught a couple things I probably would've missed clicking through manually. And within minutes I had screenshots, a report with images, and an email draft ready in Outlook.

**If anyone wants to try:**
1. `npm install -g @anthropic-ai/claude-code`
2. `npx @anthropic-ai/claude-code mcp add playwright`
3. Run `claude` and describe what you want to test

Happy to walk through it if anyone's curious. Still learning myself but thought it was worth sharing.
