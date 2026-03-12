#!/usr/bin/env python3
"""
BlogClaw - Unpublished Draft Analyzer

Analyzes drafts that haven't been published after a certain age threshold.
Identifies patterns in what the author chooses NOT to publish to inform future drafts.

Learning from rejection is as valuable as learning from edits.
"""

import os
import sys
import json
import argparse
import re
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from pathlib import Path


def load_wp_credentials(env_path=None):
    """Load WordPress credentials from .env file"""
    creds = {}
    paths_to_try = [
        env_path,
        Path(__file__).parent.parent / '.env',
        Path('/workspace/group/.env'),
    ]
    for p in paths_to_try:
        if p and Path(p).exists():
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        creds[key.strip()] = value.strip()
            break
    return creds


def fetch_wordpress_drafts(age_threshold=3):
    """Fetch posts in draft/pending status from WordPress that are older than threshold days.

    These represent content the author chose NOT to publish — the most direct
    rejection signal we have.
    """
    creds = load_wp_credentials()
    wp_url = creds.get('WORDPRESS_URL', os.environ.get('WORDPRESS_URL', ''))
    username = creds.get('WORDPRESS_USERNAME', os.environ.get('WORDPRESS_USERNAME', ''))
    password = creds.get('WORDPRESS_PASSWORD', os.environ.get('WORDPRESS_PASSWORD', ''))

    if not all([wp_url, username, password]):
        print("  ⚠ WordPress credentials not found — skipping WordPress draft fetch.", file=sys.stderr)
        return []

    wp_url = wp_url.rstrip('/')
    auth = HTTPBasicAuth(username, password)
    cutoff = datetime.now() - timedelta(days=age_threshold)
    drafts = []

    for status in ('draft', 'pending'):
        try:
            page = 1
            while True:
                url = (f"{wp_url}/wp-json/wp/v2/posts"
                       f"?status={status}&per_page=100&page={page}"
                       f"&_fields=id,title,date_gmt,modified_gmt,content,excerpt")
                resp = requests.get(url, auth=auth, timeout=30)
                if resp.status_code in (400, 404):
                    break
                resp.raise_for_status()
                posts = resp.json()
                if not posts:
                    break

                for post in posts:
                    # Use modified_gmt as the "last touched" date
                    date_str = post.get('modified_gmt') or post.get('date_gmt', '')
                    try:
                        post_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        post_dt = post_dt.replace(tzinfo=None)  # naive for comparison
                    except Exception:
                        continue

                    if post_dt > cutoff:
                        continue  # Too recent — not a rejection yet

                    age_days = (datetime.now() - post_dt).days
                    title = post.get('title', {}).get('rendered', f"Post {post['id']}")
                    # Strip HTML from content
                    html = post.get('content', {}).get('rendered', '')
                    body = re.sub(r'<[^>]+>', ' ', html)
                    body = re.sub(r'&[a-z]+;', ' ', body)
                    word_count = len(body.split())
                    em_dashes = body.count('—') + body.count('&mdash;')
                    has_data = any(c.isdigit() for c in body[:1000])
                    has_personal = any(p in body.lower() for p in ['i ', 'my ', "i've", "i'm"])

                    drafts.append({
                        'source': 'wordpress',
                        'wordpress_id': post['id'],
                        'wordpress_status': status,
                        'filename': f"wp-{status}-{post['id']}",
                        'title': title,
                        'age_days': age_days,
                        'created_date': post_dt.strftime('%Y-%m-%d'),
                        'word_count': word_count,
                        'h2_sections': body.count('\n## ') + body.count('<h2'),
                        'has_data_driven_content': has_data,
                        'has_personal_voice': has_personal,
                        'em_dash_violations': em_dashes,
                        'category': 'WordPress Draft',
                    })

                if len(posts) < 100:
                    break
                page += 1
        except Exception as e:
            print(f"  ⚠ Could not fetch WordPress {status} posts: {e}", file=sys.stderr)

    return drafts

def get_draft_age(draft_path):
    """Get age of draft in days based on file modification time"""
    mtime = os.path.getmtime(draft_path)
    file_date = datetime.fromtimestamp(mtime)
    age = (datetime.now() - file_date).days
    return age, file_date

def read_frontmatter(content):
    """Extract frontmatter from markdown file"""
    if not content.startswith('---'):
        return {}

    try:
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}

        frontmatter = {}
        for line in parts[1].strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
        return frontmatter
    except:
        return {}

