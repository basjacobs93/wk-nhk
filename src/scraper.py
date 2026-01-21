import requests
from bs4 import BeautifulSoup
import json
import yaml
from datetime import datetime
from pathlib import Path
import time
import re
from urllib.parse import urljoin, urlparse
import hashlib
from auth import get_nhk_token


class NHKEasyScraper:
    def __init__(self, config_path="config.yml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.base_url = self.config["scraper"]["base_url"]
        self.json_url = "https://news.web.nhk/news/easy/news-list.json"
        self.max_articles = self.config["scraper"]["max_articles"]
        self.timeout = self.config["scraper"]["timeout"]

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Get fresh authentication token
        print("Obtaining fresh authentication token...")
        try:
            token = get_nhk_token()
            # Set cookie properly using session.cookies.set() with correct domain
            self.session.cookies.set(
                name="z_at",
                value=token,
                domain=".web.nhk",
                path="/"
            )
            print("✅ Authentication token set successfully")
        except Exception as e:
            print(f"⚠️  Failed to obtain authentication token: {e}")
            print("Proceeding without authentication (may fail)...")

        # Create images directory
        self.images_dir = Path("docs/images")
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def get_article_links(self):
        """Get article links from NHK JSON API"""
        try:
            print(f"Fetching article list from JSON API...")
            response = self.session.get(self.json_url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            article_links = []

            # Parse the JSON structure: list of objects with date keys and article arrays
            for item in data:
                if not isinstance(item, dict):
                    continue

                for date_key, articles_array in item.items():
                    if not isinstance(articles_array, list):
                        continue

                    print(f"Processing {len(articles_array)} articles for {date_key}")

                    for article_info in articles_array:
                        if not isinstance(article_info, dict):
                            continue

                        # Extract article information
                        title = article_info.get("title", "")
                        news_id = article_info.get("news_id", "")
                        title_with_ruby = article_info.get("title_with_ruby", "")

                        if title and news_id:
                            # Construct the article URL
                            article_url = f"https://news.web.nhk/news/easy/{news_id}/{news_id}.html"

                            # Get image URI - prefer easy news image, fallback to web image
                            image_uri = article_info.get("news_easy_image_uri", "")
                            web_image_uri = article_info.get("news_web_image_uri", "")

                            if image_uri:
                                image_url = image_uri#f"https://news.web.nhk/news/easy/{news_id}/{image_uri}"
                                image_source = "easy"
                            elif web_image_uri:
                                image_url = web_image_uri
                                image_source = "web"
                            else:
                                image_url = ""
                                image_source = "none"

                            article_links.append({
                                "url": article_url,
                                "title": title,
                                "title_with_ruby": title_with_ruby,
                                "news_id": news_id,
                                "date": date_key,
                                "publication_time": article_info.get("news_publication_time", ""),
                                "has_voice": article_info.get("has_news_easy_voice", False),
                                "has_image": article_info.get("has_news_easy_image", False),
                                "image_uri": image_uri,
                                "image_url": image_url,
                                "image_source": image_source,
                                "voice_uri": article_info.get("news_easy_voice_uri", ""),
                                "original_web_url": article_info.get("news_web_url", "")
                            })

                        # Limit the number of articles
                        if len(article_links) >= self.max_articles:
                            break

                    if len(article_links) >= self.max_articles:
                        break

                if len(article_links) >= self.max_articles:
                    break

            print(f"Found {len(article_links)} articles from JSON API")
            return article_links

        except Exception as e:
            print(f"Error fetching article links from JSON API: {e}")
            # Fallback to HTML scraping
            return self._get_article_links_html_fallback()

    def _get_article_links_html_fallback(self):
        """Fallback HTML scraping method"""
        try:
            print("Falling back to HTML scraping...")
            response = self.session.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            article_links = []

            # Try various selectors
            link_selectors = [
                "a[href*='k10']",
                "a[href*='/news/easy/']",
                ".article-link",
                ".news-item a"
            ]

            for selector in link_selectors:
                links = soup.select(selector)
                if links:
                    for link in links[:self.max_articles]:
                        href = link.get("href")
                        if href and "k10" in href:
                            full_url = urljoin(self.base_url, href)
                            title = link.get_text(strip=True)
                            if title:
                                article_links.append({
                                    "url": full_url,
                                    "title": title
                                })
                    if article_links:
                        break

            return article_links[:self.max_articles]

        except Exception as e:
            print(f"HTML fallback also failed: {e}")
            return []

    def download_image(self, image_url, news_id):
        """Download article image and return local path"""
        if not image_url:
            return None

        try:
            # Extract filename from URL
            filename = image_url.split("/")[-1]
            if not filename or "." not in filename:
                return None

            # Create safe filename
            safe_filename = f"{news_id}_{filename}"
            local_path = self.images_dir / safe_filename

            # Skip if already downloaded
            if local_path.exists():
                print(f"      Image already exists: {safe_filename}")
                return f"images/{safe_filename}"

            print(f"      Downloading image: {filename}")
            response = self.session.get(image_url, timeout=self.timeout)
            response.raise_for_status()

            # Save image
            with open(local_path, "wb") as f:
                f.write(response.content)

            print(f"      ✅ Saved image: {safe_filename} ({len(response.content):,} bytes)")
            return f"images/{safe_filename}"

        except Exception as e:
            print(f"      ⚠️  Failed to download image {image_url}: {e}")
            return None

    def scrape_article(self, article_url):
        """Scrape individual article content"""
        try:
            response = self.session.get(article_url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract article data
            article_data = {
                "url": article_url,
                "scraped_at": datetime.now().isoformat(),
                "title": "",
                "content": "",
                "date": "",
                "raw_html": str(soup)
            }

            # NHK Easy News specific selectors
            title_selectors = [
                "h1#news_title",
                ".article-main__title",
                "h1",
                ".news-title",
                "title"
            ]

            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    article_data["title"] = title_elem.get_text(strip=True)
                    break

            # NHK Easy News content selectors
            content_selectors = [
                "#js-article-body",
                ".article-main__body",
                ".article-body",
                "#news_body",
                ".content-body",
                "article .body"
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Get text content, preserving paragraph breaks
                    paragraphs = content_elem.find_all(["p", "div"], recursive=True)
                    if paragraphs:
                        content_text = []
                        for para in paragraphs:
                            text = para.get_text(strip=True)
                            if text and len(text) > 10:  # Filter out short fragments
                                content_text.append(text)
                        if content_text:
                            article_data["content"] = "\n\n".join(content_text)
                            break
                    else:
                        # Fallback: get all text from the container
                        text = content_elem.get_text(strip=True)
                        if text and len(text) > 50:
                            article_data["content"] = text
                            break

            # NHK Easy News date selectors
            date_selectors = [
                ".article-main__date",
                ".news-date",
                "time",
                ".date",
                "[datetime]"
            ]

            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                    article_data["date"] = date_text
                    break

            # Clean up content
            if article_data["content"]:
                # Remove extra whitespace
                article_data["content"] = re.sub(r"\s+", " ", article_data["content"])
                # Remove common noise
                article_data["content"] = re.sub(r"(シェア|ツイート|印刷|メール|.*さんの.*)", "", article_data["content"])

            return article_data

        except Exception as e:
            print(f"Error scraping article {article_url}: {e}")
            return None

    def scrape_all(self):
        """Scrape all articles and return data"""
        print("Fetching article links...")
        article_links = self.get_article_links()

        if not article_links:
            print("No article links found. Check scraper selectors.")
            return []

        print(f"Found {len(article_links)} article links")

        articles = []
        for i, link_data in enumerate(article_links, 1):
            print(f"Scraping article {i}/{len(article_links)}: {link_data['title'][:50]}...")

            article = self.scrape_article(link_data["url"])
            if article and article["content"]:
                # Add metadata from JSON API
                article.update({
                    "news_id": link_data.get("news_id", ""),
                    "date": link_data.get("date", ""),
                    "publication_time": link_data.get("publication_time", ""),
                    "has_voice": link_data.get("has_voice", False),
                    "has_image": link_data.get("has_image", False),
                    "title_with_ruby": link_data.get("title_with_ruby", ""),
                    "image_url": link_data.get("image_url", ""),
                    "image_uri": link_data.get("image_uri", ""),
                    "image_source": link_data.get("image_source", "none")
                })

                # Download image if available
                if article["image_url"]:
                    local_image_path = self.download_image(
                        article["image_url"],
                        article["news_id"]
                    )
                    article["local_image_path"] = local_image_path
                else:
                    article["local_image_path"] = None

                articles.append(article)
                time.sleep(1)  # Be respectful to the server
            else:
                print(f"  Failed to scrape or empty content")

        print(f"Successfully scraped {len(articles)} articles")
        return articles

    def save_articles(self, articles, output_file="articles.json"):
        """Save articles to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(articles)} articles to {output_path}")


if __name__ == "__main__":
    scraper = NHKEasyScraper()
    articles = scraper.scrape_all()
    scraper.save_articles(articles, "data/articles.json")
