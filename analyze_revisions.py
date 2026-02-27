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


# Placeholder patterns: ${VAR}, {{var}}, %VAR%
PLACEHOLDER_PATTERNS = [
    re.compile(r'\$\{[^}]+\}'),          # ${WORDPRESS_URL}, ${POST_ID}
    re.compile(r'\{\{[^}]+\}\}'),         # {{site_name}}, {{author}}
    re.compile(r'%[A-Z][A-Z0-9_]+%'),    # %PLACEHOLDER%, %API_KEY%
]


def normalize_text(text):
    """
    Normalize text for comparison by replacing placeholders with stable tokens.

    Handles ${VAR}, {{var}}, and %VAR% patterns so they don't contribute
    to diffs or get flagged as errors.

    Returns:
        tuple: (normalized_text, placeholder_count)
    """
    placeholder_count = 0
    for pattern in PLACEHOLDER_PATTERNS:
        matches = pattern.findall(text)
        placeholder_count += len(matches)
        text = pattern.sub('PLACEHOLDER', text)
    return text, placeholder_count


def _split_paragraphs(text):
    """Split text into paragraph-level blocks for diffing."""
    # Split on double newlines or single newlines followed by whitespace
    paragraphs = re.split(r'\n\s*\n|\n(?=\s)', text.strip())
    # Filter out empty strings and whitespace-only blocks
    return [p.strip() for p in paragraphs if p.strip()]


def classify_content_block(text):
    """
    Classify an added/removed text block by content type.

    Uses keyword heuristics to determine what kind of content this is.

    Returns:
        str: One of 'business_context', 'example_case_study', 'technical_detail',
             'edge_case', 'personal_anecdote', or 'general_expansion'
    """
    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    # Score each category by keyword density
    scores = {
        'business_context': 0,
        'example_case_study': 0,
        'technical_detail': 0,
        'edge_case': 0,
        'personal_anecdote': 0,
    }

    # Business context keywords
    business_keywords = [
        'why', 'matters', 'value', 'roi', 'benefit', 'revenue', 'cost',
        'business', 'customer', 'client', 'market', 'strategy', 'growth',
        'impact', 'result', 'outcome', 'bottom line', 'competitive',
        'opportunity', 'risk', 'stakeholder', 'decision'
    ]
    for kw in business_keywords:
        if kw in text_lower:
            scores['business_context'] += 1

    # Example / case study keywords
    example_keywords = [
        'example', 'for instance', 'case study', 'company', 'organization',
        'used this', 'implemented', 'deployed', 'real-world', 'in practice',
        'here\'s how', 'such as', 'like when', 'consider'
    ]
    for kw in example_keywords:
        if kw in text_lower:
            scores['example_case_study'] += 1
    # Boost if proper nouns are present (capitalized words mid-sentence)
    proper_nouns = re.findall(r'(?<!\. )(?<!^)[A-Z][a-z]{2,}', text)
    scores['example_case_study'] += min(len(proper_nouns), 3)

    # Technical detail keywords
    technical_keywords = [
        'api', 'endpoint', 'config', 'setup', 'install', 'code', 'function',
        'parameter', 'variable', 'database', 'server', 'http', 'json', 'html',
        'css', 'javascript', 'python', 'bash', 'command', 'terminal', 'deploy',
        'docker', 'container', 'query', 'schema', 'class', 'method'
    ]
    for kw in technical_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            scores['technical_detail'] += 1
    # Boost for code-like patterns
    if re.search(r'[{}\[\]();]|->|=>|//', text):
        scores['technical_detail'] += 2

    # Edge case / gotcha keywords
    edge_keywords = [
        'however', 'except', 'gotcha', 'caveat', 'warning', 'careful',
        'breaks when', 'doesn\'t work', 'won\'t work', 'edge case',
        'limitation', 'workaround', 'note that', 'be aware', 'pitfall',
        'trap', 'mistake', 'bug', 'issue'
    ]
    for kw in edge_keywords:
        if kw in text_lower:
            scores['edge_case'] += 1

    # Personal anecdote keywords (first-person markers)
    personal_keywords = [
        'i ', 'i\'m', 'i\'ve', 'i\'d', 'my ', 'mine', 'we ', 'we\'re',
        'our ', 'myself', 'personally', 'in my experience', 'i remember',
        'i found', 'i learned', 'i realized', 'i think', 'i believe',
        'i noticed', 'last week', 'last month', 'last year', 'years ago'
    ]
    for kw in personal_keywords:
        if kw in text_lower:
            scores['personal_anecdote'] += 1

    # Find highest scoring category
    max_score = max(scores.values())
    if max_score == 0:
        return 'general_expansion'

    # Return the category with the highest score
    return max(scores, key=scores.get)


