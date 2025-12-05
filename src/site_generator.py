import json
import yaml
from pathlib import Path
from datetime import datetime
from jinja2 import Template
import re


class SiteGenerator:
    def __init__(self, config_path="config.yml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.output_dir = Path(self.config["site"]["output_dir"])
        self.site_title = self.config["site"]["title"]
        self.site_description = self.config["site"]["description"]
        self.goatcounter_code = self.config["site"].get("goatcounter_code", "")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_articles(self, articles_file="data/processed_articles.json"):
        """Load processed articles from file"""
        articles_path = Path(articles_file)

        if not articles_path.exists():
            print(f"Warning: {articles_file} not found")
            return []

        try:
            with open(articles_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading articles: {e}")
            return []

    def _create_article_slug(self, title, url):
        """Create a URL-friendly slug for an article"""
        # Extract article ID from URL if possible
        url_match = re.search(r"k10(\d+)", url)
        if url_match:
            return f"article-{url_match.group(1)}"

        # Fallback: create slug from title
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug[:50]  # Limit length

    def generate_index_page(self, articles):
        """Generate the main index page"""
        template_str = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_title }} - Japanese News with Level-based Furigana</title>
    <meta name="description" content="{{ site_description }}">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header class="site-header">
        <div class="container header-container">
            <div class="header-left">
                <h1>{{ site_title }}</h1>
                <span class="site-description">{{ site_description }}</span>
            </div>

            <div class="controls">
                <div class="level-control">
                    <label for="level-slider" class="level-label">
                        <span>WaniKani Level: </span>
                        <span id="level-value" class="level-value">10</span>
                    </label>
                    <input type="range" id="level-slider" min="0" max="60" value="10" class="level-slider">
                </div>

                <label class="toggle-label">
                    <input type="checkbox" id="show-all-toggle">
                    <span class="slider"></span>
                    <span class="label-text">Show all</span>
                </label>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="articles-list">
            {% if articles %}
                <div class="articles-grid">
                    {% for article in articles %}
                    <article class="article-card">
                        <a href="{{ article.slug }}.html" class="card-link">
                            <div class="article-header">
                                <h3 class="article-title">{{ article.title_html|safe }}</h3>
                                {% if article.date %}
                                <time class="article-date">{{ article.date }}</time>
                                {% endif %}
                            </div>

                            {% if article.local_image_path %}
                            <div class="article-image">
                                <img src="{{ article.local_image_path }}" alt="{{ article.title }}" loading="lazy">
                            </div>
                            {% endif %}

                            <div class="article-preview">
                                {{ article.content_preview_html|safe }}...
                            </div>
                        </a>

                        <div class="article-footer">
                            <a href="{{ article.url }}" target="_blank" class="original-link" onclick="event.stopPropagation()">元記事</a>
                        </div>
                    </article>
                    {% endfor %}
                </div>
            {% else %}
                <p class="no-articles">記事が見つかりませんでした。</p>
            {% endif %}
        </section>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>Last updated: {{ current_time }}</p>
            <p>Data from <a href="https://news.web.nhk/news/easy/" target="_blank">NHK News Web Easy</a></p>
        </div>
    </footer>

    <script src="wanikani-data.js"></script>
    <script src="script.js"></script>
    {% if goatcounter_code %}
    <script data-goatcounter="https://{{ goatcounter_code }}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
    {% endif %}