def analyze_draft(draft_path):
    """Extract key characteristics from an unpublished draft"""
    with open(draft_path, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter = read_frontmatter(content)

    # Remove frontmatter for analysis
    if content.startswith('---'):
        parts = content.split('---', 2)
        body = parts[2] if len(parts) > 2 else content
    else:
        body = content

    # Basic metrics
    word_count = len(body.split())
    has_data = any(char.isdigit() for char in body[:1000])  # Check first 1000 chars
    has_personal_voice = any(pronoun in body.lower() for pronoun in ['i ', 'my ', "i've", "i'm"])
    em_dash_count = body.count('—') + body.count('&mdash;')

    # Structure analysis
    headers = [line for line in body.split('\n') if line.startswith('#')]
    h2_count = len([h for h in headers if h.startswith('## ')])

    # Topic extraction (simple keyword approach)
    title = frontmatter.get('title', Path(draft_path).stem)

    age_days, created_date = get_draft_age(draft_path)

    return {
        'filename': Path(draft_path).name,
        'title': title,
        'age_days': age_days,
        'created_date': created_date.strftime('%Y-%m-%d'),
        'word_count': word_count,
        'h2_sections': h2_count,
        'has_data_driven_content': has_data,
        'has_personal_voice': has_personal_voice,
        'em_dash_violations': em_dash_count,
        'category': frontmatter.get('category', 'Unknown'),
    }

def load_published_titles(learning_dir):
    """Load titles of published posts from daily activity log"""
    published = set()
    log_path = Path(learning_dir) / 'DAILY_ACTIVITY_LOG.md'

    if not log_path.exists():
        return published

    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Extract post titles from daily log (assuming format: "- **Title**")
        import re
        titles = re.findall(r'\*\*([^*]+)\*\*', content)
        published.update(titles)

    return published

def analyze_unpublished_drafts(drafts_dir, learning_dir, age_threshold=3):
    """Find and analyze drafts older than threshold that haven't been published.

    Sources:
    1. Local markdown files in drafts_dir (NanoClaw-created drafts)
    2. WordPress posts in draft/pending status (direct WordPress drafts)
    """
    unpublished = []
    published_titles = load_published_titles(learning_dir)

    # --- Source 1: Local markdown files ---
    drafts_path = Path(drafts_dir)
    if drafts_path.exists():
        for draft_file in drafts_path.glob('*.md'):
            if draft_file.name == 'TEMPLATE.md':
                continue

            age_days, _ = get_draft_age(draft_file)

            if age_days >= age_threshold:
                analysis = analyze_draft(draft_file)
                analysis['source'] = 'local'

                # Check if title appears in published list
                if analysis['title'] not in published_titles:
                    unpublished.append(analysis)
    else:
        print(f"  ⚠ Local drafts directory not found: {drafts_dir}")

    # --- Source 2: WordPress draft/pending posts ---
    print(f"\nFetching WordPress draft/pending posts (older than {age_threshold} days)...")
    wp_drafts = fetch_wordpress_drafts(age_threshold=age_threshold)
    if wp_drafts:
        print(f"  Found {len(wp_drafts)} WordPress draft/pending post(s)")
        # Deduplicate: skip WP drafts whose title already appears in local drafts
        local_titles = {d['title'].lower().strip() for d in unpublished}
        for wp in wp_drafts:
            if wp['title'].lower().strip() not in local_titles:
                unpublished.append(wp)
    else:
        print("  No WordPress draft/pending posts found (or credentials unavailable)")

    return unpublished

def identify_patterns(unpublished_drafts):
    """Identify common patterns in unpublished drafts"""
    if not unpublished_drafts:
        return {}

    total = len(unpublished_drafts)

    patterns = {
        'avg_word_count': sum(d['word_count'] for d in unpublished_drafts) / total,
        'lacking_data': sum(1 for d in unpublished_drafts if not d['has_data_driven_content']),
        'lacking_personal_voice': sum(1 for d in unpublished_drafts if not d['has_personal_voice']),
        'em_dash_violations': sum(1 for d in unpublished_drafts if d['em_dash_violations'] > 0),
        'weak_structure': sum(1 for d in unpublished_drafts if d['h2_sections'] < 3),
        'too_short': sum(1 for d in unpublished_drafts if d['word_count'] < 800),
        'too_long': sum(1 for d in unpublished_drafts if d['word_count'] > 4000),
    }

    return patterns

def generate_report(unpublished_drafts, patterns, learning_dir, age_threshold=3):
    """Generate markdown report of unpublished draft analysis"""
    report_path = Path(learning_dir) / 'UNPUBLISHED_DRAFTS_ANALYSIS.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Unpublished Drafts Analysis\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        local_count = sum(1 for d in unpublished_drafts if d.get('source') == 'local')
        wp_count = sum(1 for d in unpublished_drafts if d.get('source') == 'wordpress')
        f.write(f"**Total unpublished drafts ({age_threshold}+ days old):** {len(unpublished_drafts)}\n\n")
        if local_count or wp_count:
            f.write(f"- Local markdown drafts: {local_count}\n")
            f.write(f"- WordPress draft/pending posts: {wp_count}\n\n")

        if not unpublished_drafts:
            f.write("No unpublished drafts found older than 7 days.\n")
            return report_path

        f.write("## Pattern Analysis\n\n")
        f.write("Common characteristics of drafts the author chose NOT to publish:\n\n")

        total = len(unpublished_drafts)
        f.write(f"- **Lacking data-driven content**: {patterns['lacking_data']}/{total} ({patterns['lacking_data']/total*100:.0f}%)\n")
        f.write(f"- **Lacking personal voice**: {patterns['lacking_personal_voice']}/{total} ({patterns['lacking_personal_voice']/total*100:.0f}%)\n")
        f.write(f"- **Em-dash violations**: {patterns['em_dash_violations']}/{total} ({patterns['em_dash_violations']/total*100:.0f}%)\n")
        f.write(f"- **Weak structure** (<3 sections): {patterns['weak_structure']}/{total} ({patterns['weak_structure']/total*100:.0f}%)\n")
        f.write(f"- **Too short** (<800 words): {patterns['too_short']}/{total} ({patterns['too_short']/total*100:.0f}%)\n")
        f.write(f"- **Too long** (>4000 words): {patterns['too_long']}/{total} ({patterns['too_long']/total*100:.0f}%)\n")
        f.write(f"- **Average word count**: {patterns['avg_word_count']:.0f} words\n\n")

        f.write("## Unpublished Drafts\n\n")

        # Sort by age (oldest first)
        sorted_drafts = sorted(unpublished_drafts, key=lambda x: x['age_days'], reverse=True)

        for draft in sorted_drafts:
            f.write(f"### {draft['title']}\n\n")
            f.write(f"- **File**: `{draft['filename']}`\n")
            f.write(f"- **Age**: {draft['age_days']} days (created {draft['created_date']})\n")
            f.write(f"- **Word count**: {draft['word_count']}\n")
            f.write(f"- **Structure**: {draft['h2_sections']} H2 sections\n")
            f.write(f"- **Category**: {draft['category']}\n")

            issues = []
            if not draft['has_data_driven_content']:
                issues.append("lacks data/numbers")
            if not draft['has_personal_voice']:
                issues.append("lacks personal voice")
            if draft['em_dash_violations'] > 0:
                issues.append(f"{draft['em_dash_violations']} em-dashes")
            if draft['h2_sections'] < 3:
                issues.append("weak structure")
            if draft['word_count'] < 800:
                issues.append("too short")
            if draft['word_count'] > 4000:
                issues.append("too long")

            if issues:
                f.write(f"- **Potential issues**: {', '.join(issues)}\n")

            f.write("\n")

        f.write("## Recommendations\n\n")

        if patterns['lacking_data'] / total > 0.5:
            f.write("- **Add specific data**: Over 50% of unpublished drafts lack data-driven content. Your voice requires concrete numbers and examples.\n")

        if patterns['lacking_personal_voice'] / total > 0.5:
            f.write("- **Increase personal voice**: Over 50% lack first-person perspective. Your readers expect personal anecdotes and industry experience.\n")

        if patterns['em_dash_violations'] / total > 0.3:
            f.write("- **Check style guide compliance**: Significant number have em-dash violations (your style guide forbids them).\n")

        if patterns['weak_structure'] / total > 0.5:
            f.write("- **Improve structure**: Over 50% have fewer than 3 H2 sections. Your articles need clear hierarchical organization.\n")

        if patterns['avg_word_count'] < 1200:
            f.write(f"- **Increase depth**: Average word count is {patterns['avg_word_count']:.0f}. Your published articles typically exceed 1,500 words.\n")

    return report_path

def main():
    parser = argparse.ArgumentParser(description='Analyze unpublished drafts to identify patterns')
    parser.add_argument('--drafts-dir', default='/workspace/group/blogging/drafts',
                       help='Path to drafts directory')
    parser.add_argument('--learning-dir', default='/workspace/group/blogging',
                       help='Path to learning directory')
    parser.add_argument('--age-threshold', type=int, default=3,
                       help='Minimum age in days to consider draft unpublished (default: 3 — per SKILL.md)')
    parser.add_argument('--json', action='store_true',
                       help='Output JSON instead of generating report')

    args = parser.parse_args()

    print(f"BlogClaw - Unpublished Draft Analysis\n")
    print(f"Analyzing drafts older than {args.age_threshold} days...")

    unpublished = analyze_unpublished_drafts(
        args.drafts_dir,
        args.learning_dir,
        args.age_threshold
    )

    if args.json:
        print(json.dumps(unpublished, indent=2))
        return

    patterns = identify_patterns(unpublished)
    report_path = generate_report(unpublished, patterns, args.learning_dir, age_threshold=args.age_threshold)

    print(f"\n✓ Analysis complete")
    print(f"  Unpublished drafts: {len(unpublished)}")
    print(f"  Report: {report_path}")

    if unpublished:
        print(f"\nKey patterns:")
        total = len(unpublished)
        if patterns['lacking_data'] / total > 0.5:
            print(f"  - {patterns['lacking_data']}/{total} lack data-driven content")
        if patterns['lacking_personal_voice'] / total > 0.5:
            print(f"  - {patterns['lacking_personal_voice']}/{total} lack personal voice")
        if patterns['weak_structure'] / total > 0.5:
            print(f"  - {patterns['weak_structure']}/{total} have weak structure")

if __name__ == '__main__':
    main()
