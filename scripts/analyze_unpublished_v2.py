#!/usr/bin/env python3
"""
BlogClaw - Enhanced Unpublished Draft Analyzer (v2)

Analyzes TOPIC and CONTENT patterns in drafts that haven't been published.
Goes beyond word count to identify:
- Future speculation vs retrospective analysis
- Personal narrative vs generic content
- Duplicate topics
- Wrong audience signals
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# Pattern detection markers
FUTURE_SPECULATION_MARKERS = [
    'is going to', 'will change', 'will transform', 'the future of',
    'could change', 'might change', 'is set to', 'are going to'
]

RETROSPECTIVE_MARKERS = [
    'i built', 'i learned', 'i discovered', 'here\'s what happened',
    'when i', 'i tried', 'i found', 'here\'s what i', 'i made'
]

SETUP_GUIDE_MARKERS = [
    'setting up', 'how to', 'step-by-step', 'guide to', 'tutorial',
    'getting started with', 'install', 'configure'
]

PROMOTIONAL_MARKERS = [
    'announcing', 'introducing', 'launching', 'relaunch', 'why you should',
    'you should too', 'why i trust', 'the case for'
]

def clean_text_for_analysis(content):
    """Remove frontmatter and code blocks for analysis"""
    if content.startswith('---'):
        parts = content.split('---', 2)
        content = parts[2] if len(parts) > 2 else content

    # Remove code blocks
    content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)

    return content.lower()

def detect_future_speculation(content):
    """Check for future speculation markers"""
    text = clean_text_for_analysis(content)
    matches = sum(1 for marker in FUTURE_SPECULATION_MARKERS if marker in text)
    return matches

def detect_retrospective_narrative(content):
    """Check for retrospective/personal experience markers"""
    text = clean_text_for_analysis(content)
    matches = sum(1 for marker in RETROSPECTIVE_MARKERS if marker in text)
    return matches

def detect_setup_guide(content):
    """Check for setup guide / tutorial markers"""
    text = clean_text_for_analysis(content)
    matches = sum(1 for marker in SETUP_GUIDE_MARKERS if marker in text)
    return matches

def detect_promotional(content):
    """Check for promotional content markers"""
    text = clean_text_for_analysis(content)
    matches = sum(1 for marker in PROMOTIONAL_MARKERS if marker in text)
    return matches

def calculate_first_person_density(content):
    """Calculate density of first-person narrative"""
    text = clean_text_for_analysis(content)
    words = text.split()
    if not words:
        return 0.0

    first_person = ['i ', 'my ', 'me ', "i've", "i'm", "i'll"]
    count = sum(text.count(fp) for fp in first_person)
    return count / len(words)

def find_similar_titles(title, all_titles, threshold=0.6):
    """Find similar titles using basic word overlap"""
    title_words = set(title.lower().split())
    similar = []

    for other_title in all_titles:
        if title == other_title:
            continue
        other_words = set(other_title.lower().split())

        # Calculate Jaccard similarity
        if title_words and other_words:
            overlap = len(title_words & other_words)
            union = len(title_words | other_words)
            similarity = overlap / union if union > 0 else 0

            if similarity >= threshold:
                similar.append((other_title, similarity))

    return similar

def analyze_draft_enhanced(draft_path, all_titles):
    """Enhanced analysis with topic pattern detection"""
    with open(draft_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract title
    frontmatter = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"')

    title = frontmatter.get('title', Path(draft_path).stem)

    # Calculate patterns
    future_spec_score = detect_future_speculation(content)
    retro_score = detect_retrospective_narrative(content)
    setup_score = detect_setup_guide(content)
    promo_score = detect_promotional(content)
    first_person = calculate_first_person_density(content)

    # Find similar titles
    similar = find_similar_titles(title, all_titles)

    # Classify
    issues = []
    if future_spec_score >= 2:
        issues.append("future speculation")
    if retro_score < 2:
        issues.append("lacks retrospective")
    if setup_score >= 2:
        issues.append("setup guide (consider Consultdex)")
    if promo_score >= 2:
        issues.append("promotional content")
    if first_person < 0.02:
        issues.append("lacks personal narrative")
    if similar:
        issues.append(f"duplicate topic ({len(similar)} similar)")

    # Get file age
    mtime = os.path.getmtime(draft_path)
    file_date = datetime.fromtimestamp(mtime)
    age = (datetime.now() - file_date).days

    return {
        'filename': Path(draft_path).name,
        'title': title,
        'age_days': age,
        'created_date': file_date.strftime('%Y-%m-%d'),
        'word_count': len(content.split()),
        'future_speculation_score': future_spec_score,
        'retrospective_score': retro_score,
        'setup_guide_score': setup_score,
        'promotional_score': promo_score,
        'first_person_density': round(first_person * 100, 1),
        'similar_drafts': similar,
        'issues': issues
    }

def analyze_unpublished_drafts_enhanced(drafts_dir, age_threshold=7):
    """Analyze all unpublished drafts with enhanced pattern detection"""
    drafts_path = Path(drafts_dir)
    if not drafts_path.exists():
        return []

    # Get all draft files
    draft_files = list(drafts_path.glob('*.md'))

    # Extract all titles first for duplicate detection
    all_titles = []
    for draft_file in draft_files:
        age = (datetime.now() - datetime.fromtimestamp(draft_file.stat().st_mtime)).days
        if age >= age_threshold:
            with open(draft_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        for line in parts[1].strip().split('\n'):
                            if line.startswith('title:'):
                                title = line.split(':', 1)[1].strip().strip('"')
                                all_titles.append(title)
                                break
                        else:
                            all_titles.append(draft_file.stem)
                    else:
                        all_titles.append(draft_file.stem)
                else:
                    all_titles.append(draft_file.stem)

    # Analyze each draft
    results = []
    for draft_file in draft_files:
        age = (datetime.now() - datetime.fromtimestamp(draft_file.stat().st_mtime)).days
        if age >= age_threshold:
            try:
                analysis = analyze_draft_enhanced(draft_file, all_titles)
                results.append(analysis)
            except Exception as e:
                print(f"Error analyzing {draft_file}: {e}", file=sys.stderr)

    # Sort by age (oldest first)
    results.sort(key=lambda x: x['age_days'], reverse=True)

    return results

def generate_enhanced_report(drafts, output_path):
    """Generate markdown report with topic pattern analysis"""
    with open(output_path, 'w') as f:
        f.write("# Unpublished Drafts Analysis (Enhanced)\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(f"**Total unpublished drafts (7+ days old):** {len(drafts)}\n\n")

        # Pattern summary
        f.write("## Topic Pattern Analysis\n\n")

        future_spec = sum(1 for d in drafts if d['future_speculation_score'] >= 2)
        lacks_retro = sum(1 for d in drafts if d['retrospective_score'] < 2)
        setup_guides = sum(1 for d in drafts if d['setup_guide_score'] >= 2)
        promotional = sum(1 for d in drafts if d['promotional_score'] >= 2)
        lacks_personal = sum(1 for d in drafts if d['first_person_density'] < 2.0)
        has_duplicates = sum(1 for d in drafts if d['similar_drafts'])

        total = len(drafts)

        f.write("**Content Type Patterns:**\n\n")
        f.write(f"- **Future Speculation**: {future_spec}/{total} ({future_spec/total*100:.0f}%)\n")
        f.write(f"  - Articles predicting trends rather than analyzing experiences\n\n")

        f.write(f"- **Lacks Retrospective**: {lacks_retro}/{total} ({lacks_retro/total*100:.0f}%)\n")
        f.write(f"  - Missing 'I built', 'I learned', 'Here's what happened' narrative\n\n")

        f.write(f"- **Setup Guides**: {setup_guides}/{total} ({setup_guides/total*100:.0f}%)\n")
        f.write(f"  - Tutorials/how-to content (better suited for Consultdex)\n\n")

        f.write(f"- **Promotional Content**: {promotional}/{total} ({promotional/total*100:.0f}%)\n")
        f.write(f"  - Announcements/launches without retrospective analysis\n\n")

        f.write(f"- **Lacks Personal Narrative**: {lacks_personal}/{total} ({lacks_personal/total*100:.0f}%)\n")
        f.write(f"  - Generic content without first-person perspective\n\n")

        f.write(f"- **Duplicate Topics**: {has_duplicates}/{total} ({has_duplicates/total*100:.0f}%)\n")
        f.write(f"  - Similar titles/topics to other unpublished drafts\n\n")

        # Key insight
        f.write("## Key Insight\n\n")
        f.write("**Published Pattern:** Brian publishes retrospective analysis of things he's actually done\n\n")
        f.write("**Rejected Pattern:** Brian rejects prospective speculation about things that might happen\n\n")
        f.write("- ✅ Published = 'Here's what I learned from doing X'\n")
        f.write("- ❌ Rejected = 'Here's what X could mean for the future'\n\n")

        # Individual drafts
        f.write("## Unpublished Drafts (by pattern)\n\n")

        # Group by primary issue
        by_issue = {}
        for draft in drafts:
            primary_issue = draft['issues'][0] if draft['issues'] else 'other'
            if primary_issue not in by_issue:
                by_issue[primary_issue] = []
            by_issue[primary_issue].append(draft)

        for issue_type, issue_drafts in sorted(by_issue.items()):
            f.write(f"### {issue_type.title()}\n\n")
            for draft in issue_drafts[:5]:  # Show top 5 per category
                f.write(f"**{draft['title']}**\n\n")
                f.write(f"- File: `{draft['filename']}`\n")
                f.write(f"- Age: {draft['age_days']} days\n")
                f.write(f"- Word count: {draft['word_count']}\n")
                f.write(f"- First-person density: {draft['first_person_density']}%\n")
                f.write(f"- Scores: Future={draft['future_speculation_score']}, Retro={draft['retrospective_score']}, Setup={draft['setup_guide_score']}\n")
                if draft['similar_drafts']:
                    f.write(f"- Similar to: {draft['similar_drafts'][0][0]}\n")
                f.write("\n")

        # Recommendations
        f.write("## Recommendations\n\n")
        f.write("**Before drafting new content, ask:**\n\n")
        f.write("❌ **DON'T DRAFT:**\n")
        f.write("- Is this speculating about future trends?\n")
        f.write("- Is this a setup guide without personal context?\n")
        f.write("- Is this promoting something not yet shipped?\n")
        f.write("- Is there already a similar draft unpublished?\n\n")

        f.write("✅ **DO DRAFT:**\n")
        f.write("- Is this analyzing something Brian actually built/did?\n")
        f.write("- Does it have specific examples from his experience?\n")
        f.write("- Does it challenge conventional wisdom with data?\n")
        f.write("- Is there a unique angle/parallel (like WoW → AI)?\n\n")

    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='Enhanced unpublished draft analyzer - detects topic patterns'
    )
    parser.add_argument('--drafts-dir', default='/workspace/group/blogging/drafts',
                       help='Path to drafts directory')
    parser.add_argument('--learning-dir', default='/workspace/group/blogging',
                       help='Path to learning directory')
    parser.add_argument('--age-threshold', type=int, default=7,
                       help='Minimum age in days to consider draft unpublished (default: 7)')
    parser.add_argument('--json', action='store_true',
                       help='Output JSON instead of generating report')

    args = parser.parse_args()

    print("BlogClaw - Enhanced Unpublished Draft Analysis (v2)\n")
    print(f"Analyzing drafts older than {args.age_threshold} days...\n")

    drafts = analyze_unpublished_drafts_enhanced(
        args.drafts_dir,
        args.age_threshold
    )

    if args.json:
        print(json.dumps(drafts, indent=2))
        return

    output_path = Path(args.learning_dir) / 'UNPUBLISHED_DRAFTS_ANALYSIS.md'
    generate_enhanced_report(drafts, output_path)

    print(f"✓ Analysis complete")
    print(f"  Unpublished drafts: {len(drafts)}")
    print(f"  Report: {output_path}\n")

    if drafts:
        print("Top patterns detected:")
        future_spec = sum(1 for d in drafts if d['future_speculation_score'] >= 2)
        lacks_retro = sum(1 for d in drafts if d['retrospective_score'] < 2)
        setup_guides = sum(1 for d in drafts if d['setup_guide_score'] >= 2)

        if future_spec:
            print(f"  • {future_spec} drafts contain future speculation")
        if lacks_retro:
            print(f"  • {lacks_retro} drafts lack retrospective narrative")
        if setup_guides:
            print(f"  • {setup_guides} drafts are setup guides (consider Consultdex)")

if __name__ == '__main__':
    main()
