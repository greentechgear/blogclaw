#!/usr/bin/env python3
"""
BlogClaw - Clicky Analytics Traffic Analyzer
Analyzes referral traffic patterns and identifies engagement opportunities.

Part of the BlogClaw self-improving blog system.
Built on the OpenClaw / NanoClaw ecosystem.

Usage:
    python3 analyze_traffic.py --site brianchappell.com
    python3 analyze_traffic.py --site consultdex.com --days 30
    python3 analyze_traffic.py --all --json

Environment variables:
    CLICKY_SITE_ID_BRIANCHAPPELL   - Clicky site ID for brianchappell.com
    CLICKY_SITEKEY_BRIANCHAPPELL   - Clicky sitekey for brianchappell.com
    CLICKY_SITE_ID_CONSULTDEX      - Clicky site ID for consultdex.com
    CLICKY_SITEKEY_CONSULTDEX      - Clicky sitekey for consultdex.com

Requirements:
    pip install requests
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Clicky API base URL
CLICKY_API_BASE = "https://api.clicky.com/api/stats/4"

def load_site_config():
    """Load site configuration from sites.json"""
    config_path = Path(__file__).parent / 'sites.json'
    if not config_path.exists():
        return {}

    with open(config_path) as f:
        config = json.load(f)

    # Build domain -> env mapping
    site_map = {}
    for site in config.get('sites', []):
        domain = site.get('domain')
        # Extract env prefix from env var name (e.g. "CLICKY_SITE_ID_EXAMPLE" -> "EXAMPLE")
        clicky_env = site.get('clicky_site_id_env', '')
        if domain and clicky_env:
            prefix = clicky_env.replace('CLICKY_SITE_ID_', '')
            site_map[domain] = prefix

    return site_map


def load_env():
    """Load environment variables from .env file if present."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_site_credentials(domain, site_config=None):
    """
    Get Clicky API credentials for a site.

    Args:
        domain: Site domain (e.g. 'example.com')
        site_config: Optional site config dict (loaded from sites.json)

    Returns:
        tuple: (site_id, sitekey) or (None, None) if not configured
    """
    if site_config is None:
        site_config = load_site_config()

    prefix = site_config.get(domain)
    if not prefix:
        # Try to construct from domain (replace dots/dashes with underscores, uppercase)
        prefix = domain.split('.')[0].upper().replace('-', '_')

    site_id = os.getenv(f'CLICKY_SITE_ID_{prefix}')
    sitekey = os.getenv(f'CLICKY_SITEKEY_{prefix}')

    return site_id, sitekey


def clicky_request(site_id, sitekey, type_param, date='last-7-days', limit=100, extra_params=None):
    """
    Make a request to the Clicky API.

    Args:
        site_id: Clicky site ID
        sitekey: Clicky site key
        type_param: Data type to fetch (e.g. 'pages-list', 'traffic-sources-list')
        date: Date range (e.g. 'last-7-days', 'last-30-days', '2026-02-01,2026-02-26')
        limit: Max results to return
        extra_params: Additional query parameters

    Returns:
        list: API response data, or empty list on failure
    """
    params = {
        'site_id': site_id,
        'sitekey': sitekey,
        'type': type_param,
        'date': date,
        'limit': limit,
        'output': 'json',
    }
    if extra_params:
        params.update(extra_params)

    try:
        response = requests.get(CLICKY_API_BASE, params=params, timeout=30)
        if response.status_code != 200:
            print(f"Error: Clicky API returned HTTP {response.status_code}", file=sys.stderr)
            return []

        data = response.json()

        # Clicky returns a list of date-grouped results
        # Each item has 'date' and 'items' (or 'dates' depending on the type)
        if isinstance(data, list):
            return data
        return []

    except requests.exceptions.RequestException as e:
        print(f"Error calling Clicky API: {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing Clicky response: {e}", file=sys.stderr)
        return []


