# WK・NHK

A public website that displays [NHK News Web Easy](https://news.web.nhk/news/easy/) articles with adjustable furigana based on WaniKani levels. No API tokens or accounts required!

**Live Site**: https://www.wk-nhk.com/

## Features

- **WaniKani Level Slider**: Adjust furigana display from level 0-60 in real-time
- **Smart Furigana**: Shows furigana only for kanji above your selected level
- **Automated Daily Updates**: GitHub Actions scrapes new articles daily at 9 PM JST
- **No Setup Required**: Public site works for everyone without forking or configuration
- **Mobile Responsive**: Clean, compact design that works on all devices
- **Clickable Article Cards**: Click anywhere on a card to read the full article

## How to Use

1. Visit the site
2. Adjust the "WaniKani Level" slider to match your current level (0-60)
3. Read articles with furigana shown only for kanji you haven't learned yet
4. Toggle "Show all" to temporarily display all furigana

Your level preference is saved in your browser for future visits.

## How It Works

1. **WaniKani Data**: Uses static kanji data from [kanji-data](https://github.com/davidluzgouveia/kanji-data) (community-maintained WaniKani level progressions)
2. **NHK Scraping**: Automatically scrapes latest articles from NHK News Web Easy
3. **Level-based Furigana**: Each kanji is tagged with its WaniKani level (data-level attribute)
4. **Dynamic Display**: JavaScript shows/hides furigana based on your slider position
5. **Static Site**: Generates and deploys to GitHub Pages daily

## Local Development

```bash
# Install dependencies
uv sync
uv run playwright install chromium

# Run the pipeline
uv run python src/main.py

# Open the generated site
open docs/index.html
```

The site will be generated in the `docs/` directory.

## Analytics

The site uses [GoatCounter](https://www.goatcounter.com/) for privacy-friendly visitor tracking. To enable:

1. Sign up at [goatcounter.com](https://www.goatcounter.com/)
2. Add your site code to `config.yml`:
   ```yaml
   site:
     goatcounter_code: "yoursite"  # for yoursite.goatcounter.com
   ```
3. The tracking script will be automatically added to all pages

## Architecture

### Pipeline Flow

```
1. Generate WaniKani level data → docs/wanikani-data.js
2. Scrape NHK articles with furigana
3. Process articles (add data-level attributes to kanji)
4. Generate static HTML/CSS/JS
5. Deploy to GitHub Pages
```

### Key Files

```
├── .github/workflows/scrape-and-deploy.yml  # Daily scraping automation
├── src/
│   ├── main.py                 # Pipeline coordinator
│   ├── auth.py                 # NHK authentication
│   ├── scraper.py              # Article scraping
│   ├── wanikani_levels.py      # WaniKani data processing
│   ├── furigana_processor.py   # Kanji level tagging
│   └── site_generator.py       # HTML/CSS/JS generation
├── data/
│   └── kanji-wanikani.json     # Static WaniKani kanji data
├── docs/                        # Generated static site
├── config.yml                   # Site configuration
└── pyproject.toml               # Python dependencies
```

## Contributing

This is a public learning tool. Contributions welcome!

- **Bug reports**: Open an issue
- **Feature requests**: Open an issue
- **Pull requests**: Please include a description of the changes

## Credits

- Article content: [NHK News Web Easy](https://news.web.nhk/news/easy/)
- WaniKani kanji data: [davidluzgouveia/kanji-data](https://github.com/davidluzgouveia/kanji-data)
- Level system: [WaniKani](https://www.wanikani.com/)

## License

MIT License - see LICENSE file for details.
