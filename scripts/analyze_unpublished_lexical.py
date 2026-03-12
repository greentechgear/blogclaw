#!/usr/bin/env python3
"""
BlogClaw - Unpublished Draft Lexical Analyzer

Monthly word frequency analysis comparing published vs unpublished drafts.
Requires statistical significance (minimum 5,000 words per corpus).

Identifies language patterns that correlate with rejection:
- Words that appear more frequently in unpublished drafts
- Words that appear more frequently in published articles
- Topic/subject matter differences
- Sentiment and tone markers

Run monthly for sufficient data volume.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import re

# Common stop words to exclude from analysis
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'it',
    'its', 'they', 'them', 'their', 'we', 'us', 'our', 'you', 'your', 'he',
    'she', 'him', 'her', 'his', 'my', 'me', 'i', 'am', 'not', 'no', 'yes'
}

def clean_text_for_analysis(text):
    """Clean text and extract words for frequency analysis"""
    # Remove frontmatter
    if text.startswith('---'):
        parts = text.split('---', 2)
        text = parts[2] if len(parts) > 2 else text

    # Remove markdown formatting
    text = re.sub(r'#+\s', '', text)  # Headers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)  # Comments

    # Convert to lowercase
    text = text.lower()

    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[a-z]{3,}\b', text)  # Min 3 chars

    # Filter stop words
    words = [w for w in words if w not in STOP_WORDS]

    return words

def load_published_content(learning_dir):
    """Fetch content of published posts from WordPress API.

    Loads WordPress credentials from the blogclaw .env file and queries
    wp/v2/posts (status=publish) to collect actual post body text.
    Falls back gracefully if credentials are not available.
    """
    import requests
    from requests.auth import HTTPBasicAuth

    # Load credentials
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        env_path = Path('/workspace/group/.env')

    creds = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    creds[key.strip()] = value.strip()

    wp_url = creds.get('WORDPRESS_URL', os.environ.get('WORDPRESS_URL', ''))
    username = creds.get('WORDPRESS_USERNAME', os.environ.get('WORDPRESS_USERNAME', ''))
    password = creds.get('WORDPRESS_PASSWORD', os.environ.get('WORDPRESS_PASSWORD', ''))

    if not all([wp_url, username, password]):
        print("  ⚠ WordPress credentials not found — published corpus will be empty.", file=sys.stderr)
        return []

    wp_url = wp_url.rstrip('/')
    auth = HTTPBasicAuth(username, password)
    published_texts = []

    try:
        page = 1
        while True:
            url = f"{wp_url}/wp-json/wp/v2/posts?status=publish&per_page=100&page={page}&_fields=id,content"
            resp = requests.get(url, auth=auth, timeout=30)
            if resp.status_code == 400:
                break  # No more pages
            resp.raise_for_status()
            posts = resp.json()
            if not posts:
                break
            for post in posts:
                # content.rendered contains HTML — strip tags for text analysis
                html = post.get('content', {}).get('rendered', '')
                text = re.sub(r'<[^>]+>', ' ', html)  # strip HTML tags
                text = re.sub(r'&[a-z]+;', ' ', text)  # strip HTML entities
                published_texts.append(text)
            if len(posts) < 100:
                break
            page += 1
        print(f"  ✓ Fetched {len(published_texts)} published posts from WordPress")
    except Exception as e:
        print(f"  ⚠ Could not fetch published posts: {e}", file=sys.stderr)

    return published_texts

def analyze_word_frequency(drafts_dir, published_content, age_threshold=7):
    """Compare word frequency between unpublished drafts and published content"""
    drafts_path = Path(drafts_dir)

    unpublished_words = []
    unpublished_total_words = 0
    unpublished_count = 0

    # Collect words from unpublished drafts
    for draft_file in drafts_path.glob('*.md'):
        if draft_file.name == 'TEMPLATE.md':
            continue

        # Check age
        mtime = os.path.getmtime(draft_file)
        file_date = datetime.fromtimestamp(mtime)
        age = (datetime.now() - file_date).days

        if age >= age_threshold:
            with open(draft_file, 'r', encoding='utf-8') as f:
                content = f.read()
                words = clean_text_for_analysis(content)
                unpublished_words.extend(words)
                unpublished_total_words += len(words)
                unpublished_count += 1

    # Collect words from published content
    published_words = []
    published_total_words = 0
    published_count = len(published_content)

    for content in published_content:
        words = clean_text_for_analysis(content)
        published_words.extend(words)
        published_total_words += len(words)

    # Calculate frequencies
    unpublished_freq = Counter(unpublished_words)
    published_freq = Counter(published_words)

    # Statistical significance check
    min_words = 5000
    if unpublished_total_words < min_words:
        return {
            'insufficient_data': True,
            'unpublished_word_count': unpublished_total_words,
            'published_word_count': published_total_words,
            'required_words': min_words,
            'unpublished_drafts': unpublished_count,
            'published_articles': published_count,
        }

    # Normalize frequencies (per 1000 words)
    unpublished_normalized = {
        word: (count / unpublished_total_words) * 1000
        for word, count in unpublished_freq.items()
        if count >= 3  # Min 3 occurrences
    }

    published_normalized = {
        word: (count / published_total_words) * 1000
        for word, count in published_freq.items()
        if count >= 3
    }

    # Find words more common in unpublished drafts
    unpublished_markers = []
    for word, freq in unpublished_normalized.items():
        pub_freq = published_normalized.get(word, 0)
        if freq > pub_freq * 1.5:  # 50% more frequent
            ratio = freq / pub_freq if pub_freq > 0 else float('inf')
            unpublished_markers.append({
                'word': word,
                'unpublished_freq': freq,
                'published_freq': pub_freq,
                'ratio': ratio
            })

    # Find words more common in published articles
    published_markers = []
    for word, freq in published_normalized.items():
        unpub_freq = unpublished_normalized.get(word, 0)
        if freq > unpub_freq * 1.5:
            ratio = freq / unpub_freq if unpub_freq > 0 else float('inf')
            published_markers.append({
                'word': word,
                'published_freq': freq,
                'unpublished_freq': unpub_freq,
                'ratio': ratio
            })

    # Sort by ratio
    unpublished_markers.sort(key=lambda x: x['ratio'], reverse=True)
    published_markers.sort(key=lambda x: x['ratio'], reverse=True)

    return {
        'insufficient_data': False,
        'unpublished_word_count': unpublished_total_words,
        'published_word_count': published_total_words,
        'unpublished_drafts': unpublished_count,
        'published_articles': published_count,
        'unpublished_markers': unpublished_markers[:20],  # Top 20
        'published_markers': published_markers[:20],  # Top 20
        'unpublished_unique_words': len(unpublished_freq),
        'published_unique_words': len(published_freq),
    }

def generate_lexical_report(analysis, learning_dir):
    """Generate markdown report of lexical analysis"""
    report_path = Path(learning_dir) / 'UNPUBLISHED_LEXICAL_ANALYSIS.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Unpublished Drafts - Lexical Analysis\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(f"**Analysis Type:** Word frequency comparison (published vs unpublished)\n\n")

        if analysis.get('insufficient_data'):
            f.write("## Insufficient Data\n\n")
            f.write(f"**Minimum required:** {analysis['required_words']:,} words\n")
            f.write(f"**Unpublished corpus:** {analysis['unpublished_word_count']:,} words ({analysis['unpublished_drafts']} drafts)\n")
            f.write(f"**Published corpus:** {analysis['published_word_count']:,} words ({analysis['published_articles']} articles)\n\n")
            f.write("Word frequency analysis requires at least 5,000 words in the unpublished corpus for statistical significance.\n\n")
            f.write("**Next steps:**\n")
            f.write("- This analysis runs monthly (not bi-weekly like basic analysis)\n")
            f.write("- Accumulate more unpublished drafts over time\n")
            f.write("- Re-run when corpus exceeds 5,000 words\n")
            return report_path

        f.write("## Corpus Statistics\n\n")
        f.write(f"- **Unpublished drafts analyzed:** {analysis['unpublished_drafts']}\n")
        f.write(f"- **Published articles analyzed:** {analysis['published_articles']}\n")
        f.write(f"- **Unpublished word count:** {analysis['unpublished_word_count']:,} words\n")
        f.write(f"- **Published word count:** {analysis['published_word_count']:,} words\n")
        f.write(f"- **Unpublished unique words:** {analysis['unpublished_unique_words']:,}\n")
        f.write(f"- **Published unique words:** {analysis['published_unique_words']:,}\n\n")

        f.write("## Words That Signal Rejection\n\n")
        f.write("Words that appear significantly more often in UNPUBLISHED drafts:\n\n")
        f.write("| Word | Unpub Freq | Pub Freq | Ratio |\n")
        f.write("|------|-----------|----------|-------|\n")

        for marker in analysis['unpublished_markers'][:15]:
            ratio_str = f"{marker['ratio']:.1f}x" if marker['ratio'] != float('inf') else "∞"
            f.write(f"| {marker['word']} | {marker['unpublished_freq']:.2f} | {marker['published_freq']:.2f} | {ratio_str} |\n")

        f.write("\n**Interpretation:** These words correlate with drafts the author chose NOT to publish.\n\n")

        f.write("## Words That Signal Success\n\n")
        f.write("Words that appear significantly more often in PUBLISHED articles:\n\n")
        f.write("| Word | Pub Freq | Unpub Freq | Ratio |\n")
        f.write("|------|---------|-----------|-------|\n")

        for marker in analysis['published_markers'][:15]:
            ratio_str = f"{marker['ratio']:.1f}x" if marker['ratio'] != float('inf') else "∞"
            f.write(f"| {marker['word']} | {marker['published_freq']:.2f} | {marker['unpublished_freq']:.2f} | {ratio_str} |\n")

        f.write("\n**Interpretation:** These words correlate with content the author chose to publish.\n\n")

        f.write("## Recommendations\n\n")

        # Analyze top unpublished markers for patterns
        top_unpub = [m['word'] for m in analysis['unpublished_markers'][:10]]
        top_pub = [m['word'] for m in analysis['published_markers'][:10]]

        f.write("Based on lexical analysis:\n\n")
        f.write(f"- **Avoid overusing:** {', '.join(top_unpub[:5])}\n")
        f.write(f"- **Consider including:** {', '.join(top_pub[:5])}\n")
        f.write("- Review unpublished drafts for subject matter patterns\n")
        f.write("- Compare tone and complexity between corpora\n\n")

        f.write("## Methodology\n\n")
        f.write("1. Extract all words (3+ characters) from unpublished drafts (7+ days old)\n")
        f.write("2. Extract all words from published articles\n")
        f.write("3. Remove common stop words (the, and, or, etc.)\n")
        f.write("4. Normalize frequencies (per 1,000 words)\n")
        f.write("5. Identify words with 1.5x+ frequency difference\n")
        f.write("6. Minimum 3 occurrences per word for inclusion\n")
        f.write("7. Requires 5,000+ word corpus for statistical validity\n")

    return report_path

def main():
    parser = argparse.ArgumentParser(description='Lexical analysis of unpublished vs published drafts')
    parser.add_argument('--drafts-dir', default='/workspace/group/blogging/drafts',
                       help='Path to drafts directory')
    parser.add_argument('--learning-dir', default='/workspace/group/blogging',
                       help='Path to learning directory')
    parser.add_argument('--age-threshold', type=int, default=3,
                       help='Minimum age in days to consider draft unpublished (default: 3 — per SKILL.md)')
    parser.add_argument('--json', action='store_true',
                       help='Output JSON instead of generating report')

    args = parser.parse_args()

    print(f"BlogClaw - Lexical Analysis (Unpublished vs Published)\n")
    print(f"Analyzing word frequencies...")

    # TODO: Implement published content fetching
    published_content = load_published_content(args.learning_dir)

    analysis = analyze_word_frequency(
        args.drafts_dir,
        published_content,
        args.age_threshold
    )

    if args.json:
        print(json.dumps(analysis, indent=2))
        return

    report_path = generate_lexical_report(analysis, args.learning_dir)

    print(f"\n✓ Lexical analysis complete")

    if analysis.get('insufficient_data'):
        print(f"  ⚠ Insufficient data for statistical significance")
        print(f"  Unpublished: {analysis['unpublished_word_count']:,} words (need 5,000+)")
        print(f"  Published: {analysis['published_word_count']:,} words")
    else:
        print(f"  Unpublished corpus: {analysis['unpublished_word_count']:,} words")
        print(f"  Published corpus: {analysis['published_word_count']:,} words")
        print(f"  Rejection markers: {len(analysis['unpublished_markers'])} words")
        print(f"  Success markers: {len(analysis['published_markers'])} words")

    print(f"  Report: {report_path}")

if __name__ == '__main__':
    main()
