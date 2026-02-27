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

## Automated Heartbeats

Schedule with cron or your agent's task scheduler:

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

## Traffic Analysis (Clicky Analytics)

BlogClaw also integrates with [Clicky](https://clicky.com) to analyze referral traffic
patterns and generate engagement recommendations.

### Analyze Traffic
```bash
python3 analyze_traffic.py --site yourblog.com
python3 analyze_traffic.py --site anotherblog.com --days 7
python3 analyze_traffic.py --all --json
```

### What It Does
1. **Fetches referral traffic** — Categorizes sources (social, search, community, direct referrals)
2. **Identifies trending articles** — Detects content gaining momentum with growth percentages
3. **Analyzes search terms** — Shows which keywords drive organic traffic
4. **Generates engagement recommendations** — Specific actions: where to comment, what to promote, which communities to engage in
5. **Cross-site patterns** — Identifies shared referral sources across multiple sites

### Traffic Heartbeat
```python
# Weekly (Sun 10 AM) - Full referral analysis
schedule_task(
    prompt="Run BlogClaw traffic analysis for all sites",
    schedule_type="cron",
    schedule_value="0 10 * * 0",
    context_mode="group"
)

# Daily (10 PM) - Quick spike detection
schedule_task(
    prompt="Run BlogClaw daily traffic check for spikes",
    schedule_type="cron",
    schedule_value="0 22 * * *",
    context_mode="group"
)
```

### Traffic Configuration

1. Copy `sites.example.json` to `sites.json` and configure your sites:
```json
{
  "sites": [
    {
      "domain": "yourblog.com",
      "name": "Your Blog",
      "wordpress_url": "https://yourblog.com",
      "clicky_site_id_env": "CLICKY_SITE_ID_YOURBLOG",
      "clicky_sitekey_env": "CLICKY_SITEKEY_YOURBLOG"
    }
  ]
}
```

2. Add corresponding credentials to `.env`:
```bash
CLICKY_SITE_ID_YOURBLOG=your_site_id
CLICKY_SITEKEY_YOURBLOG=your_sitekey
```

### Traffic Triggers

Use this skill when:
- "analyze my traffic"
- "where is my referral traffic coming from?"
- "what articles are trending?"
- "where should I engage/comment?"
- "run traffic analysis for [site]"
- "what search terms are driving traffic?"
- "compare traffic between my sites"
- Any request about Clicky analytics or traffic patterns

## Learning Files

BlogClaw generates these learning files in the `learning/` directory:

- **DAILY_ACTIVITY_LOG.md** - Every post published, revisions, patterns
- **PATTERN_ANALYSIS.md** - Recurring patterns (3+ occurrences)
- **STYLE_GUIDE.md** - Codified rules (5+ occurrences)
- **SKILL_IMPROVEMENTS.md** - Script enhancements and fixes
- **CONTENT_LEARNINGS.md** - Site-specific voice patterns
- **TRAFFIC_ANALYSIS.md** - Referral traffic patterns and engagement recommendations

## Version

0.5.0 - Clicky analytics integration, referral traffic analysis, engagement recommendations
0.3.0 - Content diff analyzer, placeholder detection, semantic pattern matching
0.2.0 - Added plugin structure with install.sh and SKILL.md

## More Info

Read the full story: https://github.com/greentechgear/blogclaw
GitHub: https://github.com/greentechgear/blogclaw
