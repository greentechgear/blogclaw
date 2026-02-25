# Content Learnings - [Your Site Name]

Site-specific learnings for your blog. Tracks what works, what doesn't, and your consistent preferences.

**Voice:** [Describe your writing voice]
**Style Guide:** See `STYLE_GUIDE.md` for comprehensive reference

---

## Voice Patterns That Resonate

### Signature Moves
- [Your recurring intros, transitions, conclusions]
- [Unique phrases you use]
- [Structural patterns you prefer]

### Common Phrases (track frequency)
- "[Your phrase 1]" -> [track usage]
- "[Your phrase 2]" -> [track usage]

---

## Manual Edits You Make

Track WordPress revisions to learn your preferences and reduce future edits.

### Structure Edits
*To be tracked from WordPress revision API*

### Tone Adjustments
*To be tracked from WordPress revision API*

### Content Additions
*To be tracked from WordPress revision API*

---

## Topics That Perform Well

### [Topic Category 1]
- [Article title]: [What resonated]

### [Topic Category 2]
*To be tracked*

---

## What to Avoid

### Tone
- [Things that don't match your voice]

### Structure
- [Structural patterns that don't work]

---

## Learning From Revisions

**Process:**
1. Daily heartbeat checks WordPress revisions for posts published today
2. Compare original AI-generated content vs your edits
3. Categorize edits (structure, tone, content, facts)
4. Identify patterns (3+ similar edits = update style guide)
5. Feed learnings back into reviewer

**Revision Check:**
```bash
# WordPress API endpoint for revisions
GET /wp-json/wp/v2/posts/{id}/revisions
```

---

## Metrics to Track

| Metric | Current | Trend | Goal |
|--------|---------|-------|------|
| Manual edits per post | TBD | - | <3 |
| Time to publish (draft to live) | TBD | - | <30 min |
| Tone corrections | TBD | - | 0 |
| Structure changes | TBD | - | <2 |