</body>
</html>"""

        template = Template(template_str)

        # Prepare articles with slugs
        for article in articles:
            article["slug"] = self._create_article_slug(
                article.get("title", ""), article.get("url", "")
            )

        html = template.render(
            site_title=self.site_title,
            site_description=self.site_description,
            articles=articles,
            current_time=datetime.now().strftime("%Y年%m月%d日 %H:%M"),
            goatcounter_code=self.goatcounter_code,
        )

        index_path = self.output_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Generated index page: {index_path}")

    def generate_article_page(self, article):
        """Generate individual article page"""
        template_str = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ article.title }} - {{ site_title }}</title>
    <meta name="description" content="{{ article.title }}">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header class="site-header">
        <div class="container header-container">
            <div class="header-left">
                <nav class="breadcrumb">
                    <a href="index.html">{{ site_title }}</a> > <span>記事</span>
                </nav>
            </div>

            <div class="controls">
                <div class="level-control">
                    <label for="level-slider" class="level-label">
                        <span>WaniKani Level: </span>
                        <span id="level-value" class="level-value">10</span>
                    </label>
                    <input type="range" id="level-slider" min="0" max="60" value="10" class="level-slider">
                </div>

                <label class="toggle-label">
                    <input type="checkbox" id="show-all-toggle">
                    <span class="slider"></span>
                    <span class="label-text">Show all</span>
                </label>
            </div>
        </div>
    </header>

    <main class="container">
        <article class="article-full">
            <header class="article-header">
                <h1 class="article-title">{{ article.title_html|safe }}</h1>

                {% if article.date %}
                <time class="article-date">{{ article.date }}</time>
                {% endif %}

            </header>

            {% if article.local_image_path %}
            <div class="article-image-full">
                <img src="{{ article.local_image_path }}" alt="{{ article.title }}">
            </div>
            {% endif %}

            <div class="article-content">
                {{ article.content_html|safe }}
            </div>

            <footer class="article-footer">
                <a href="{{ article.url }}" target="_blank" class="original-link">元記事を見る</a>
                <a href="index.html" class="back-link">記事一覧に戻る</a>
            </footer>
        </article>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>Data from <a href="https://news.web.nhk/news/easy/" target="_blank">NHK News Web Easy</a></p>
        </div>
    </footer>

    <script src="wanikani-data.js"></script>
    <script src="script.js"></script>
    {% if goatcounter_code %}
    <script data-goatcounter="https://{{ goatcounter_code }}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
    {% endif %}
</body>
</html>"""

        template = Template(template_str)

        slug = self._create_article_slug(
            article.get("title", ""), article.get("url", "")
        )

        html = template.render(site_title=self.site_title, article=article, goatcounter_code=self.goatcounter_code)

        article_path = self.output_dir / f"{slug}.html"
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(html)

        return slug

    def generate_css(self):
        """Generate CSS file"""
        css_content = """/* CSS Reset and Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

/* Ensure ruby elements are not affected by reset */
ruby, rt {
    margin: unset;
    padding: unset;
    box-sizing: unset;
}

body {
    font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Noto Sans CJK JP', sans-serif;
    line-height: 1.7;
    color: #333;
    background-color: #f8f9fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header */
.site-header {
    background: #4a5568;
    color: white;
    padding: 1rem 0;
    margin-bottom: 2rem;
}

.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 2rem;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.site-header h1 {
    font-size: 1.5rem;
    margin: 0;
    font-weight: 600;
}

.site-description {
    font-size: 0.9rem;
    opacity: 0.85;
    font-weight: 300;
}

.breadcrumb {
    font-size: 0.95rem;
}

.breadcrumb a {
    color: white;
    text-decoration: none;
}

.breadcrumb a:hover {
    text-decoration: underline;
}

/* Controls */
.controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.level-control {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.level-label {
    font-size: 0.9rem;
    font-weight: 400;
    display: flex;
    align-items: center;
    gap: 0.3rem;
    white-space: nowrap;
}

.level-value {
    font-weight: 600;
    font-size: 1rem;
    min-width: 1.5rem;
    text-align: center;
}

.level-slider {
    width: 200px;
    height: 6px;
    border-radius: 3px;
    background: rgba(255,255,255,0.3);
    outline: none;
    -webkit-appearance: none;
}

.level-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: white;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.level-slider::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: white;
    cursor: pointer;
    border: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.toggle-label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    cursor: pointer;
    user-select: none;
}

.toggle-label input[type="checkbox"] {
    display: none;
}

.slider {
    width: 40px;
    height: 20px;
    background: rgba(255,255,255,0.3);
    border-radius: 20px;
    position: relative;
    transition: background 0.3s;
}

.slider:before {
    content: '';
    position: absolute;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: white;
    top: 2px;
    left: 2px;
    transition: transform 0.3s;
}

.toggle-label input:checked + .slider {
    background: rgba(255,255,255,0.6);
}

.toggle-label input:checked + .slider:before {
    transform: translateX(20px);
}

.label-text {
    font-size: 0.85rem;
    font-weight: 300;
}

/* Articles Grid */
.articles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(400px, 100%), 1fr));
    gap: 2rem;
    margin-top: 2rem;
}

.article-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
    display: flex;
    flex-direction: column;
}

.article-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.card-link {
    text-decoration: none;
    color: inherit;
    display: block;
    flex: 1;
}

.card-link:hover {
    text-decoration: none;
}

.article-title {
    font-size: 1.3rem;
    margin-bottom: 0.5rem;
    color: #333;
}

.card-link:hover .article-title {
    color: #667eea;
}

.article-date {
    color: #666;
    font-size: 0.9rem;
    margin-bottom: 1rem;
    display: block;
}

/* Article Stats */
.article-stats {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}

.stat {
    background: #e9ecef;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
}

.stat.unknown {
    background: #fff3cd;
    color: #856404;
}

.stat.known {
    background: #d1ecf1;
    color: #0c5460;
}

/* Article Images */
.article-image {
    margin: 1rem 0;
    border-radius: 8px;
    overflow: hidden;
}

.article-image img {
    width: 100%;
    height: 200px;
    object-fit: cover;
    border-radius: 8px;
    transition: transform 0.2s;
}

.article-image img:hover {
    transform: scale(1.02);
}

.article-image-full {
    margin: 2rem 0;
    text-align: center;
}

.article-image-full img {
    max-width: 100%;
    height: auto;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

/* Article Content */
.article-preview {
    color: #666;
    margin-bottom: 1rem;
    line-height: 1.6;
}

.article-content {
    font-size: 1.1rem;
    line-height: 1.8;
    margin: 2rem 0;
}

.article-content p {
    margin-bottom: 1.5rem;
}

.article-content p:last-child {
    margin-bottom: 0;
}

.article-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    padding-top: 1rem;
    border-top: 1px solid #e9ecef;
    margin-top: auto;
}

.original-link, .back-link {
    color: #667eea;
    text-decoration: none;
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    transition: background 0.2s;
}

.original-link:hover, .back-link:hover {
    background: #f8f9ff;
}

/* Furigana Styles */
ruby {
    ruby-position: over;
    display: ruby;
    ruby-align: center;
}

rt {
    display: ruby-text;
    font-size: 0.6em;
    color: #666;
    font-weight: normal;
    line-height: 1;
    text-align: center;
}

/* Level-based furigana control */
ruby.hide-furigana rt {
    display: none;
}

ruby.show-furigana rt {
    display: ruby-text;
}

/* Kanji By Level List */
.kanji-by-level-list {
    margin: 1rem 0;
}

.kanji-by-level-list summary {
    cursor: pointer;
    font-weight: 500;
    color: #667eea;
    margin-bottom: 0.5rem;
}

.unknown-kanji-list {
    margin: 1rem 0;
}

.unknown-kanji-list summary {
    cursor: pointer;
    font-weight: 500;
    color: #667eea;
    margin-bottom: 0.5rem;
}

.kanji-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.kanji-item {
    background: #fff3cd;
    color: #856404;
    padding: 0.5rem;
    text-align: center;
    border-radius: 6px;
    font-weight: 500;
    font-size: 1.2rem;
}

/* Full Article */
.article-full {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}

.article-full .article-title {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #333;
}

/* Footer */
.site-footer {
    background: #343a40;
    color: white;
    text-align: center;
    padding: 2rem 0;
    margin-top: 3rem;
}

.site-footer a {
    color: #adb5bd;
}

.no-articles {
    text-align: center;
    color: #666;
    font-size: 1.1rem;
    padding: 3rem;
}

/* Responsive Design */
@media (max-width: 768px) {
    .container {
        padding: 0 15px;
    }

    .header-container {
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
    }

    .header-left {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.25rem;
    }

    .controls {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.75rem;
        width: 100%;
    }

    .level-slider {
        width: 100%;
        max-width: 300px;
    }

    .site-header h1 {
        font-size: 1.3rem;
    }

    .site-description {
        font-size: 0.8rem;
    }

    .articles-grid {
        # grid-template-columns: 1fr;
        gap: 1rem;
    }

    .article-card {
        padding: 1rem;
        width: 100%;
        max-width: 100%;
    }

    .article-footer {
        flex-direction: column;
        gap: 1rem;
        align-items: stretch;
    }

    .article-full {
        padding: 1rem;
    }

    .article-full .article-title {
        font-size: 1.5rem;
    }

    .article-image img {
        height: 150px;
    }

    .article-image-full img {
        border-radius: 8px;
    }
}"""

        css_path = self.output_dir / "style.css"
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css_content)

        print(f"Generated CSS: {css_path}")

    def generate_javascript(self):
        """Generate JavaScript file"""
        js_content = """// Level-based furigana control
document.addEventListener('DOMContentLoaded', function() {
    const levelSlider = document.getElementById('level-slider');
    const levelValue = document.getElementById('level-value');
    const showAllToggle = document.getElementById('show-all-toggle');

    // Load saved level preference (default: 10)
    const savedLevel = localStorage.getItem('waniKaniLevel') || '10';
    levelSlider.value = savedLevel;
    levelValue.textContent = savedLevel;

    // Load show all toggle preference
    const showAll = localStorage.getItem('showAllFurigana') === 'true';
    showAllToggle.checked = showAll;

    // Apply furigana display based on current settings
    updateFuriganaDisplay();

    // Level slider change
    levelSlider.addEventListener('input', function() {
        levelValue.textContent = this.value;
        localStorage.setItem('waniKaniLevel', this.value);
        updateFuriganaDisplay();
    });

    // Show all toggle change
    showAllToggle.addEventListener('change', function() {
        localStorage.setItem('showAllFurigana', this.checked);
        updateFuriganaDisplay();
    });

    function updateFuriganaDisplay() {
        const level = parseInt(levelSlider.value);
        const showAll = showAllToggle.checked;

        // Get all ruby elements with data-level attribute
        const rubyElements = document.querySelectorAll('ruby[data-level]');

        rubyElements.forEach(ruby => {
            const kanjiLevel = ruby.getAttribute('data-level');

            // Show all furigana if toggle is on
            if (showAll) {
                ruby.classList.add('show-furigana');
                ruby.classList.remove('hide-furigana');
                return;
            }

            // Show furigana for kanji above user's level
            if (kanjiLevel === 'unknown' || parseInt(kanjiLevel) > level) {
                ruby.classList.add('show-furigana');
                ruby.classList.remove('hide-furigana');
            } else {
                ruby.classList.add('hide-furigana');
                ruby.classList.remove('show-furigana');
            }
        });
    }

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});"""

        js_path = self.output_dir / "script.js"
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js_content)

        print(f"Generated JavaScript: {js_path}")

    def generate_site(self, articles_file="data/processed_articles.json"):
        """Generate the complete static site"""
        print("Loading articles...")
        articles = self._load_articles(articles_file)

        if not articles:
            print("No articles found. Generating empty site.")

        print("Generating index page...")
        self.generate_index_page(articles)

        print("Generating individual article pages...")
        for article in articles:
            slug = self.generate_article_page(article)
            print(f"  Generated: {slug}.html")

        print("Generating CSS...")
        self.generate_css()

        print("Generating JavaScript...")
        self.generate_javascript()

        print(f"Site generated successfully in {self.output_dir}")
        print(f"Total articles: {len(articles)}")


if __name__ == "__main__":
    generator = SiteGenerator()
    generator.generate_site()