def extract_items(api_response):
    """
    Extract items from Clicky API response.

    Clicky wraps results in a type container with a 'dates' array:
    [{"type": "pages", "dates": [{"date": "...", "items": [...]}]}]

    Returns:
        list: Flattened list of all items across all type containers and dates
    """
    all_items = []
    for type_container in api_response:
        if not isinstance(type_container, dict):
            continue
        # Navigate into 'dates' array
        dates = type_container.get('dates', [])
        for date_group in dates:
            if isinstance(date_group, dict) and 'items' in date_group:
                items = date_group['items']
                if isinstance(items, list):
                    # Skip empty/zero-only items ({"value":"0"} with no title)
                    for item in items:
                        if isinstance(item, dict) and item.get('title'):
                            all_items.append(item)
    return all_items


def fetch_referral_traffic(site_id, sitekey, date='last-30-days', limit=100):
    """
    Fetch referral traffic sources from Clicky.

    Uses 'links-domains' (referral domains) and 'traffic-sources' (source types).

    Returns:
        list of dicts with keys: title (domain), value (visits), value_percent
    """
    data = clicky_request(
        site_id, sitekey,
        type_param='links-domains',
        date=date,
        limit=limit,
    )
    return extract_items(data)


def fetch_traffic_sources(site_id, sitekey, date='last-30-days', limit=20):
    """
    Fetch high-level traffic source breakdown (search, social, direct, etc.)

    Returns:
        list of dicts with source type and visit counts
    """
    data = clicky_request(
        site_id, sitekey,
        type_param='traffic-sources',
        date=date,
        limit=limit,
    )
    return extract_items(data)


def fetch_top_pages(site_id, sitekey, date='last-30-days', limit=100):
    """
    Fetch top-performing pages from Clicky.

    Returns:
        list of dicts with keys: title (URL/path), value (pageviews)
    """
    data = clicky_request(
        site_id, sitekey,
        type_param='pages',
        date=date,
        limit=limit,
    )
    return extract_items(data)


def fetch_referrers_by_page(site_id, sitekey, page_url, date='last-30-days'):
    """
    Fetch which referrers are driving traffic to a specific page.

    Args:
        page_url: The page path (e.g. '/self-improving-blog-system/')

    Returns:
        list of referrer items for that page
    """
    data = clicky_request(
        site_id, sitekey,
        type_param='links-domains',
        date=date,
        limit=50,
        extra_params={'filter_url': page_url},
    )
    return extract_items(data)


def fetch_search_terms(site_id, sitekey, date='last-30-days', limit=50):
    """
    Fetch search terms driving organic traffic.

    Returns:
        list of dicts with keys: title (search term), value (visits)
    """
    data = clicky_request(
        site_id, sitekey,
        type_param='searches',
        date=date,
        limit=limit,
    )
    return extract_items(data)


def fetch_traffic_over_time(site_id, sitekey, date='last-30-days'):
    """
    Fetch daily visitor counts for trend analysis.

    Returns:
        list of dicts with date and visitor count
    """
    data = clicky_request(
        site_id, sitekey,
        type_param='visitors',
        date=date,
        limit=100,
        extra_params={'daily': '1'},
    )
    return data


