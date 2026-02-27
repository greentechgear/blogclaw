#!/usr/bin/env python3
"""
BlogClaw Monthly Heartbeat - Runs 1st of month at 8 AM
Measures quality metrics and codifies patterns into style guide
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import re
from collections import Counter

def parse_pattern_analysis(pattern_path):
    """Parse PATTERN_ANALYSIS.md and extract patterns with 5+ occurrences"""

    if not pattern_path.exists():
        return []

    with open(pattern_path) as f:
        content = f.read()

    # Extract patterns with frequency
    pattern_blocks = re.findall(
        r'### Pattern \d+: (.*?)\n.*?Frequency:\*\* (\d+) occurrences',
        content,
        re.DOTALL
    )

    codifiable = []
    for pattern_name, frequency in pattern_blocks:
        freq = int(frequency)
        if freq >= 5:
            codifiable.append({
                'name': pattern_name.strip(),
                'frequency': freq
            })

    return codifiable

def calculate_quality_metrics(daily_log_path):
    """Calculate month-over-month quality metrics"""

    if not daily_log_path.exists():
        return {}

    with open(daily_log_path) as f:
        content = f.read()

    # Extract revision counts from last 30 days
    revision_counts = re.findall(r'Revisions?: (\d+)', content)
    revisions = [int(r) for r in revision_counts]

    # Extract word count additions
    word_additions = re.findall(r'\+(\d+)\s+words', content)
    words_added = [int(w) for w in word_additions]

    # Count critical bugs
    critical_bugs = content.count('CRITICAL') + content.count('RED:')

    # Count em-dash occurrences
    em_dash_count = content.count('em-dash') + content.count('em dash')

    metrics = {
        'avg_revisions': sum(revisions) / len(revisions) if revisions else 0,
        'total_posts': len(revisions),
        'avg_content_expansion': sum(words_added) / len(words_added) if words_added else 0,
        'critical_bugs': critical_bugs,
        'style_violations': em_dash_count
    }

    return metrics

def update_style_guide(codifiable_patterns, style_guide_path):
    """Update STYLE_GUIDE.md with codified patterns (5+ occurrences)"""

    # Read existing style guide or create new
    if style_guide_path.exists():
        with open(style_guide_path) as f:
            existing_content = f.read()
    else:
        existing_content = """# Style Guide

Auto-generated from BlogClaw pattern analysis (5+ occurrences)

---

"""

    additions = []

    for pattern in codifiable_patterns:
        # Skip if already in style guide
        if pattern['name'] in existing_content:
            continue

        additions.append(f"\n## {pattern['name']} (Codified Pattern)\n\n")
        additions.append(f"**Frequency:** {pattern['frequency']} occurrences\n")
        additions.append(f"**Status:** Codified rule (enforce in all drafts)\n\n")

        # Add specific rules based on pattern type
        if 'Em-Dash' in pattern['name']:
            additions.append("**Rule:** Never use em-dashes (—) in blog content\n")
            additions.append("**Replacement:** Use commas, periods, or parentheses instead\n\n")

        elif 'Content Depth' in pattern['name'] or 'Content Expansion' in pattern['name']:
            additions.append("**Rule:** All articles must include:\n")
            additions.append("- Business context section (\"Why This Matters\")\n")
            additions.append("- Minimum 1500 words for technical tutorials\n")
            additions.append("- Concrete examples with real data\n\n")

        elif 'Structure' in pattern['name']:
            additions.append("**Rule:** Preferred article structure:\n")
            additions.append("1. Hook with data or controversy\n")
            additions.append("2. \"Why This Matters\" section (near top, not buried)\n")
            additions.append("3. Technical details after value prop\n")
            additions.append("4. Examples and edge cases\n")
            additions.append("5. Conclusion with next steps\n\n")

    if additions:
        with open(style_guide_path, 'a') as f:
            f.writelines(additions)

        print(f"✓ Added {len(additions)} new rules to {style_guide_path}")
    else:
        print(f"✓ No new patterns to codify (all existing patterns already in style guide)")

def generate_monthly_report(metrics, codifiable_patterns, report_path):
    """Generate monthly evolution report"""

    lines = [
        "# Monthly Evolution Report\n",
        f"Generated: {datetime.now().strftime('%B %Y')}\n\n",
        "## Quality Metrics\n\n",
        f"- **Posts analyzed:** {int(metrics.get('total_posts', 0))}\n",
        f"- **Avg revisions per post:** {metrics.get('avg_revisions', 0):.1f}\n",
        f"- **Avg content expansion:** +{int(metrics.get('avg_content_expansion', 0))} words\n",
        f"- **Critical bugs:** {metrics.get('critical_bugs', 0)}\n",
        f"- **Style violations:** {metrics.get('style_violations', 0)}\n\n",
        "## Codified Patterns (5+ occurrences)\n\n"
    ]

    if codifiable_patterns:
        for pattern in codifiable_patterns:
            lines.append(f"- **{pattern['name']}** ({pattern['frequency']} occurrences) → Added to style guide\n")
    else:
        lines.append("- No patterns reached codification threshold this month\n")

    lines.append("\n## Next Month's Focus\n\n")
    lines.append("- Continue monitoring quality metrics\n")
    lines.append("- Reduce average revisions per post\n")
    lines.append("- Eliminate critical bugs\n")
    lines.append("- Achieve zero style guide violations\n")

    with open(report_path, 'w') as f:
        f.writelines(lines)

    print(f"✓ Generated {report_path}")

def main():
    parser = argparse.ArgumentParser(description='BlogClaw Monthly Evolution Check')
    parser.add_argument('--learning-dir', default='learning', help='Learning files directory')

    args = parser.parse_args()

    print("BlogClaw Monthly Heartbeat")
    print(f"Month: {datetime.now().strftime('%B %Y')}\n")

    learning_dir = Path(args.learning_dir)
    learning_dir.mkdir(parents=True, exist_ok=True)

    # Calculate quality metrics
    daily_log_path = learning_dir / 'DAILY_ACTIVITY_LOG.md'
    metrics = calculate_quality_metrics(daily_log_path)

    print("Quality Metrics:")
    print(f"  Posts analyzed: {int(metrics.get('total_posts', 0))}")
    print(f"  Avg revisions: {metrics.get('avg_revisions', 0):.1f}")
    print(f"  Avg expansion: +{int(metrics.get('avg_content_expansion', 0))} words")
    print(f"  Critical bugs: {metrics.get('critical_bugs', 0)}")
    print(f"  Style violations: {metrics.get('style_violations', 0)}\n")

    # Find patterns to codify (5+ occurrences)
    pattern_path = learning_dir / 'PATTERN_ANALYSIS.md'
    codifiable = parse_pattern_analysis(pattern_path)

    print(f"Patterns ready for codification (5+): {len(codifiable)}")

    # Update style guide
    style_guide_path = learning_dir / 'STYLE_GUIDE.md'
    update_style_guide(codifiable, style_guide_path)

    # Generate monthly report
    report_path = learning_dir / f"MONTHLY_REPORT_{datetime.now().strftime('%Y_%m')}.md"
    generate_monthly_report(metrics, codifiable, report_path)

    print(f"\n✓ Monthly heartbeat complete")
    print(f"  Metrics calculated: {len(metrics)}")
    print(f"  Patterns codified: {len(codifiable)}")

if __name__ == '__main__':
    main()
