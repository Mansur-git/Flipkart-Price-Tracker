"""
config.py — Edit this file to set your products, email, and schedule.
"""

# ── Products to track ──────────────────────────────────────────────────────────
# Add as many products as you like.
# target_price: alert fires when price drops TO or BELOW this value (in ₹).

PRODUCTS = [
    {
        "name": "boAt Rockerz 450 Bluetooth Headphones",
        "url": "https://www.flipkart.com/boat-rockerz-450-bluetooth-headphone/p/itmfbfhfzkhfnzjt",
        "target_price": 1200,
    },
    {
        "name": "Logitech M235 Wireless Mouse",
        "url": "https://www.flipkart.com/logitech-m235-wireless-optical-mouse/p/itme9gyhg6gdzctb",
        "target_price": 900,
    },
    # Add more products here:
    # {
    #     "name": "Your Product Name",
    #     "url":  "https://www.flipkart.com/...",
    #     "target_price": 5000,
    # },
]

# ── Email alerts ───────────────────────────────────────────────────────────────
# Uses Gmail. You need a Google "App Password" (not your regular password).
# How to get one: https://myaccount.google.com/apppasswords
# Set enabled: False to disable email and just log to console.

EMAIL_CONFIG = {
    "enabled": False,                         # ← Set True to enable
    "sender": "your.email@gmail.com",         # ← Your Gmail address
    "receiver": "your.email@gmail.com",       # ← Where to send alerts (can be same)
    "app_password": "xxxx xxxx xxxx xxxx",   # ← 16-char Google App Password
}

# ── Schedule ───────────────────────────────────────────────────────────────────
CHECK_INTERVAL_HOURS = 6    # How often to check prices (in hours)

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "prices.db"       # SQLite file — created automatically on first run