def analyze_referral_patterns(referrers):
    """
    Analyze referral traffic for engagement patterns.

    Categorizes referral sources and identifies where engagement is most productive.

    Returns:
        dict with categorized referrers, top sources, and engagement recommendations
    """
    categories = {
        'social': [],         # Reddit, Twitter/X, LinkedIn, Facebook, etc.
        'search': [],         # Google, Bing, DuckDuckGo, etc.
        'community': [],      # HackerNews, Dev.to, forums, Discord, Slack
        'aggregator': [],     # RSS readers, newsletters, Pocket, Flipboard
        'direct_referral': [],  # Other blogs, articles linking to you
        'other': [],
    }

    social_domains = {
        'reddit.com', 'old.reddit.com', 'www.reddit.com',
        'twitter.com', 'x.com', 't.co',
        'linkedin.com', 'www.linkedin.com',
        'facebook.com', 'www.facebook.com', 'm.facebook.com',
        'mastodon.social', 'threads.net',
        'bsky.app',
        'chatgpt.com',
    }

    search_domains = {
        'google.com', 'www.google.com', 'google.co.uk',
        'bing.com', 'www.bing.com',
        'duckduckgo.com',
        'search.yahoo.com', 'yahoo.com',
        'baidu.com', 'yandex.com',
    }

    community_domains = {
        'news.ycombinator.com',
        'dev.to',
        'hashnode.com',
        'medium.com',
        'lobste.rs',
        'stackoverflow.com',
        'producthunt.com',
        'indiehackers.com',
        'discord.com', 'discord.gg',
    }

    aggregator_domains = {
        'feedly.com', 'newsblur.com', 'theoldreader.com',
        'pocket.co', 'getpocket.com',
        'flipboard.com',
    }

    for ref in referrers:
        domain = ref.get('title', '').lower().strip()
        visits = int(ref.get('value', 0))

        entry = {
            'domain': domain,
            'visits': visits,
            'percent': ref.get('value_percent', '0'),
        }

        # Categorize
        matched = False
        for known_domain in social_domains:
            if known_domain in domain:
                categories['social'].append(entry)
                matched = True
                break
        if not matched:
            for known_domain in search_domains:
                if known_domain in domain:
                    categories['search'].append(entry)
                    matched = True
                    break
        if not matched:
            for known_domain in community_domains:
                if known_domain in domain:
                    categories['community'].append(entry)
                    matched = True
                    break
        if not matched:
            for known_domain in aggregator_domains:
                if known_domain in domain:
                    categories['aggregator'].append(entry)
                    matched = True
                    break
        if not matched:
            if domain and visits > 0:
                categories['direct_referral'].append(entry)
            else:
                categories['other'].append(entry)

    # Sort each category by visits descending
    for cat in categories:
        categories[cat].sort(key=lambda x: -x['visits'])

    return categories


def identify_trending_articles(pages, previous_pages=None):
    """
    Identify articles that are gaining momentum.

    If previous_pages is provided, compares current vs previous period
    to detect growth trends.

    Args:
        pages: Current period top pages
        previous_pages: Previous period top pages (optional)

    Returns:
        list of trending article dicts with growth info
    """
    trending = []

    if not previous_pages:
        # Without comparison data, just identify top performers
        for page in pages[:20]:
            title = page.get('title', '')
            visits = int(page.get('value', 0))

            # Skip non-article pages (homepage, category pages, etc.)
            if title in ('/', '') or '/category/' in title or '/tag/' in title:
                continue

            trending.append({
                'url': title,
                'current_visits': visits,
                'growth': None,
                'status': 'top_performer',
            })
        return trending

    # Build lookup for previous period
    prev_lookup = {}
    for page in previous_pages:
        prev_lookup[page.get('title', '')] = int(page.get('value', 0))

    # Titles that indicate non-content pages to skip
    skip_title_fragments = ('page not found', '404', 'error 404', 'not found')

    for page in pages:
        title = page.get('title', '')
        current_visits = int(page.get('value', 0))
        url = page.get('url', '')

        if title in ('/', '') or '/category/' in title or '/tag/' in title:
            continue

        # Skip 404 / error pages
        if any(frag in title.lower() for frag in skip_title_fragments):
            continue

        prev_visits = prev_lookup.get(title, 0)

        if prev_visits > 0:
            growth_pct = round(((current_visits - prev_visits) / prev_visits) * 100, 1)
        elif current_visits > 0:
            growth_pct = 100.0  # New article, all growth
        else:
            continue

        status = 'declining'
        if growth_pct > 50:
            status = 'surging'
        elif growth_pct > 20:
            status = 'growing'
        elif growth_pct > 0:
            status = 'stable_up'
        elif growth_pct == 0:
            status = 'flat'

        trending.append({
            'url': title,
            'current_visits': current_visits,
            'previous_visits': prev_visits,
            'growth_pct': growth_pct,
            'status': status,
        })

    # Deduplicate by URL (keep highest visit count entry)
    seen_urls = {}
    for item in trending:
        url = item['url']
        if url not in seen_urls or item['current_visits'] > seen_urls[url]['current_visits']:
            seen_urls[url] = item
    trending = list(seen_urls.values())

    # Sort by growth percentage descending
    trending.sort(key=lambda x: -(x.get('growth_pct', 0)))

    return trending


