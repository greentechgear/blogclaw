# BlogClaw

A self-improving blog system that learns from your WordPress edits.

## Description

BlogClaw watches you edit blog posts in WordPress and automatically learns your writing voice. After analyzing your revision patterns, it updates style guides that help your AI agent write better first drafts.

**Real results:** 23 revisions → 8 revisions in one week

## How It Works

1. **Fetch Revisions** - WordPress REST API provides full revision history
2. **Normalize & Strip** - Strips HTML, normalizes placeholders (`${VAR}`, `{{var}}`, `%VAR%`) so they don't pollute diffs
3. **Content Diff Analysis** - Paragraph-level diff via SequenceMatcher extracts *what* was added/removed, not just word counts
4. **Classify Content Blocks** - Each added block classified as: business context, example/case study, technical detail, edge case, personal anecdote, or general expansion
5. **Categorize Patterns** - Content Expansion (100+ words), Structure Refinement (headers, reordering), Iterative Polish (<50 words)
6. **Semantic Pattern Detection** - Explains *why* patterns matter with confidence scores and suggested actions
7. **Detect Patterns** - When 3+ posts show same pattern, log to PATTERN_ANALYSIS.md
8. **Update Style Guide** - When 5+ posts show same pattern, codify as rule

## Usage

### Analyze Specific Post
```bash
python3 analyze_revisions.py --site yourdomain.com --post-id 1926
python3 analyze_revisions.py --site yourdomain.com --post-title "Your Post Title"
```

### Analyze From Config File
```bash
python3 analyze_revisions.py --config posts.json --json
```

## Learning Files

BlogClaw generates these learning files in the `learning/` directory:

- **DAILY_ACTIVITY_LOG.md** - Every post published, revisions, patterns
- **PATTERN_ANALYSIS.md** - Recurring patterns (3+ occurrences)
- **STYLE_GUIDE.md** - Codified rules (5+ occurrences)
- **SKILL_IMPROVEMENTS.md** - Script enhancements and fixes
- **CONTENT_LEARNINGS.md** - Site-specific voice patterns

## Automated Heartbeats

Schedule with NanoClaw's task scheduler:

```python
# Daily (11 PM) - Analyze today's posts
schedule_task(
    prompt="Run BlogClaw revision analysis for posts published today on yourdomain.com",
    schedule_type="cron",
    schedule_value="0 23 * * *",
    context_mode="group"
)

# Weekly (Sun 9 AM) - Detect patterns (3+ threshold)
schedule_task(
    prompt="Run BlogClaw weekly pattern analysis to identify recurring editing patterns",
    schedule_type="cron",
    schedule_value="0 9 * * 0",
    context_mode="group"
)

# Monthly (1st 8 AM) - Update style guides (5+ threshold)
schedule_task(
    prompt="Run BlogClaw monthly evolution check to update style guides with codified patterns",
    schedule_type="cron",
    schedule_value="0 8 1 * *",
    context_mode="group"
)
```

## Configuration

Create `.env` in the blogclaw directory:

```bash
WORDPRESS_URL=https://yourdomain.com
WORDPRESS_USERNAME=admin
WORDPRESS_PASSWORD=xxxx_xxxx_xxxx_xxxx
```

## Triggers

Use this skill when:
- "analyze my blog revisions"
- "what patterns am I editing?"
- "what kind of content am I adding?"
- "run BlogClaw on [post]"
- "check WordPress revisions for [site]"
- "why does the AI keep missing [X] in drafts?"
- "update my writing style guide"
- Any request about learning from WordPress edits

## Dependencies

- requests (HTTP client for WordPress REST API)

Installed automatically by `install.sh`

## Version

0.3.0 - Content diff analyzer, placeholder detection, semantic pattern matching
0.2.0 - Added NanoClaw plugin structure with install.sh and SKILL.md

## More Info

Read the full story: https://brianchappell.com/self-improving-blog-system/
GitHub: https://github.com/greentechgear/blogclaw
