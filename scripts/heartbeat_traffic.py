#!/usr/bin/env python3
"""
BlogClaw Traffic Heartbeat - Runs weekly (Sunday 10 AM)
Analyzes referral traffic patterns and updates TRAFFIC_ANALYSIS.md

Also runs a lighter daily check to catch traffic spikes.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path to import analyze_traffic
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_traffic import (
    load_env,
    run_analysis,
    SITE_CONFIG,
)


def update_traffic_log(analyses, log_path, period_label='Weekly'):
    """
    Update TRAFFIC_ANALYSIS.md with the latest traffic findings.

    Args:
        analyses: List of analysis dicts from run_analysis()
        log_path: Path to TRAFFIC_ANALYSIS.md
        period_label: 'Weekly' or 'Daily'
    """
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    today_formatted = datetime.now(timezone.utc).strftime('%B %d, %Y')

    # Read existing log
    if log_path.exists():
        with open(log_path) as f:
            content = f.read()
    else:
        content = (
            "# Traffic Analysis Log\n\n"
            "Automated referral traffic analysis powered by BlogClaw + Clicky.\n\n"
            "## How to Read This Log\n\n"
            "- **Referral Categories**: Where your traffic comes from (social, search, community, direct links)\n"
            "- **Trending Articles**: Content gaining momentum — prioritize promotion\n"
            "- **Engagement Recommendations**: Specific actions to take based on traffic patterns\n"
            "- **Patterns**: Recurring trends across multiple analysis periods\n\n"
            "---\n"
        )

    # Check if today's entry already exists
    if f"## {period_label} Report — {today}" in content:
        print(f"Entry for {today} ({period_label}) already exists in log")
        return

    # Build entry
    lines = [
        f"\n---\n",
        f"\n## {period_label} Report — {today_formatted}\n",
    ]

    for analysis in analyses:
        domain = analysis['domain']
        summary = analysis['summary']

        lines.append(f"\n### {domain}\n")
        lines.append(f"\n**Period:** {analysis['period']}\n")
        lines.append(f"\n**Summary:**\n")
        lines.append(f"- Referral sources: {summary['total_referral_sources']}\n")
        lines.append(f"- Pages tracked: {summary['total_pages_tracked']}\n")
        lines.append(f"- Search terms: {summary['total_search_terms']}\n")
        lines.append(f"- Trending articles: {summary['trending_articles']}\n")

        # Referral breakdown
        categories = analysis.get('referral_categories', {})
        if categories:
            lines.append(f"\n**Referral Traffic:**\n")
            for cat_name, sources in categories.items():
                if not sources:
                    continue
                label = cat_name.replace('_', ' ').title()
                total = sum(s['visits'] for s in sources)
                top_sources = ', '.join(
                    f"{s['domain']} ({s['visits']})"
                    for s in sources[:3]
                )
                lines.append(f"- {label}: {total} visits — {top_sources}\n")

        # Trending articles
        trending = analysis.get('trending_articles', [])
        if trending:
            lines.append(f"\n**Trending Content:**\n")
            for article in trending[:5]:
                status = article.get('status', 'unknown')
                growth_str = ''
                if article.get('growth_pct') is not None:
                    sign = '+' if article['growth_pct'] > 0 else ''
                    growth_str = f" ({sign}{article['growth_pct']}%)"
                emoji = {
                    'surging': '🚀',
                    'growing': '📈',
                    'stable_up': '↗️',
                    'top_performer': '⭐',
                }.get(status, '•')
                lines.append(
                    f"- {emoji} `{article['url']}` — "
                    f"{article['current_visits']} visits{growth_str}\n"
                )

        # Search terms
        search_terms = analysis.get('search_terms', [])
        if search_terms:
            lines.append(f"\n**Top Search Terms:**\n")
            for term in search_terms[:5]:
                lines.append(f"- \"{term['term']}\" — {term['visits']} visits\n")

        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            lines.append(f"\n**Engagement Recommendations:**\n")
            for rec in recommendations[:8]:
                priority_badge = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢',
                }.get(rec['priority'], '•')
                lines.append(f"- {priority_badge} **{rec['action']}**\n")
                lines.append(f"  {rec['reasoning']}\n")

    # Cross-site patterns (if multiple sites)
    if len(analyses) > 1:
        lines.append(f"\n### Cross-Site Patterns\n")

        # Find shared referral sources
        all_referrers = {}
        for analysis in analyses:
            for cat, sources in analysis.get('referral_categories', {}).items():
                for source in sources:
                    domain_key = source['domain']
                    if domain_key not in all_referrers:
                        all_referrers[domain_key] = {'sites': [], 'total_visits': 0}
                    all_referrers[domain_key]['sites'].append(analysis['domain'])
                    all_referrers[domain_key]['total_visits'] += source['visits']

        shared = {
            k: v for k, v in all_referrers.items()
            if len(v['sites']) > 1
        }
        if shared:
            lines.append(f"\n**Shared Referral Sources (driving traffic to multiple sites):**\n")
            for domain, info in sorted(shared.items(), key=lambda x: -x[1]['total_visits']):
                sites_str = ', '.join(info['sites'])
                lines.append(f"- {domain}: {info['total_visits']} total visits across {sites_str}\n")
        else:
            lines.append(f"\nNo shared referral sources detected across sites.\n")

    # Append to log
    with open(log_path, 'a') as f:
        f.writelines(lines)

    print(f"✓ Updated {log_path}")


def main():
    parser = argparse.ArgumentParser(description='BlogClaw Traffic Heartbeat')
    parser.add_argument('--sites', nargs='+',
                        help='Sites to analyze (default: all configured sites)')
    parser.add_argument('--days', type=int, default=7,
                        help='Days to analyze (default: 7 for weekly, use 1 for daily)')
    parser.add_argument('--period', choices=['daily', 'weekly', 'monthly'],
                        default='weekly', help='Report period label')
    parser.add_argument('--learning-dir', default='learning',
                        help='Learning files directory')
    parser.add_argument('--json', action='store_true',
                        help='Also output raw JSON')

    args = parser.parse_args()

    load_env()

    # Determine sites to analyze
    sites = args.sites or list(SITE_CONFIG.keys())

    period_label = args.period.title()
    days = args.days
    if args.period == 'daily' and args.days == 7:
        days = 1  # Override default for daily
    elif args.period == 'monthly' and args.days == 7:
        days = 30  # Override default for monthly

    print(f"BlogClaw Traffic Heartbeat — {period_label}")
    print(f"Analyzing {len(sites)} site(s) for the last {days} day(s)...\n")

    # Run analysis for each site
    analyses = []
    for site in sites:
        print(f"Analyzing {site}...")
        try:
            analysis = run_analysis(site, days=days, compare=True)
            if analysis:
                analyses.append(analysis)
                rec_count = len(analysis.get('recommendations', []))
                trending_count = analysis['summary']['trending_articles']
                print(f"  ✓ {analysis['summary']['total_referral_sources']} referral sources, "
                      f"{trending_count} trending articles, "
                      f"{rec_count} recommendations")
            else:
                print(f"  ✗ Analysis failed for {site}")
        except Exception as e:
            print(f"  ✗ Error analyzing {site}: {e}")

    if not analyses:
        print("\nNo analyses completed. Check credentials.", file=sys.stderr)
        sys.exit(1)

    # Update traffic log
    learning_dir = Path(args.learning_dir)
    learning_dir.mkdir(parents=True, exist_ok=True)

    log_path = learning_dir / 'TRAFFIC_ANALYSIS.md'
    update_traffic_log(analyses, log_path, period_label=period_label)

    # Optionally dump JSON
    if args.json:
        json_path = learning_dir / f'traffic_{args.period}_{datetime.now().strftime("%Y%m%d")}.json'
        with open(json_path, 'w') as f:
            json.dump(analyses, f, indent=2)
        print(f"✓ JSON saved to {json_path}")

    # Summary
    total_recs = sum(len(a.get('recommendations', [])) for a in analyses)
    total_trending = sum(a['summary']['trending_articles'] for a in analyses)

    print(f"\n✓ {period_label} traffic heartbeat complete")
    print(f"  Sites analyzed: {len(analyses)}")
    print(f"  Trending articles: {total_trending}")
    print(f"  Engagement recommendations: {total_recs}")


if __name__ == '__main__':
    main()