def generate_engagement_recommendations(referral_categories, trending_articles, search_terms=None):
    """
    Generate actionable engagement recommendations based on traffic patterns.

    Analyzes where traffic comes from, what content performs well, and suggests
    specific places to engage (comment, post, share) for maximum impact.

    Returns:
        list of recommendation dicts with action, platform, reasoning, priority
    """
    recommendations = []

    # --- Recommendation: Double down on active referral sources ---
    social = referral_categories.get('social', [])
    for source in social[:3]:
        if source['visits'] >= 5:
            platform = source['domain'].split('.')[0].replace('www', '').strip('.')
            if not platform:
                platform = source['domain']
            recommendations.append({
                'action': f"Increase engagement on {platform.title()}",
                'platform': source['domain'],
                'reasoning': f"{source['visits']} visits from {source['domain']} — this channel is already working. "
                             f"Share more content, engage in relevant threads, respond to comments.",
                'priority': 'high',
                'type': 'amplify_existing',
            })

    # --- Recommendation: Engage in communities driving traffic ---
    communities = referral_categories.get('community', [])
    for source in communities[:3]:
        if source['visits'] >= 3:
            recommendations.append({
                'action': f"Participate actively on {source['domain']}",
                'platform': source['domain'],
                'reasoning': f"{source['visits']} visits from {source['domain']}. Community traffic converts well. "
                             f"Comment on related discussions, share expertise (not just links).",
                'priority': 'high',
                'type': 'community_engagement',
            })

    # --- Recommendation: Explore untapped communities ---
    active_community_domains = {s['domain'] for s in communities}
    potential_communities = [
        ('news.ycombinator.com', 'Hacker News — great for technical/startup content'),
        ('dev.to', 'Dev.to — republish technical articles for developer audience'),
        ('reddit.com', 'Reddit — find relevant subreddits for your niche'),
        ('indiehackers.com', 'Indie Hackers — share building-in-public stories'),
        ('lobste.rs', 'Lobsters — curated tech community, high-quality traffic'),
    ]
    for domain, description in potential_communities:
        if not any(domain in d for d in active_community_domains):
            recommendations.append({
                'action': f"Consider posting/engaging on {domain}",
                'platform': domain,
                'reasoning': f"No traffic detected from {description}. "
                             f"This could be an untapped channel worth testing.",
                'priority': 'low',
                'type': 'explore_new',
            })

    # --- Recommendation: Capitalize on trending articles ---
    surging = [a for a in trending_articles if a.get('status') == 'surging']
    growing = [a for a in trending_articles if a.get('status') == 'growing']

    for article in (surging + growing)[:5]:
        growth_str = f" (+{article['growth_pct']}%)" if article.get('growth_pct') is not None else ""
        recommendations.append({
            'action': f"Promote trending article: {article['url']}",
            'platform': 'cross-platform',
            'reasoning': f"This article is {article['status']}{growth_str} with "
                         f"{article['current_visits']} visits. Share it on social, "
                         f"link to it from related discussions, consider writing a follow-up.",
            'priority': 'high' if article['status'] == 'surging' else 'medium',
            'type': 'promote_trending',
        })

    # --- Recommendation: Direct referral sites to engage with ---
    direct_refs = referral_categories.get('direct_referral', [])
    for source in direct_refs[:5]:
        if source['visits'] >= 2:
            recommendations.append({
                'action': f"Engage with {source['domain']}",
                'platform': source['domain'],
                'reasoning': f"{source['visits']} visits from this site — someone is linking to your content. "
                             f"Find the linking article, leave a thoughtful comment, consider guest posting or collaboration.",
                'priority': 'medium',
                'type': 'relationship_building',
            })

    # --- Recommendation: SEO opportunities from search terms ---
    if search_terms:
        for term in search_terms[:5]:
            keyword = term.get('title', '')
            visits = int(term.get('value', 0))
            if visits >= 2 and keyword:
                recommendations.append({
                    'action': f"Create/optimize content for: '{keyword}'",
                    'platform': 'organic search',
                    'reasoning': f"'{keyword}' is driving {visits} visits via search. "
                                 f"Consider writing a dedicated article targeting this keyword, "
                                 f"or expanding existing content that ranks for it.",
                    'priority': 'medium',
                    'type': 'seo_opportunity',
                })

    # Sort: high priority first
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))

    return recommendations