def analyze_content_changes(old_content, new_content):
    """
    Analyze what changed between two revisions.

    Compares plain text (HTML stripped) for word count deltas,
    uses SequenceMatcher for paragraph-level diff extraction,
    normalizes placeholders before comparison,
    and uses regex on raw HTML for structural changes (header additions/removals).
    """
    old_text = strip_html(old_content)
    new_text = strip_html(new_content)

    # Normalize placeholders before comparison
    old_normalized, old_ph_count = normalize_text(old_text)
    new_normalized, new_ph_count = normalize_text(new_text)
    total_placeholders = old_ph_count + new_ph_count

    changes = {
        'word_count_change': len(new_normalized.split()) - len(old_normalized.split()),
        'additions': [],
        'deletions': [],
        'structure_changes': [],
        'content_blocks': [],
        'placeholders_found': total_placeholders
    }

    # Paragraph-level diff using SequenceMatcher
    old_paragraphs = _split_paragraphs(old_normalized)
    new_paragraphs = _split_paragraphs(new_normalized)

    matcher = SequenceMatcher(None, old_paragraphs, new_paragraphs)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            # New paragraphs added
            for p in new_paragraphs[j1:j2]:
                word_count = len(p.split())
                if word_count < 3:
                    continue  # Skip trivial fragments
                content_type = classify_content_block(p)
                preview = p[:120] + '...' if len(p) > 120 else p
                changes['content_blocks'].append({
                    'action': 'added',
                    'type': content_type,
                    'text_preview': preview,
                    'word_count': word_count
                })
        elif tag == 'delete':
            # Paragraphs removed
            for p in old_paragraphs[i1:i2]:
                word_count = len(p.split())
                if word_count < 3:
                    continue
                content_type = classify_content_block(p)
                preview = p[:120] + '...' if len(p) > 120 else p
                changes['content_blocks'].append({
                    'action': 'removed',
                    'type': content_type,
                    'text_preview': preview,
                    'word_count': word_count
                })
        elif tag == 'replace':
            # Paragraphs changed -- track both sides
            for p in old_paragraphs[i1:i2]:
                word_count = len(p.split())
                if word_count < 3:
                    continue
                content_type = classify_content_block(p)
                preview = p[:120] + '...' if len(p) > 120 else p
                changes['content_blocks'].append({
                    'action': 'removed',
                    'type': content_type,
                    'text_preview': preview,
                    'word_count': word_count
                })
            for p in new_paragraphs[j1:j2]:
                word_count = len(p.split())
                if word_count < 3:
                    continue
                content_type = classify_content_block(p)
                preview = p[:120] + '...' if len(p) > 120 else p
                changes['content_blocks'].append({
                    'action': 'added',
                    'type': content_type,
                    'text_preview': preview,
                    'word_count': word_count
                })

    # Detect structure changes (any header modification)
    old_headers = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', old_content)
    new_headers = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', new_content)

    if old_headers != new_headers:
        # Distinguish reordering from additions/removals
        old_header_set = set(old_headers)
        new_header_set = set(new_headers)
        if old_header_set == new_header_set and old_headers != new_headers:
            changes['structure_changes'].append('Headers reordered')
        else:
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
        'structure_reorders': 0,
        'iterative_refinements': 0,
        'all_content_blocks': [],
        'total_placeholders': 0
    }

    # Analyze revision-to-revision changes
    for i in range(len(revisions) - 1):
        curr = revisions[i]
        prev = revisions[i + 1]

        changes = analyze_content_changes(
            prev['content']['rendered'],
            curr['content']['rendered']
        )

        # Accumulate content blocks across all revisions
        analysis['all_content_blocks'].extend(changes['content_blocks'])
        analysis['total_placeholders'] += changes['placeholders_found']

        # Track major additions (100+ words added)
        if changes['word_count_change'] > 100:
            # Summarize content block types in this addition
            added_blocks = [b for b in changes['content_blocks'] if b['action'] == 'added']
            block_types = [b['type'] for b in added_blocks]
            analysis['major_additions'].append({
                'words_added': changes['word_count_change'],
                'sections': changes['additions'],
                'content_types': block_types,
                'timestamp': curr['date']
            })

        # Track structure changes, distinguishing reorders from modifications
        if changes['structure_changes']:
            analysis['structure_changes'] += 1
            if 'Headers reordered' in changes['structure_changes']:
                analysis['structure_reorders'] += 1

        # Track iterative refinements (small edits < 50 words)
        if 0 < abs(changes['word_count_change']) < 50:
            analysis['iterative_refinements'] += 1

    # Run semantic pattern detection on accumulated data
    analysis['semantic_patterns'] = detect_semantic_patterns(analysis)

    return analysis


