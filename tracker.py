"""
Price Tracker — Flipkart
Uses Playwright to scrape product prices, stores history in SQLite,
and sends an email alert when the price drops below your target.
"""

import asyncio
import sqlite3
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from config import PRODUCTS, EMAIL_CONFIG, DB_PATH, CHECK_INTERVAL_HOURS

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Database ───────────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            url         TEXT NOT NULL UNIQUE,
            target_price REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL,
            price       REAL,
            scraped_at  TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    conn.commit()
    conn.close()
    log.info("Database ready.")


def upsert_product(name: str, url: str, target_price: float) -> int:
    """Insert or update a product, return its id."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (name, url, target_price)
        VALUES (?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            name=excluded.name,
            target_price=excluded.target_price
    """, (name, url, target_price))
    conn.commit()
    cur.execute("SELECT id FROM products WHERE url = ?", (url,))
    product_id = cur.fetchone()[0]
    conn.close()
    return product_id


def save_price(product_id: int, price: float | None):
    """Record a price snapshot."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO price_history (product_id, price, scraped_at) VALUES (?, ?, ?)",
        (product_id, price, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_price_history(product_id: int, limit: int = 10) -> list[dict]:
    """Fetch recent price history for a product."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT price, scraped_at FROM price_history
        WHERE product_id = ?
        ORDER BY scraped_at DESC LIMIT ?
    """, (product_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [{"price": r[0], "scraped_at": r[1]} for r in rows]


# ── Scraping ───────────────────────────────────────────────────────────────────

def parse_price(raw: str) -> float | None:
    """Convert '₹1,23,456' → 123456.0"""
    try:
        cleaned = raw.replace("₹", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


async def scrape_flipkart(url: str, browser) -> dict:
    """
    Open a Flipkart product page and extract name + price.
    Returns dict with keys: name, price (float or None), raw_price (str)
    """
    page = await browser.new_page()
    result = {"name": "Unknown", "price": None, "raw_price": "N/A"}

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)  # let JS settle

        # ── Product name ──────────────────────────────────────────────────────
        # Flipkart uses <span class="B_NuCI"> for product title
        name_selectors = [
            "span.B_NuCI",
            "h1.yhB1nd span",
            "h1 span",
        ]
        for sel in name_selectors:
            el = await page.query_selector(sel)
            if el:
                result["name"] = (await el.inner_text()).strip()
                break

        # ── Price ─────────────────────────────────────────────────────────────
        # Flipkart uses <div class="_30jeq3 _16Jk6d"> for the final price
        price_selectors = [
            "div._30jeq3._16Jk6d",
            "div._30jeq3",
            "._16Jk6d",
            "[class*='_30jeq3']",
        ]
        for sel in price_selectors:
            el = await page.query_selector(sel)
            if el:
                raw = (await el.inner_text()).strip()
                result["raw_price"] = raw
                result["price"] = parse_price(raw)
                break

    except PlaywrightTimeout:
        log.error(f"Timed out loading: {url}")
    except Exception as e:
        log.error(f"Error scraping {url}: {e}")
    finally:
        await page.close()

    return result


# ── Email Alerts ───────────────────────────────────────────────────────────────

def send_alert(product_name: str, current_price: float, target_price: float, url: str):
    """Send an email alert when price drops to/below target."""
    if not EMAIL_CONFIG.get("enabled"):
        log.info("Email alerts disabled. Skipping.")
        return

    subject = f"Price Drop Alert: {product_name}"
    body = f"""
Good news! A product you're tracking has dropped to your target price.

Product  : {product_name}
Current  : ₹{current_price:,.0f}
Target   : ₹{target_price:,.0f}
Savings  : ₹{target_price - current_price:,.0f} below your target

View on Flipkart:
{url}

— Price Tracker Bot
    """.strip()

    msg = MIMEMultipart()
    msg["From"] = EMAIL_CONFIG["sender"]
    msg["To"] = EMAIL_CONFIG["receiver"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["app_password"])
            server.sendmail(EMAIL_CONFIG["sender"], EMAIL_CONFIG["receiver"], msg.as_string())
        log.info(f"Alert email sent for: {product_name}")
    except Exception as e:
        log.error(f"Failed to send email: {e}")


# ── Main Loop ──────────────────────────────────────────────────────────────────

async def run_check():
    """Single check cycle — scrape all products and handle alerts."""
    log.info("=" * 55)
    log.info(f"Check started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for product_cfg in PRODUCTS:
            name  = product_cfg["name"]
            url   = product_cfg["url"]
            target = product_cfg["target_price"]

            log.info(f"Checking: {name}")
            product_id = upsert_product(name, url, target)

            data = await scrape_flipkart(url, browser)
            price = data["price"]
            save_price(product_id, price)

            if price is None:
                log.warning(f"  Could not parse price for {name}. Raw: {data['raw_price']}")
                continue

            log.info(f"  Current price : ₹{price:,.0f}")
            log.info(f"  Target price  : ₹{target:,.0f}")

            if price <= target:
                log.info(f"  ✓ PRICE DROP! Sending alert...")
                send_alert(name, price, target, url)
            else:
                diff = price - target
                log.info(f"  ✗ ₹{diff:,.0f} above target. No alert.")

            # Brief pause between products
            await asyncio.sleep(2)

        await browser.close()

    log.info("Check complete.\n")


async def main():
    """Run the tracker in a loop."""
    init_db()

    while True:
        await run_check()

        interval_secs = CHECK_INTERVAL_HOURS * 3600
        log.info(f"Next check in {CHECK_INTERVAL_HOURS} hour(s). Sleeping...")
        await asyncio.sleep(interval_secs)


if __name__ == "__main__":
    asyncio.run(main())