def run_analysis(domain, days=30, compare=True):
    """
    Run a full traffic analysis for a site.

    Args:
        domain: Site domain (e.g. 'brianchappell.com')
        days: Number of days to analyze
        compare: Whether to compare with previous period for trends

    Returns:
        dict with full analysis results
    """
    site_id, sitekey = get_site_credentials(domain)
    if not site_id or not sitekey:
        print(f"Error: No Clicky credentials found for {domain}", file=sys.stderr)
        print(f"Set CLICKY_SITE_ID_{SITE_CONFIG.get(domain, domain.split('.')[0].upper())} "
              f"and CLICKY_SITEKEY_{SITE_CONFIG.get(domain, domain.split('.')[0].upper())} "
              f"in your .env file", file=sys.stderr)
        return None

    date_range = f'last-{days}-days'
    prev_date_range = f'last-{days * 2}-days'  # Double the range for comparison

    print(f"Fetching traffic data for {domain} (last {days} days)...")

    # Fetch current period data
    referrers = fetch_referral_traffic(site_id, sitekey, date=date_range)        # links-domains
    traffic_sources = fetch_traffic_sources(site_id, sitekey, date=date_range)   # traffic-sources
    pages = fetch_top_pages(site_id, sitekey, date=date_range)                   # pages
    search_terms = fetch_search_terms(site_id, sitekey, date=date_range)         # searches

    # Fetch previous period for comparison
    previous_pages = None
    if compare and days <= 90:
        # For comparison we fetch a wider range - the "previous" period is implicit
        # We use a simple approach: fetch 2x the range and compare halves
        wider_pages = fetch_top_pages(site_id, sitekey, date=prev_date_range, limit=200)
        if wider_pages:
            previous_pages = wider_pages

    # Analyze patterns
    referral_categories = analyze_referral_patterns(referrers)
    trending = identify_trending_articles(pages, previous_pages)
    recommendations = generate_engagement_recommendations(
        referral_categories, trending, search_terms
    )

    analysis = {
        'domain': domain,
        'period': f'last {days} days',
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'summary': {
            'total_referral_sources': len(referrers),
            'total_pages_tracked': len(pages),
            'total_search_terms': len(search_terms),
            'trending_articles': len([t for t in trending if t.get('status') in ('surging', 'growing')]),
        },
        'traffic_sources': [
            {'source': t.get('title', ''), 'visits': int(t.get('value', 0))}
            for t in traffic_sources
        ],
        'referral_categories': {
            cat: sources for cat, sources in referral_categories.items() if sources
        },
        'trending_articles': trending[:20],
        'search_terms': [
            {'term': t.get('title', ''), 'visits': int(t.get('value', 0))}
            for t in search_terms[:20]
        ],
        'recommendations': recommendations,
    }

    return analysis


