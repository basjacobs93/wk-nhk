import json
import base64
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class NHKAuthenticator:
    def __init__(self):
        pass

    def decode_jwt_payload(self, token):
        """Decode JWT payload to check expiration"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            payload = parts[1]
            padding = "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding)
            return json.loads(decoded)
        except Exception as e:
            print(f"Failed to decode JWT: {e}")
            return None

    def get_fresh_token(self, headless=True):
        """
        Accept NHK terms and extract the z_at token.
        NHK automatically generates tokens when users accept their terms of service.
        No login credentials required.

        Args:
            headless: Run browser in headless mode (default: True for CI/CD)
        """
        print("Starting automated terms acceptance...")

        with sync_playwright() as p:
            # Use Firefox in headless mode as it's harder to detect
            # Chromium headless is easily detected by NHK
            if headless:
                browser = p.firefox.launch(
                    headless=True,
                    firefox_user_prefs={
                        "dom.webdriver.enabled": False,
                        "useAutomationExtension": False,
                        "general.useragent.override": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
                    }
                )
            else:
                browser = p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )

            # Create context with realistic settings
            if headless:
                # Firefox headless - minimal config needed
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    locale="ja-JP",
                    timezone_id="Asia/Tokyo",
                )
            else:
                # Chromium - need stealth settings
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="ja-JP",
                    timezone_id="Asia/Tokyo",
                )

                # Stealth script for Chromium
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
            page = context.new_page()

            try:
                print("Navigating to NHK News Easy...")
                page.goto("https://news.web.nhk/news/easy/", timeout=30000)

                # Wait for page to load
                page.wait_for_load_state("domcontentloaded")

                print("Looking for 'For Users Abroad' dialog...")

                # Wait a bit for JavaScript to render the dialog
                page.wait_for_timeout(2000)

                # First, handle the "For Users Abroad" dialog
                abroad_button_selectors = [
                    "button:has-text('確認しました')",
                    "button:has-text('I understand')",
                    "text=確認しました",
                    "text=I understand"
                ]

                abroad_button_clicked = False
                for selector in abroad_button_selectors:
                    try:
                        button = page.locator(selector).first
                        if button.is_visible(timeout=5000):
                            print(f"Found 'For Users Abroad' button: {selector}")
                            # Try clicking and wait for the button to disappear
                            button.click()
                            print("✓ Clicked 'I understand' button")

                            # Wait for the button to disappear (indicating dialog closed)
                            try:
                                button.wait_for(state="hidden", timeout=10000)
                                print("✓ Dialog dismissed successfully")
                                abroad_button_clicked = True
                            except:
                                print("⚠️  Button still visible after click, trying force click")
                                # Try force click if regular click didn't work
                                button.click(force=True)
                                page.wait_for_timeout(2000)
                                abroad_button_clicked = True

                            page.wait_for_load_state("networkidle", timeout=30000)
                            break
                    except Exception as e:
                        print(f"Error with selector {selector}: {e}")
                        continue

                # Now look for any additional terms acceptance dialogs
                print("Looking for additional terms acceptance dialogs...")

                # Look for terms acceptance checkbox
                checkbox_selectors = [
                    "input[type='checkbox']",
                    "[type='checkbox']",
                    "label:has(input[type='checkbox'])"
                ]

                checkbox_found = False
                for selector in checkbox_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            print(f"Found checkbox: {selector}")
                            page.check(selector)
                            checkbox_found = True
                            print("✓ Checked terms acceptance box")
                            break
                    except Exception as e:
                        continue

                # Look for additional submit/accept buttons
                button_selectors = [
                    "button:has-text('OK')",
                    "button:has-text('同意')",
                    "button:has-text('次へ')",
                    "button[type='submit']",
                    "button.submit",
                    ".button--primary"
                ]

                additional_button_clicked = False
                for selector in button_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            print(f"Clicking additional button: {selector}")
                            page.click(selector)
                            additional_button_clicked = True
                            break
                    except:
                        continue

                if additional_button_clicked or checkbox_found:
                    print("Waiting for final token generation...")
                    page.wait_for_load_state("networkidle", timeout=30000)
                elif abroad_button_clicked:
                    print("'I understand' button clicked, waiting for token...")
                else:
                    print("No dialogs found, token may already be set...")

                # Additional wait to ensure cookies are set
                print("Waiting additional time for cookies to be set...")
                page.wait_for_timeout(3000)

                # Extract cookies
                current_url = page.url

                # Try multiple URLs that might have the cookie
                urls_to_try = [
                    current_url,
                    "https://news.web.nhk",
                    "https://news.web.nhk/",
                    "https://news.web.nhk/news/easy/",
                ]

                cookies = []
                for url in urls_to_try:
                    try:
                        url_cookies = context.cookies(urls=[url])
                        if url_cookies:
                            cookies.extend(url_cookies)
                    except Exception:
                        pass

                # Deduplicate cookies by name
                seen_names = set()
                unique_cookies = []
                for cookie in cookies:
                    if cookie["name"] not in seen_names:
                        seen_names.add(cookie["name"])
                        unique_cookies.append(cookie)
                cookies = unique_cookies

                # Find the z_at token
                z_at_token = None
                for cookie in cookies:
                    if cookie["name"] == "z_at":
                        z_at_token = cookie["value"]
                        break

                if not z_at_token:
                    cookie_names = [c["name"] for c in cookies]
                    raise Exception(f"Failed to extract z_at token. Found cookies: {cookie_names}")

                # Decode and verify token
                payload = self.decode_jwt_payload(z_at_token)
                if payload:
                    exp = payload.get("exp")
                    if exp:
                        from datetime import datetime
                        exp_date = datetime.fromtimestamp(exp)
                        print(f"Token obtained, expires: {exp_date}")

                print("✅ Successfully obtained authentication token")
                return z_at_token

            except Exception as e:
                print(f"❌ Token extraction failed: {e}")
                # Take screenshot for debugging
                try:
                    page.screenshot(path="/tmp/nhk_auth_error.png")
                    print("Screenshot saved to /tmp/nhk_auth_error.png")
                    # Also save page HTML for debugging
                    with open("/tmp/nhk_page.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                    print("Page HTML saved to /tmp/nhk_page.html")
                except:
                    pass
                raise

            finally:
                browser.close()


def get_nhk_token(headless=True):
    """Convenience function to get a fresh NHK token"""
    authenticator = NHKAuthenticator()
    return authenticator.get_fresh_token(headless=headless)


if __name__ == "__main__":
    # Test terms acceptance and token extraction
    token = get_nhk_token()
    print(f"\nToken obtained: {token[:50]}...")
