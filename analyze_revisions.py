#!/usr/bin/env python3
"""
BlogClaw - WordPress Revision Analyzer
Analyzes revision history to learn from your editing patterns.

Part of the BlogClaw self-improving blog system.
Built on the OpenClaw / NanoClaw ecosystem.

Usage:
    python3 analyze_revisions.py --site https://yoursite.com --post-id 123 --username admin
    python3 analyze_revisions.py --config posts.json

Environment variables:
    WORDPRESS_URL       - Your WordPress site URL
    WORDPRESS_USERNAME  - WordPress username
    WORDPRESS_PASSWORD  - WordPress application password

Requirements:
    pip install requests
"""

import os
import sys
import json
import argparse
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path
from datetime import datetime, timezone
import re
from difflib import SequenceMatcher
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    """Strip HTML tags to extract plain text for comparison."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)


def strip_html(html):
    """Strip HTML tags to get plain text."""
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def analyze_content_changes(old_content, new_content):
    """
    Analyze what changed between two revisions.

    Compares plain text (HTML stripped) for word count deltas,
    and uses regex on raw HTML for structural changes (header additions/removals).
    """
    old_text = strip_html(old_content)
    new_text = strip_html(new_content)

    changes = {
        'word_count_change': len(new_text.split()) - len(old_text.split()),
        'additions': [],
        'deletions': [],
        'structure_changes': []
    }

    # Detect structure changes (any header modification)
    old_headers = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', old_content)
    new_headers = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', new_content)

    if old_headers != new_headers:
        changes['structure_changes'].append('Headers modified')

    # Detect new/removed H2 sections
    old_sections = set(re.findall(r'<h2[^>]*>(.*?)</h2>', old_content))
    new_sections = set(re.findall(r'<h2[^>]*>(.*?)</h2>', new_content))

    added_sections = new_sections - old_sections
    removed_sections = old_sections - new_sections

    if added_sections:
        changes['additions'].extend([f"Section: {s}" for s in added_sections])
    if removed_sections:
        changes['deletions'].extend([f"Section: {s}" for s in removed_sections])

    return changes


def analyze_post_revisions(base_url, post_id, post_title, auth):
    """
    Fetch and analyze all revisions for a WordPress post.

    Args:
        base_url: WordPress site URL (e.g. https://yoursite.com)
        post_id: WordPress post ID
        post_title: Post title (for display)
        auth: Tuple of (username, password)

    Returns:
        dict with revision analysis, or None on failure
    """
    url = f"{base_url}/wp-json/wp/v2/posts/{post_id}/revisions?per_page=100"

    try:
        response = requests.get(url, auth=HTTPBasicAuth(*auth), timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching revisions: {e}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code} for post {post_id}", file=sys.stderr)
        return None

    revisions = response.json()

    analysis = {
        'post_title': post_title,
        'site': base_url,
        'total_revisions': len(revisions),
        'revision_patterns': [],
        'major_additions': [],
        'structure_changes': 0,
        'iterative_refinements': 0
    }

    # Analyze revision-to-revision changes
    for i in range(len(revisions) - 1):
        curr = revisions[i]
        prev = revisions[i + 1]

        changes = analyze_content_changes(
            prev['content']['rendered'],
            curr['content']['rendered']
        )

        # Track major additions (100+ words added)
        if changes['word_count_change'] > 100:
            analysis['major_additions'].append({
                'words_added': changes['word_count_change'],
                'sections': changes['additions'],
                'timestamp': curr['date']
            })

        # Track structure changes
        if changes['structure_changes']:
            analysis['structure_changes'] += 1

        # Track iterative refinements (small edits < 50 words)
        if 0 < abs(changes['word_count_change']) < 50:
            analysis['iterative_refinements'] += 1

    return analysis


def categorize_editing_patterns(analysis):
    """
    Categorize editing patterns into actionable types.

    Returns list of pattern dicts with type, description, and insight.
    """
    patterns = []

    if analysis['major_additions']:
        patterns.append({
            'type': 'Content Expansion',
            'description': f"{len(analysis['major_additions'])} major content additions",
            'insight': 'Substantial content added in chunks during the drafting process'
        })

    if analysis['structure_changes'] > 3:
        patterns.append({
            'type': 'Structure Refinement',
            'description': f"{analysis['structure_changes']} structure modifications",
            'insight': 'Content structure reorganized multiple times before finalizing'
        })

    if analysis['iterative_refinements'] > 5:
        patterns.append({
            'type': 'Iterative Polish',
            'description': f"{analysis['iterative_refinements']} small refinements",
            'insight': 'Many small tweaks to polish language and tone after structure is set'
        })

    return patterns


def load_env():
    """Load environment variables from .env file if present."""
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def print_analysis(analysis):
    """Pretty-print a post analysis."""
    if not analysis:
        return

    print(f"\n  {analysis['post_title']}")
    print(f"  Site: {analysis['site']}")
    print(f"  Total revisions: {analysis['total_revisions']}")

    patterns = categorize_editing_patterns(analysis)

    for pattern in patterns:
        print(f"\n    {pattern['type']}: {pattern['description']}")
        print(f"    -> {pattern['insight']}")

    if analysis['major_additions']:
        print(f"\n    Major Content Additions:")
        for addition in analysis['major_additions'][:3]:
            print(f"      +{addition['words_added']} words")
            if addition['sections']:
                for section in addition['sections'][:2]:
                    print(f"        - {section}")


def main():
    parser = argparse.ArgumentParser(
        description='BlogClaw - Analyze WordPress revision history to learn editing patterns',
        epilog='Part of the BlogClaw self-improving blog system (OpenClaw / NanoClaw ecosystem)'
    )
    parser.add_argument('--site', help='WordPress site URL (or set WORDPRESS_URL env var)')
    parser.add_argument('--post-id', type=int, help='WordPress post ID to analyze')
    parser.add_argument('--title', help='Post title (for display)', default='Untitled')
    parser.add_argument('--username', help='WordPress username (or set WORDPRESS_USERNAME env var)')
    parser.add_argument('--password', help='WordPress app password (or set WORDPRESS_PASSWORD env var)')
    parser.add_argument('--config', help='JSON config file with multiple posts to analyze')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of formatted text')

    args = parser.parse_args()

    load_env()

    site = args.site or os.getenv('WORDPRESS_URL')
    username = args.username or os.getenv('WORDPRESS_USERNAME')
    password = args.password or os.getenv('WORDPRESS_PASSWORD')

    # Config file mode: analyze multiple posts
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

        posts = config.get('posts', [])
        if not posts:
            print("Error: No posts found in config file", file=sys.stderr)
            sys.exit(1)

        all_analyses = []
        all_patterns = []

        print("=" * 70)
        print("BLOGCLAW - REVISION ANALYSIS")
        print("=" * 70)

        for post in posts:
            post_site = post.get('site', site)
            post_user = post.get('username', username)
            post_pass = post.get('password', password)

            if not all([post_site, post_user, post_pass]):
                print(f"Skipping {post.get('title', 'unknown')}: missing credentials", file=sys.stderr)
                continue

            analysis = analyze_post_revisions(
                post_site, post['id'], post.get('title', 'Untitled'),
                (post_user, post_pass)
            )

            if analysis:
                all_analyses.append(analysis)
                all_patterns.extend(categorize_editing_patterns(analysis))
                if not args.json:
                    print_analysis(analysis)

        if args.json:
            print(json.dumps(all_analyses, indent=2))
        else:
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            total = len(all_analyses)
            expansions = sum(1 for p in all_patterns if p['type'] == 'Content Expansion')
            restructures = sum(1 for p in all_patterns if p['type'] == 'Structure Refinement')
            polishes = sum(1 for p in all_patterns if p['type'] == 'Iterative Polish')
            print(f"\n  Posts analyzed: {total}")
            print(f"  Posts with major content expansion: {expansions}/{total}")
            print(f"  Posts with significant restructuring: {restructures}/{total}")
            print(f"  Posts with iterative polishing: {polishes}/{total}")

    # Single post mode
    elif args.post_id:
        if not all([site, username, password]):
            print("Error: Need --site, --username, --password (or env vars)", file=sys.stderr)
            sys.exit(1)

        analysis = analyze_post_revisions(site, args.post_id, args.title, (username, password))

        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print("=" * 70)
            print("BLOGCLAW - REVISION ANALYSIS")
            print("=" * 70)
            print_analysis(analysis)

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python3 analyze_revisions.py --site https://mysite.com --post-id 42 --username admin")
        print("  python3 analyze_revisions.py --config posts.json --json")
        sys.exit(1)


if __name__ == '__main__':
    main()
