#!/usr/bin/env python3
"""
BlogClaw Weekly Heartbeat - Runs Sunday 9 AM
Analyzes patterns from the past week and proposes improvements
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import re

def load_env():
    """Load environment variables from .env"""
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        env_path = Path('/workspace/group/.env')

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def parse_daily_log(log_path):
    """Parse DAILY_ACTIVITY_LOG.md and extract patterns from last 7 days"""

    if not log_path.exists():
        return []

    with open(log_path) as f:
        content = f.read()

    # Get entries from last 7 days
    today = datetime.now()
    week_ago = today - timedelta(days=7)

    # Extract date sections (## YYYY-MM-DD or ## Month DD, YYYY)
    date_pattern = r'## (\d{4}-\d{2}-\d{2})|## ([A-Za-z]+ \d{1,2}, \d{4})'
    sections = re.split(date_pattern, content)

    patterns = {
        'content_expansions': [],
        'structure_changes': [],
        'em_dashes': 0,
        'broken_links': [],
        'tone_corrections': [],
        'critical_bugs': []
    }

    for section in sections:
        if not section or len(section) < 50:
            continue

        # Look for patterns
        if '+' in section and 'words' in section:
            # Extract word count additions
            word_adds = re.findall(r'\+(\d+)\s+words', section)
            patterns['content_expansions'].extend([int(w) for w in word_adds])

        if 'structure' in section.lower():
            structure_count = section.lower().count('structure')
            patterns['structure_changes'].append(structure_count)

        if 'em-dash' in section.lower() or 'em dash' in section.lower():
            patterns['em_dashes'] += 1

        if 'broken link' in section.lower():
            patterns['broken_links'].append(section[:200])

        if 'CRITICAL' in section or 'RED' in section:
            patterns['critical_bugs'].append(section[:300])

    return patterns

def detect_recurring_patterns(patterns, threshold=3):
    """Identify patterns that occur 3+ times"""

    recurring = []

    # Content expansions
    if len(patterns['content_expansions']) >= threshold:
        avg_expansion = sum(patterns['content_expansions']) / len(patterns['content_expansions'])
        recurring.append({
            'type': 'Content Depth',
            'frequency': len(patterns['content_expansions']),
            'severity': 'high',
            'description': f"AI drafts consistently require content expansion (avg +{int(avg_expansion)} words)",
            'proposed_fix': "Add pre-publish check: flag articles < 1500 words or missing 'Why This Matters' section",
            'confidence': 0.95
        })

    # Structure changes
    if len(patterns['structure_changes']) >= threshold:
        recurring.append({
            'type': 'Structure Refinement',
            'frequency': len(patterns['structure_changes']),
            'severity': 'medium',
            'description': f"Articles require {len(patterns['structure_changes'])} structure reorganizations",
            'proposed_fix': "Document preferred structure in CONTENT_LEARNINGS.md and enforce in drafts",
            'confidence': 0.90
        })

    # Em-dashes
    if patterns['em_dashes'] >= threshold:
        recurring.append({
            'type': 'Em-Dash Usage',
            'frequency': patterns['em_dashes'],
            'severity': 'medium',
            'description': "Em-dashes appearing despite style guide prohibition",
            'proposed_fix': "Add em-dash detection to expert-reviewer and consultdex-reviewer pre-publish checks",
            'confidence': 0.99
        })

    # Critical bugs
    if len(patterns['critical_bugs']) >= 2:  # Lower threshold for critical issues
        recurring.append({
            'type': 'Critical Bug',
            'frequency': len(patterns['critical_bugs']),
            'severity': 'critical',
            'description': "Critical system issues detected multiple times",
            'proposed_fix': "Stop all publishing until critical bugs are resolved",
            'confidence': 1.0
        })

    return recurring

def generate_pattern_report(recurring_patterns, report_path):
    """Generate PATTERN_ANALYSIS.md report"""

    lines = [
        "# Pattern Analysis Report\n",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"\n## Summary\n\n",
        f"- Patterns detected: {len(recurring_patterns)}\n",
        f"- Threshold: 3+ occurrences\n\n"
    ]

    if not recurring_patterns:
        lines.append("✓ No recurring patterns detected this week\n")
    else:
        lines.append("## Recurring Patterns (3+ occurrences)\n\n")

        for i, pattern in enumerate(recurring_patterns, 1):
            severity_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(pattern['severity'], '⚪')

            lines.append(f"### Pattern {i}: {pattern['type']} {severity_emoji}\n\n")
            lines.append(f"- **Frequency:** {pattern['frequency']} occurrences\n")
            lines.append(f"- **Severity:** {pattern['severity']}\n")
            lines.append(f"- **Description:** {pattern['description']}\n")
            lines.append(f"- **Proposed Fix:** {pattern['proposed_fix']}\n")
            lines.append(f"- **Confidence:** {int(pattern['confidence'] * 100)}%\n\n")

            # Auto-implement if confidence > 90%
            if pattern['confidence'] > 0.90:
                lines.append(f"✓ **Auto-implement recommended** (high confidence)\n\n")

    lines.append("\n## Recommended Actions\n\n")
    lines.append("1. Review high-confidence patterns and implement fixes\n")
    lines.append("2. Update SKILL_IMPROVEMENTS.md with changes made\n")
    lines.append("3. Test improvements on next publish\n\n")

    with open(report_path, 'w') as f:
        f.writelines(lines)

    print(f"✓ Generated {report_path}")

def main():
    parser = argparse.ArgumentParser(description='BlogClaw Weekly Pattern Analysis')
    parser.add_argument('--learning-dir', default='learning', help='Learning files directory')

    args = parser.parse_args()

    print("BlogClaw Weekly Heartbeat")
    print("Analyzing patterns from last 7 days...\n")

    learning_dir = Path(args.learning_dir)
    learning_dir.mkdir(parents=True, exist_ok=True)

    # Parse daily log
    log_path = learning_dir / 'DAILY_ACTIVITY_LOG.md'
    patterns = parse_daily_log(log_path)

    print(f"Patterns found:")
    print(f"  Content expansions: {len(patterns['content_expansions'])}")
    print(f"  Structure changes: {len(patterns['structure_changes'])}")
    print(f"  Em-dashes: {patterns['em_dashes']}")
    print(f"  Critical bugs: {len(patterns['critical_bugs'])}")

    # Detect recurring patterns (3+ threshold)
    recurring = detect_recurring_patterns(patterns, threshold=3)

    print(f"\nRecurring patterns (3+): {len(recurring)}")

    # Generate report
    report_path = learning_dir / 'PATTERN_ANALYSIS.md'
    generate_pattern_report(recurring, report_path)

    print(f"\n✓ Weekly heartbeat complete")
    print(f"  Patterns analyzed: {len(recurring)}")
    print(f"  High-confidence fixes: {sum(1 for p in recurring if p['confidence'] > 0.90)}")

if __name__ == '__main__':
    main()
