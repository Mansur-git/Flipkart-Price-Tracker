"""
history.py — View price history stored in the SQLite database.
Usage:
    python history.py              # Show all products + latest prices
    python history.py --product 1  # Show full history for product ID 1
"""

import sqlite3
import argparse
from config import DB_PATH


def all_products():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.target_price,
            ph.price AS latest_price,
            ph.scraped_at
        FROM products p
        LEFT JOIN price_history ph ON ph.id = (
            SELECT id FROM price_history
            WHERE product_id = p.id
            ORDER BY scraped_at DESC LIMIT 1
        )
        ORDER BY p.id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No products tracked yet. Run tracker.py first.")
        return

    print(f"\n{'ID':<5} {'Product':<40} {'Target ₹':>10} {'Latest ₹':>10} {'Checked At':<22}")
    print("─" * 92)
    for row in rows:
        pid, name, target, latest, checked = row
        latest_str = f"₹{latest:,.0f}" if latest else "N/A"
        target_str = f"₹{target:,.0f}"
        alert = " ✓ DEAL" if latest and latest <= target else ""
        print(f"{pid:<5} {name[:38]:<40} {target_str:>10} {latest_str:>10} {str(checked)[:19]:<22}{alert}")
    print()


def product_history(product_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT name, target_price FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()
    if not product:
        print(f"No product found with ID {product_id}.")
        conn.close()
        return

    name, target = product
    print(f"\nHistory for: {name}")
    print(f"Target price: ₹{target:,.0f}\n")

    cur.execute("""
        SELECT price, scraped_at FROM price_history
        WHERE product_id = ?
        ORDER BY scraped_at DESC
    """, (product_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No price history yet.")
        return

    print(f"{'#':<5} {'Price':>12} {'Scraped At':<22} {'Status'}")
    print("─" * 60)
    for i, (price, ts) in enumerate(rows, 1):
        price_str = f"₹{price:,.0f}" if price else "N/A"
        status = "✓ Below target" if price and price <= target else "✗ Above target"
        print(f"{i:<5} {price_str:>12} {str(ts)[:19]:<22} {status}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View price history")
    parser.add_argument("--product", type=int, help="Product ID to inspect")
    args = parser.parse_args()

    if args.product:
        product_history(args.product)
    else:
        all_products()
