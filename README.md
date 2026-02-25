# BlogClaw

**A self-improving blog system that learns from your WordPress edits.**

BlogClaw is part of the [OpenClaw](https://github.com/greentechgear) ecosystem, built on [NanoClaw](https://github.com/gavrielc/nanoclaw) — an AI agent orchestrator that runs Claude (or other LLMs) in isolated Docker containers with Telegram integration.

BlogClaw's components (scripts, templates, learning files) are plain Python and Markdown. They work as a NanoClaw plugin out of the box, but can be adapted to any AI agent framework that can run bash commands, read/write files, and follow instructions.

---

## The Problem: AI Needs 20+ Edits Per Post

Last week I published an article about Claw Marketing. The AI draft looked decent. Then I opened WordPress and started editing.

Twenty-three revisions later, the post was ready to publish.

That's not unusual. My recent workflow tutorials averaged 15-20 revisions each. One article needed 22 edits and a +655 word content expansion.

The AI was writing my blog posts, but I was still writing my voice.

## Enter: The Self-Improving Loop

Inspired by Caleb Denio's [Dog Game technique](https://www.calebleak.com/posts/dog-game/) — where he gave his AI tools to observe its own output and iterate — I built something similar for my blog.

The system:
1. **Tracks every WordPress revision** I make during the drafting process
2. **Analyzes patterns** in my edits (content additions, structure changes, tone adjustments)
3. **Updates style guides automatically** when it detects recurring patterns (3+ occurrences)
4. **Improves the next draft** based on learned patterns

## How It Actually Works

### The Learning Files

The system maintains five interconnected learning files (templates included in `templates/`):

- **DAILY_ACTIVITY_LOG.md** — Every edit, publish, and reviewer run logged daily
- **PATTERN_ANALYSIS.md** — Weekly analysis of recurring issues (3+ occurrences = pattern)
- **SKILL_IMPROVEMENTS.md** — Documents all enhancements to scripts and reviewers
- **CONTENT_LEARNINGS.md** — Your blog voice patterns (one per site)
- **STYLE_GUIDE.md** — Your comprehensive writing style reference

### The Heartbeats

Three automated scheduled tasks run the learning loops:

**Daily Review (11 PM):**
- Fetches all WordPress revisions for posts published today
- Compares revision-to-revision content changes
- Identifies what you added, deleted, reorganized
- Updates DAILY_ACTIVITY_LOG.md

**Weekly Pattern Analysis (Sunday 9 AM):**
- Reviews full week of activity logs
- Identifies patterns: 3+ similar issues = actionable pattern
- Proposes improvements (script updates, reviewer enhancements, style guide changes)
- Auto-implements high-confidence fixes (90%+ certainty)

**Monthly Evolution Check (1st of month 8 AM):**
- Measures quality metrics month-over-month
- Updates style guide with codified patterns (5+ occurrences)
- Sets next month's improvement targets

### The Revision Analyzer

`analyze_revisions.py` fetches WordPress revision history and categorizes your editing patterns:

**Step 1: Fetch WordPress Revisions**

WordPress REST API endpoint:
```
GET /wp-json/wp/v2/posts/{post_id}/revisions
```

Returns all revisions for a post, including full HTML content and timestamps.

**Step 2: Compare Adjacent Revisions**

For each pair of consecutive revisions:
- Strip HTML tags to get plain text
- Calculate word count delta
- Extract added/removed sections (H2 headers via regex)
- Identify structure changes (heading reordering)

**Step 3: Categorize Changes**

Each revision change gets tagged:
- **Content expansion** (100+ words added)
- **Structure refinement** (headings moved/added/removed)
- **Iterative polish** (small changes < 50 words)

**Step 4: Pattern Detection**

When 3+ posts show the same issue:
- Log pattern in PATTERN_ANALYSIS.md
- Propose fix (script update, reviewer check, style guide addition)
- If confidence > 90%, auto-implement

**Step 5: Update Style Guides**

When 5+ posts show the same voice pattern:
- Document in your style guide
- Make it a rule, not a suggestion
- Feed into next AI draft prompt

## What It Learned in Week One

I ran the system on three articles. Here's what it discovered.

### Pattern #1: AI Drafts Lack Depth

**Data:**
- Article A: 23 revisions over 2 days
- Article B: 22 revisions, **+655 words added**
- Article C: 8 revisions (most efficient)

Article B needed a massive content expansion. I added an entire "Why This Matters" section — 655 words the AI never generated.

**Why it happened:** AI drafts hit the main points but miss the *context* that makes them matter. The missing section answered "So what?" It connected abstract capabilities to concrete business value.

**System response:** Added "content depth check" to the reviewer. If articles lack business context sections, flag for expansion before publish.

### Pattern #2: Structure Gets Reorganized 4-5 Times

**Data:**
- Article A: 4 structure reorganizations
- Article B: 5 structure changes
- Article C: Minimal restructuring

I kept moving sections around. The AI writes linearly (intro -> body -> conclusion), but I think associatively. I want the "aha moment" near the top, technical details in the middle, philosophical implications at the end.

**Why it happened:** AI optimizes for logical flow. I optimize for *reader engagement*. Those aren't the same thing.

**System response:** Documented preferred article structure in CONTENT_LEARNINGS.md:
- Hook with data or controversy
- "Why this matters" section near top (not buried in conclusion)
- Technical details after the value prop is established
- Sidebars for tangential but interesting context

### Pattern #3: The "Polish Pass" is Where Voice Lives

**Data:**
- Article A: 12 small edits after structure was finalized
- These weren't fixing errors — they were injecting *personality*

Changes like:
- "This is important" -> "Enter: The important thing"
- "The data shows..." -> "Fast forward to the data..."
- Generic transition -> Sidebar with historical parallel

**Why it happened:** Voice isn't about *what* you say, it's about *how* you say it. The AI gets the information right. I add the personal touch.

**System response:** Harder to systematize. Can't just tell the AI "sound more like me." But I can document signature moves:
- "Enter:" intros for new concepts
- "Fast forward to..." for time jumps
- Sidebars for tangential context
- Honest admissions ("I was wrong about X")
- Name-dropping with specificity ("John Mueller from Google" not just "Google")

## The Creepy Part: When It Works Too Well

Article C only needed 8 revisions. That's efficient, right?

Maybe *too* efficient.

When I reviewed the draft, it already had:
- Proper structure (value prop before technical details)
- Depth in the right places (business context present)
- My voice patterns (sidebars, specific name-drops)

It felt like reading something I'd already written.

There's a philosophical question here: If the AI learns your voice so well that you can't tell the difference, did *you* write it?

I'm not sure I have a good answer yet. But I know this: **The system still needed my 8 edits.** Whatever those final touches are, they're something the AI can observe but not yet replicate.

## The Mistake I Almost Made

Initially, my daily heartbeat only checked for edits made *after* publishing — the "oh crap I published a typo" emergency fixes.

That's not where the learning data lives.

The real edits — the 23 revisions, the +655 word expansions, the 4-5 structure reorganizations — happen *during* the drafting process. I was looking for post-publish corrections and missing 99% of my actual editing patterns.

Once I fixed that (analyzing full revision history, not just post-publish), the patterns became obvious.

**Lesson:** Don't optimize for the wrong metric. I thought "fewer post-publish edits = success." Wrong. I should have been tracking "fewer revisions needed during drafting = AI learning my voice."

## What It Still Gets Wrong

### False Positives in Pattern Detection

The system flagged "ngl" as casual language in professional articles.

Except it was detecting "ngl" inside the word "single."

**Fix:** Changed pattern matching from substring to word-boundary regex (`\bngl\b` instead of just `ngl`).

But this reveals a broader issue: The system can detect patterns mechanically but can't evaluate *why* they matter. It needs human judgment to distinguish signal from noise.

### The Context Problem

The system learned "author adds 600+ words to AI drafts" but not *what kind* of words.

I'm not padding. I'm adding:
- Business value explanations ("Why this matters for the reader")
- Real-world examples ("Here's how Company X uses this")
- Edge cases and gotchas ("This breaks when Y happens")

The AI can count words. It can't yet generate the *type* of content I'm adding.

**Next iteration:** Build content diff analyzer that extracts *what* you're adding, not just *how much*. Learn the themes, not just the metrics.

## Installation

### Prerequisites

- [NanoClaw](https://github.com/gavrielc/nanoclaw) installed and running
- A WordPress site with REST API enabled
- WordPress application password ([how to create one](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/))
- Python 3.9+

### Setup (NanoClaw Plugin)

1. **Copy the learning file templates** into your NanoClaw blogging group folder:

```bash
# From your nanoclaw root
cp -r /path/to/blogclaw/templates/* groups/tg-your-blogging-group/blogging/
```

2. **Copy the revision analyzer** into your group's skills:

```bash
cp /path/to/blogclaw/analyze_revisions.py groups/tg-your-blogging-group/.claude/skills/
```

3. **Set up environment variables** in your group's `.env`:

```bash
WORDPRESS_URL=https://yoursite.com
WORDPRESS_USERNAME=admin
WORDPRESS_PASSWORD=your-application-password
```

4. **Add the heartbeats** to your group's CLAUDE.md — tell your AI agent to run these on a schedule:

```
Daily Review (11 PM): Analyze today's WordPress revisions, update DAILY_ACTIVITY_LOG.md
Weekly Pattern Analysis (Sunday 9 AM): Review week's logs, identify 3+ patterns, update PATTERN_ANALYSIS.md
Monthly Evolution (1st of month): Codify 5+ patterns into style guide, set next month's targets
```

5. **Create your style guide** using `templates/STYLE_GUIDE_TEMPLATE.md` as a starting point. See `templates/EXAMPLE_STYLE_GUIDE.md` for a completed example.

### Standalone Usage (Without NanoClaw)

The revision analyzer works as a standalone CLI tool:

```bash
pip install -r requirements.txt

# Analyze a single post
python3 analyze_revisions.py \
  --site https://yoursite.com \
  --post-id 42 \
  --title "My Blog Post" \
  --username admin \
  --password your-app-password

# Analyze multiple posts from a config file
python3 analyze_revisions.py --config posts.json --json
```

Example `posts.json`:
```json
{
  "posts": [
    {
      "site": "https://yoursite.com",
      "id": 42,
      "title": "My First Post",
      "username": "admin",
      "password": "your-app-password"
    },
    {
      "site": "https://yoursite.com",
      "id": 55,
      "title": "My Second Post"
    }
  ]
}
```

The learning files and style guides need to be maintained by an AI agent (or manually). The standalone analyzer gives you the raw data; the AI interprets it.

## Architecture

```
BlogClaw (this repo)
  Scripts + Templates + Learning Files
  100% LLM-agnostic (Python + Markdown)
         |
         v
NanoClaw (orchestrator)
  Scheduling, Telegram, Docker, IPC
  Also LLM-agnostic
         |
         v
Agent Runner (inside container)
  Currently uses Claude Agent SDK
  Swap this one layer to change LLMs
```

BlogClaw never touches the LLM directly. It ships:
- **Python scripts** that run as CLI tools (any AI can call them)
- **Markdown files** that any AI can read and write
- **SKILL.md descriptions** that tell the AI what tools are available

To use with a different AI framework, you just need an agent that can run bash commands, read/write files, and follow instructions.

## Several Trends Emerge

After one week of data:

1. **Efficiency is increasing.** Article C (8 revisions) vs Article A (23 revisions). The system is learning.

2. **Some patterns can't be systematized.** The "polish pass" is still manual. Voice lives in the details the AI can observe but not replicate.

3. **The learning loop compounds.** Each improvement makes the next draft better, which generates better data, which enables better improvements.

4. **The creepy threshold is real.** When AI gets too good at mimicking you, it raises identity questions nobody's equipped to answer.

## Roadmap

**Short term (next month):**
- Content diff analyzer (extract *what* you're adding, not just word counts)
- Better placeholder detection (stop flagging `${VARIABLES}` as errors)
- Semantic pattern matching (understand *why* patterns matter, not just frequency)

**Medium term (3-6 months):**
- Multi-site learning (cross-pollinate patterns across blogs)
- Predictive revision suggestions ("Based on past patterns, you'll probably want to add a business value section here")

**Long term (aspirational):**
- The system writes first drafts indistinguishable from your final output
- You become editor-in-chief instead of writer
- Philosophical crisis about authorship and identity

## License

MIT — Fork it, break it, improve it. If you build something interesting on top of this, open an issue and let me know.

## Credits

- Built on [NanoClaw](https://github.com/gavrielc/nanoclaw) by Gavriel Cohen
- Inspired by Caleb Denio's [Dog Game technique](https://www.calebleak.com/posts/dog-game/)
- Part of the [OpenClaw](https://github.com/greentechgear) ecosystem
