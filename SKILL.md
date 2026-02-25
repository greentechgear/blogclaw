# BlogClaw

A self-improving blog system that learns from your WordPress edits.

## Description

BlogClaw watches you edit blog posts in WordPress and automatically learns your writing voice. After analyzing your revision patterns, it updates style guides that help your AI agent write better first drafts.

**Real results:** 23 revisions → 8 revisions in one week

## How It Works

1. **Fetch Revisions** - WordPress REST API provides full revision history
2. **Analyze Changes** - HTMLStripper extracts plain text, word counts calculated
3. **Categorize Patterns** - Content Expansion (100+ words), Structure Refinement (headers), Iterative Polish (<50 words)
4. **Detect Patterns** - When 3+ posts show same pattern, log to PATTERN_ANALYSIS.md
5. **Update Style Guide** - When 5+ posts show same pattern, codify as rule

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
- "run BlogClaw on [post]"
- "check WordPress revisions for [site]"
- "update my writing style guide"
- Any request about learning from WordPress edits

## Dependencies

- requests (HTTP client for WordPress REST API)

Installed automatically by `install.sh`

## Version

0.2.0 - Added NanoClaw plugin structure with install.sh and SKILL.md

## More Info

Read the full story: https://brianchappell.com/self-improving-blog-system/
GitHub: https://github.com/greentechgear/blogclaw