def print_analysis(analysis):
    """Pretty-print a traffic analysis."""
    if not analysis:
        return

    print(f"\n{'=' * 70}")
    print(f"BLOGCLAW TRAFFIC ANALYSIS — {analysis['domain'].upper()}")
    print(f"Period: {analysis['period']}")
    print(f"{'=' * 70}")

    summary = analysis['summary']
    print(f"\n  Referral sources: {summary['total_referral_sources']}")
    print(f"  Pages tracked: {summary['total_pages_tracked']}")
    print(f"  Search terms: {summary['total_search_terms']}")
    print(f"  Trending articles: {summary['trending_articles']}")

    # Referral breakdown
    categories = analysis.get('referral_categories', {})
    if categories:
        print(f"\n  {'─' * 50}")
        print(f"  REFERRAL TRAFFIC BREAKDOWN")
        print(f"  {'─' * 50}")

        for cat_name, sources in categories.items():
            if not sources:
                continue
            total_visits = sum(s['visits'] for s in sources)
            label = cat_name.replace('_', ' ').title()
            print(f"\n    {label} ({total_visits} total visits):")
            for source in sources[:5]:
                print(f"      {source['domain']}: {source['visits']} visits")

    # Trending articles
    trending = analysis.get('trending_articles', [])
    if trending:
        print(f"\n  {'─' * 50}")
        print(f"  TRENDING ARTICLES")
        print(f"  {'─' * 50}")

        for article in trending[:10]:
            status_emoji = {
                'surging': '🚀',
                'growing': '📈',
                'stable_up': '↗️',
                'flat': '→',
                'declining': '📉',
                'top_performer': '⭐',
            }.get(article['status'], '•')

            growth_str = ''
            if article.get('growth_pct') is not None:
                growth_str = f" ({'+' if article['growth_pct'] > 0 else ''}{article['growth_pct']}%)"

            print(f"    {status_emoji} {article['url']}")
            print(f"       {article['current_visits']} visits{growth_str}")

    # Search terms
    search_terms = analysis.get('search_terms', [])
    if search_terms:
        print(f"\n  {'─' * 50}")
        print(f"  TOP SEARCH TERMS")
        print(f"  {'─' * 50}")

        for term in search_terms[:10]:
            print(f"    \"{term['term']}\" — {term['visits']} visits")

    # Recommendations
    recommendations = analysis.get('recommendations', [])
    if recommendations:
        print(f"\n  {'─' * 50}")
        print(f"  ENGAGEMENT RECOMMENDATIONS")
        print(f"  {'─' * 50}")

        for i, rec in enumerate(recommendations, 1):
            priority_badge = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢',
            }.get(rec['priority'], '•')

            print(f"\n    {priority_badge} [{rec['priority'].upper()}] {rec['action']}")
            print(f"       {rec['reasoning']}")


def main():
    parser = argparse.ArgumentParser(
        description='BlogClaw Traffic Analyzer - Clicky analytics for referral patterns & engagement opportunities',
        epilog='Part of the BlogClaw self-improving blog system (OpenClaw / NanoClaw ecosystem)'
    )
    parser.add_argument('--site', help='Site domain to analyze (e.g. brianchappell.com)')
    parser.add_argument('--all', action='store_true', help='Analyze all configured sites')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
    parser.add_argument('--no-compare', action='store_true', help='Skip trend comparison with previous period')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    load_env()

    sites = []
    if args.all:
        sites = list(SITE_CONFIG.keys())
    elif args.site:
        sites = [args.site]
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python3 analyze_traffic.py --site brianchappell.com")
        print("  python3 analyze_traffic.py --site consultdex.com --days 7")
        print("  python3 analyze_traffic.py --all --json")
        sys.exit(1)

    all_analyses = []

    for site in sites:
        analysis = run_analysis(site, days=args.days, compare=not args.no_compare)
        if analysis:
            all_analyses.append(analysis)
            if not args.json:
                print_analysis(analysis)

    if args.json:
        print(json.dumps(all_analyses if len(all_analyses) > 1 else all_analyses[0], indent=2))

    if not all_analyses:
        print("\nNo analyses completed. Check your Clicky credentials in .env", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
