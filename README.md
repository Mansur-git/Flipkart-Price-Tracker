# Flipkart Price Tracker

Tracks product prices on Flipkart using **Playwright**, stores history in **SQLite**, and fires **email alerts** when prices drop to your target.

---

## Project structure

```
price_tracker/
├── tracker.py       ← Main scraper + alert loop
├── config.py        ← Your products, email, schedule
├── history.py       ← CLI to view price history
├── requirements.txt
└── prices.db        ← Auto-created on first run
```

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright browsers

```bash
playwright install chromium
```

### 3. Configure your products

Open `config.py` and edit the `PRODUCTS` list:

```python
PRODUCTS = [
    {
        "name": "boAt Rockerz 450 Headphones",
        "url": "https://www.flipkart.com/...",   # paste the product URL
        "target_price": 1200,                     # alert when price ≤ this
    },
]
```

### 4. (Optional) Enable email alerts

To receive email alerts, you need a **Gmail App Password**:
1. Go to https://myaccount.google.com/apppasswords
2. Create an app password for "Mail"
3. Paste it into `config.py`:

```python
EMAIL_CONFIG = {
    "enabled": True,
    "sender": "you@gmail.com",
    "receiver": "you@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
}
```

---

## Running

### Start the tracker

```bash
python tracker.py
```

It checks all products immediately, then waits `CHECK_INTERVAL_HOURS` (default: 6) before repeating.

### View price history

```bash
python history.py              # all products + latest price
python history.py --product 1  # full history for product ID 1
```

---

## How it works

```
tracker.py
│
├── init_db()            — creates SQLite tables on first run
├── upsert_product()     — inserts/updates product config
│
├── [Playwright loop]
│   └── scrape_flipkart()  — headless Chromium loads the page
│       ├── Waits for JS to settle
│       ├── Tries multiple CSS selectors for price + name
│       └── Returns parsed float price
│
├── save_price()         — writes snapshot to price_history table
│
└── send_alert()         — emails you if price ≤ target (via Gmail SMTP)
```

---

## Scheduling (run 24/7)

Instead of keeping a terminal open, you can schedule it:

**Linux/macOS — cron:**
```bash
# Run every 6 hours
0 */6 * * * /usr/bin/python3 /path/to/tracker.py >> /path/to/tracker.log 2>&1
```

**Windows — Task Scheduler:**
Create a basic task that runs `python tracker.py` on a schedule.

---

## Notes

- Playwright renders JavaScript, so it works on dynamic sites like Flipkart.
- If Flipkart changes its CSS class names, update the `price_selectors` list in `scrape_flipkart()`.
- This project is for **educational purposes only**. Always respect a website's Terms of Service.