def detect_semantic_patterns(analysis):
    """
    Analyze content blocks across all revisions to explain *why* patterns matter.

    Goes beyond numeric thresholds to classify the meaning behind editing patterns.

    Returns:
        list of dicts with pattern_type, why_it_matters, suggested_action, confidence
    """
    semantic_patterns = []
    all_blocks = analysis.get('all_content_blocks', [])
    added_blocks = [b for b in all_blocks if b['action'] == 'added']
    removed_blocks = [b for b in all_blocks if b['action'] == 'removed']

    if not all_blocks:
        return semantic_patterns

    # --- Pattern: What kind of content is being added? ---
    if added_blocks:
        type_counts = {}
        for block in added_blocks:
            t = block['type']
            type_counts[t] = type_counts.get(t, 0) + 1

        total_added = len(added_blocks)
        dominant_type = max(type_counts, key=type_counts.get)
        dominant_count = type_counts[dominant_type]
        confidence = round(dominant_count / total_added, 2) if total_added > 0 else 0

        type_insights = {
            'business_context': {
                'why': 'AI drafts are missing the "why this matters" framing that connects features to real value',
                'action': 'Add a business value section check to your reviewer -- flag drafts missing context sections'
            },
            'example_case_study': {
                'why': 'AI generates abstract claims but author grounds them with real examples and named companies',
                'action': 'Require at least one concrete example per major claim in the reviewer checklist'
            },
            'technical_detail': {
                'why': 'AI drafts lack the implementation specifics that technical readers need',
                'action': 'Add a technical depth check -- flag sections that mention tools without config/setup details'
            },
            'edge_case': {
                'why': 'AI presents the happy path but author adds the gotchas that build credibility',
                'action': 'Add edge case prompting to the draft template -- "What breaks? What are the limitations?"'
            },
            'personal_anecdote': {
                'why': 'AI writes generically but the author\'s voice comes from personal experience and honest reflection',
                'action': 'Include personal experience prompts in the draft template -- "What\'s your story with this?"'
            },
            'general_expansion': {
                'why': 'Author is adding depth that the AI draft left shallow -- more detail needed overall',
                'action': 'Increase target word count for AI drafts or add a "depth pass" to the review process'
            }
        }

        insight = type_insights.get(dominant_type, type_insights['general_expansion'])

        if confidence >= 0.4:  # At least 40% of additions are this type
            semantic_patterns.append({
                'pattern_type': f'Content Gap: {dominant_type.replace("_", " ").title()}',
                'why_it_matters': insight['why'],
                'suggested_action': insight['action'],
                'confidence': confidence,
                'evidence': f'{dominant_count}/{total_added} added blocks are {dominant_type.replace("_", " ")}'
            })

        # Secondary type if present and significant
        if total_added >= 4:
            for content_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                if content_type == dominant_type:
                    continue
                secondary_conf = round(count / total_added, 2)
                if secondary_conf >= 0.25 and count >= 2:
                    s_insight = type_insights.get(content_type, type_insights['general_expansion'])
                    semantic_patterns.append({
                        'pattern_type': f'Secondary Gap: {content_type.replace("_", " ").title()}',
                        'why_it_matters': s_insight['why'],
                        'suggested_action': s_insight['action'],
                        'confidence': secondary_conf,
                        'evidence': f'{count}/{total_added} added blocks are {content_type.replace("_", " ")}'
                    })
                    break  # Only one secondary

    # --- Pattern: Structure reordering vs modification ---
    if analysis.get('structure_reorders', 0) > 0:
        reorders = analysis['structure_reorders']
        total_struct = analysis.get('structure_changes', 0)
        if total_struct > 0:
            reorder_ratio = round(reorders / total_struct, 2)
            if reorder_ratio >= 0.5:
                semantic_patterns.append({
                    'pattern_type': 'Reader Engagement Optimization',
                    'why_it_matters': 'Author prefers hook-first structure over linear logic -- reorganizes for reader engagement, not information flow',
                    'suggested_action': 'Use the preferred structure: Hook with data/controversy -> Why it matters -> Technical details -> Implications',
                    'confidence': reorder_ratio,
                    'evidence': f'{reorders}/{total_struct} structure changes were reorderings (not additions/removals)'
                })

    # --- Pattern: Iterative polish concentration ---
    if analysis.get('iterative_refinements', 0) > 5:
        # Check if polish edits are concentrated in specific block types
        polish_blocks = [b for b in all_blocks if b['word_count'] < 50]
        if polish_blocks:
            personal_polish = sum(1 for b in polish_blocks if b['type'] == 'personal_anecdote')
            total_polish = len(polish_blocks)
            if total_polish > 0 and personal_polish / total_polish >= 0.3:
                semantic_patterns.append({
                    'pattern_type': 'Voice Injection',
                    'why_it_matters': 'Author personalizes tone and voice in small edits -- this is where personality lives',
                    'suggested_action': 'Document signature phrases and voice patterns in the style guide; these are hard to automate but can be prompted for',
                    'confidence': round(personal_polish / total_polish, 2),
                    'evidence': f'{personal_polish}/{total_polish} polish edits inject personal voice'
                })

    return semantic_patterns


