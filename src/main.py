#!/usr/bin/env python3

import json
from pathlib import Path
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scraper import NHKEasyScraper
from furigana_processor import FuriganaProcessor
from site_generator import SiteGenerator
from wanikani_levels import WaniKaniLevels


def fail(message):
    """Abort the pipeline with a non-zero exit, surfaced as an error annotation in GitHub Actions."""
    print(f"   ❌ {message}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::error title=NHK pipeline failed::{message}")
    sys.exit(1)


def main():
    """Main pipeline to scrape, process, and generate the site"""
    print("=== NHK Easy News Pipeline ===")

    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    try:
        # Step 1: Generate WaniKani level data for frontend
        print("\n1. Generating WaniKani level data for frontend...")
        wk_levels = WaniKaniLevels("data/kanji-wanikani.json")
        wk_levels.export_to_js("docs/wanikani-data.js")
        print(f"   Exported level data for {len(wk_levels.kanji_by_level)} levels")

    except Exception as e:
        print(f"   Warning: Failed to generate WaniKani data: {e}")
        print("   Continuing without level data...")

    try:
        # Step 2: Scrape NHK Easy News
        print("\n2. Scraping NHK Easy News...")
        scraper = NHKEasyScraper()
        articles = scraper.scrape_all()

        if not articles:
            fail("No articles scraped (0 pages). Check NHK auth and the news-list API.")

        # Save raw articles
        scraper.save_articles(articles, "data/articles.json")

    except Exception as e:
        fail(f"Error scraping articles: {e}")

    try:
        # Step 3: Process articles with furigana
        print("\n3. Processing articles with furigana...")
        processor = FuriganaProcessor("data/kanji-wanikani.json")

        processed_articles = []
        for i, article in enumerate(articles, 1):
            print(f"   Processing article {i}/{len(articles)}: {article.get('title', 'Untitled')[:50]}...")

            try:
                processed_article = processor.process_article(article)
                processed_articles.append(processed_article)

                # Print stats
                stats = processed_article.get("stats", {})
                if stats:
                    total_kanji = stats.get('total_kanji', 0)
                    levels_present = len([k for k in stats.get('kanji_by_level', {}).keys() if k != 0])
                    print(f"     漢字: {total_kanji}, Levels present: {levels_present}")

            except Exception as e:
                print(f"     Error processing article: {e}")
                continue

        # Save processed articles
        processed_path = "data/processed_articles.json"
        with open(processed_path, "w", encoding="utf-8") as f:
            json.dump(processed_articles, f, ensure_ascii=False, indent=2)

        print(f"   Saved {len(processed_articles)} processed articles to {processed_path}")

    except Exception as e:
        fail(f"Error processing articles: {e}")

    if not processed_articles:
        fail(f"All {len(articles)} scraped articles failed furigana processing (0 pages to publish).")

    try:
        # Step 4: Generate static site
        print("\n4. Generating static site...")
        generator = SiteGenerator()
        generator.generate_site("data/processed_articles.json")

        print("\n=== Pipeline completed successfully! ===")
        print(f"Site generated in: {generator.output_dir}")
        print("You can now deploy the 'docs' directory to GitHub Pages.")

    except Exception as e:
        fail(f"Error generating site: {e}")


if __name__ == "__main__":
    main()