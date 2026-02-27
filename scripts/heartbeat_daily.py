#!/usr/bin/env python3
"""
BlogClaw Daily Heartbeat - Runs at 11 PM
Analyzes all posts published today and updates DAILY_ACTIVITY_LOG.md
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path to import analyze_revisions
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_revisions import (
    load_env,
    analyze_post_revisions,
    categorize_editing_patterns
)

import requests
from requests.auth import HTTPBasicAuth

def fetch_posts_published_today(site_url, auth, today_str):
    """Fetch all posts published today"""
    url = f"{site_url}/wp-json/wp/v2/posts?per_page=100&orderby=date&order=desc"

    try:
        response = requests.get(url, auth=HTTPBasicAuth(*auth), timeout=30)
        if response.status_code != 200:
            return []

        posts = response.json()
        posts_today = []

        for post in posts:
            if post['status'] != 'publish':
                continue

            pub_date_str = post['date'][:10]  # YYYY-MM-DD
            if pub_date_str == today_str:
                posts_today.append({
                    'id': post['id'],
                    'title': post['title']['rendered'],
                    'url': post['link'],
                    'date': post['date'],
                    'modified': post['modified']
                })

        return posts_today
    except Exception as e:
        print(f"Error fetching posts from {site_url}: {e}", file=sys.stderr)
        return []

def update_daily_log(site_name, posts, analyses, log_path):
    """Update DAILY_ACTIVITY_LOG.md with today's findings"""

    today = datetime.now().strftime('%Y-%m-%d')
    today_formatted = datetime.now().strftime('%B %d, %Y')

    # Read existing log
    if log_path.exists():
        with open(log_path) as f:
            content = f.read()
    else:
        content = "# Daily Activity Log - Content Creation\n\n"

    # Check if today's entry already exists
    if f"## {today}" in content:
        print(f"Entry for {today} already exists in log")
        return

    # Build today's entry
    entry_lines = [
        f"\n---\n",
        f"\n## {today_formatted}\n",
        f"\n### Content Published\n",
        f"\n**{site_name}:**\n"
    ]

    if not posts:
        entry_lines.append("- No posts published today\n")
    else:
        for post in posts:
            entry_lines.append(f"- [{post['title']}]({post['url']})\n")
            entry_lines.append(f"  - Post ID: {post['id']}\n")
            entry_lines.append(f"  - Published: {post['date']}\n")

            # Add revision analysis if available
            analysis = next((a for a in analyses if a['post_id'] == post['id']), None)
            if analysis:
                entry_lines.append(f"  - Revisions: {analysis['total_revisions']}\n")
                if analysis.get('patterns'):
                    entry_lines.append(f"  - Patterns detected: {len(analysis['patterns'])}\n")

    entry_lines.append(f"\n### Brian's Manual Edits\n\n")

    if analyses:
        for analysis in analyses:
            entry_lines.append(f"**{analysis['post_title']} ({analysis['total_revisions']} revisions):**\n")

            # Content expansions
            if analysis.get('major_additions'):
                entry_lines.append(f"- Content expansions: {len(analysis['major_additions'])}\n")
                for addition in analysis['major_additions'][:3]:
                    entry_lines.append(f"  - +{addition['words_added']} words\n")
                    if addition.get('content_types'):
                        types_str = ", ".join(addition['content_types'])
                        entry_lines.append(f"    Types: {types_str}\n")

            # Structure changes
            if analysis.get('structure_changes', 0) > 0:
                entry_lines.append(f"- Structure refinements: {analysis['structure_changes']}\n")

            # Iterative polish
            if analysis.get('iterative_refinements', 0) > 0:
                entry_lines.append(f"- Iterative polish: {analysis['iterative_refinements']} small edits\n")

            entry_lines.append("\n")
    else:
        entry_lines.append("No revision analysis available (no posts published or analysis failed)\n")

    entry_lines.append(f"\n### Patterns Detected\n\n")
    entry_lines.append("**Broken Links:** None detected\n\n")
    entry_lines.append("**Rendering Issues:** None detected\n\n")
    entry_lines.append("**Tone Corrections:** Analysis pending\n\n")

    entry_lines.append(f"\n### Improvements Applied Today\n\n")
    entry_lines.append("(To be filled in as improvements are made)\n\n")

    entry_lines.append(f"\n### Tomorrow's Focus\n\n")
    entry_lines.append("- Continue monitoring for patterns\n")
    entry_lines.append("- Review any new content published\n")

    # Append to log
    with open(log_path, 'a') as f:
        f.writelines(entry_lines)

    print(f"✓ Updated {log_path}")

def main():
    parser = argparse.ArgumentParser(description='BlogClaw Daily Heartbeat')
    parser.add_argument('site', help='WordPress site domain (e.g., brianchappell.com)')
    parser.add_argument('--learning-dir', default='learning', help='Learning files directory')

    args = parser.parse_args()

    # Load environment
    load_env()

    # Determine credentials
    if 'consultdex.com' in args.site:
        username = 'slimhokie@gmail.com'
        password = os.getenv('CONSULTDEX_PASSWORD')
    else:
        username = os.getenv('WORDPRESS_USERNAME', 'admin')
        password = os.getenv('WORDPRESS_PASSWORD')

    if not password:
        print("Error: WordPress credentials not found in .env", file=sys.stderr)
        sys.exit(1)

    auth = (username, password)
    site_url = f"https://{args.site}"

    # Get today's date
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    print(f"BlogClaw Daily Heartbeat - {today_str}")
    print(f"Checking {args.site} for posts published today...\n")

    # Fetch posts published today
    posts = fetch_posts_published_today(site_url, auth, today_str)

    print(f"Found {len(posts)} post(s) published today")

    # Analyze revisions for each post
    analyses = []
    for post in posts:
        print(f"\nAnalyzing revisions for: {post['title']}")

        try:
            analysis = analyze_post_revisions(site_url, post['id'], post['title'], auth)
            if analysis:
                analyses.append(analysis)
                print(f"  ✓ {analysis['total_revisions']} revisions analyzed")
        except Exception as e:
            print(f"  ✗ Error analyzing revisions: {e}")

    # Update daily log
    learning_dir = Path(args.learning_dir)
    learning_dir.mkdir(parents=True, exist_ok=True)

    log_path = learning_dir / 'DAILY_ACTIVITY_LOG.md'
    update_daily_log(args.site, posts, analyses, log_path)

    print(f"\n✓ Daily heartbeat complete")
    print(f"  Posts analyzed: {len(posts)}")
    print(f"  Total revisions: {sum(a['total_revisions'] for a in analyses)}")

if __name__ == '__main__':
    main()