def categorize_editing_patterns(analysis):
    """
    Categorize editing patterns into actionable types.

    Returns list of pattern dicts with type, description, insight,
    and semantic context when available.
    """
    patterns = []

    if analysis['major_additions']:
        # Aggregate content types across all major additions
        all_types = []
        for addition in analysis['major_additions']:
            all_types.extend(addition.get('content_types', []))

        type_summary = ''
        if all_types:
            type_counts = {}
            for t in all_types:
                type_counts[t] = type_counts.get(t, 0) + 1
            top_types = sorted(type_counts.items(), key=lambda x: -x[1])[:3]
            type_summary = ' (' + ', '.join(
                f'{t.replace("_", " ")}: {c}' for t, c in top_types
            ) + ')'

        patterns.append({
            'type': 'Content Expansion',
            'description': f"{len(analysis['major_additions'])} major content additions{type_summary}",
            'insight': 'Substantial content added in chunks during the drafting process'
        })

    if analysis['structure_changes'] > 3:
        reorders = analysis.get('structure_reorders', 0)
        detail = ''
        if reorders > 0:
            detail = f' ({reorders} reorderings, {analysis["structure_changes"] - reorders} modifications)'
        patterns.append({
            'type': 'Structure Refinement',
            'description': f"{analysis['structure_changes']} structure modifications{detail}",
            'insight': 'Content structure reorganized multiple times before finalizing'
        })

    if analysis['iterative_refinements'] > 5:
        patterns.append({
            'type': 'Iterative Polish',
            'description': f"{analysis['iterative_refinements']} small refinements",
            'insight': 'Many small tweaks to polish language and tone after structure is set'
        })

    if analysis.get('total_placeholders', 0) > 0:
        patterns.append({
            'type': 'Placeholders Detected',
            'description': f"{analysis['total_placeholders']} template variables found and excluded",
            'insight': 'Template placeholders (${VAR}, {{var}}, %VAR%) were normalized before analysis'
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
    """Pretty-print a post analysis with content intelligence."""
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
            types_str = ''
            if addition.get('content_types'):
                types_str = f" [{', '.join(set(addition['content_types']))}]"
            print(f"      +{addition['words_added']} words{types_str}")
            if addition['sections']:
                for section in addition['sections'][:2]:
                    print(f"        - {section}")

    # Content block breakdown
    all_blocks = analysis.get('all_content_blocks', [])
    added_blocks = [b for b in all_blocks if b['action'] == 'added']
    if added_blocks:
        print(f"\n    Content Diff Breakdown ({len(added_blocks)} blocks added):")
        type_counts = {}
        for block in added_blocks:
            t = block['type'].replace('_', ' ').title()
            type_counts[t] = type_counts.get(t, 0) + 1
        for content_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"      {content_type}: {count} blocks")

        # Show top 3 added block previews
        top_blocks = sorted(added_blocks, key=lambda b: -b['word_count'])[:3]
        if top_blocks:
            print(f"\n    Largest Additions:")
            for block in top_blocks:
                label = block['type'].replace('_', ' ').title()
                print(f"      [{label}] +{block['word_count']} words: {block['text_preview']}")

    # Semantic patterns
    semantic = analysis.get('semantic_patterns', [])
    if semantic:
        print(f"\n    Semantic Insights:")
        for sp in semantic:
            conf_pct = int(sp['confidence'] * 100)
            print(f"\n      {sp['pattern_type']} ({conf_pct}% confidence)")
            print(f"      Why: {sp['why_it_matters']}")
            print(f"      Action: {sp['suggested_action']}")
            print(f"      Evidence: {sp['evidence']}")


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
