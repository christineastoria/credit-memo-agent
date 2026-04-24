"""
Seed script for the internal SQLite database.

Creates two tables:
  - deals: Historical deal records (leveraged loans, HY bonds, direct lending, CLOs)
  - portfolio: Current portfolio holdings and exposure

Run this once before using the agent:
    python data/seed_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "deals.db")


def create_tables(cursor):
    """Create the deals and portfolio tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            borrower TEXT NOT NULL,
            deal_type TEXT NOT NULL,          -- 'leveraged_loan', 'high_yield', 'direct_lending', 'clo'
            deal_date TEXT NOT NULL,
            amount_mm REAL NOT NULL,          -- deal size in millions
            spread_bps INTEGER NOT NULL,      -- spread in basis points
            leverage_at_close REAL NOT NULL,  -- total leverage (Debt/EBITDA) at close
            sector TEXT NOT NULL,
            rating TEXT,                      -- S&P/Moody's equivalent
            outcome TEXT                      -- 'performing', 'watchlist', 'default', 'repaid'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            borrower TEXT NOT NULL,
            instrument TEXT NOT NULL,
            par_amount_mm REAL NOT NULL,      -- current par value in millions
            current_price REAL NOT NULL,      -- price as % of par
            yield_pct REAL NOT NULL,          -- current yield %
            sector TEXT NOT NULL,
            maturity_date TEXT NOT NULL,
            risk_rating INTEGER NOT NULL      -- internal 1-5 scale (1=best)
        )
    """)


def seed_deals(cursor):
    """Insert dummy historical deal data."""
    deals = [
        # Healthcare sector deals
        ("Summit Healthcare Partners", "leveraged_loan", "2023-03-15", 450.0, 525, 5.2, "Healthcare", "B+", "performing"),
        ("Summit Healthcare Partners", "high_yield", "2021-06-20", 300.0, 625, 4.8, "Healthcare", "B", "performing"),
        ("MedCore Solutions", "direct_lending", "2024-01-10", 125.0, 700, 5.8, "Healthcare", "B", "watchlist"),
        ("Apex Medical Group", "leveraged_loan", "2022-09-05", 600.0, 475, 4.5, "Healthcare", "BB-", "performing"),
        ("Pinnacle Health Systems", "high_yield", "2020-11-12", 350.0, 550, 5.0, "Healthcare", "B+", "repaid"),

        # Technology sector deals
        ("GlobalTech Industries", "leveraged_loan", "2023-07-22", 800.0, 400, 4.2, "Technology", "BB-", "performing"),
        ("GlobalTech Industries", "clo", "2022-02-14", 500.0, 350, 3.8, "Technology", "BB", "performing"),
        ("NexGen Software Corp", "direct_lending", "2024-03-01", 200.0, 650, 6.1, "Technology", "B", "performing"),
        ("CyberShield Solutions", "leveraged_loan", "2023-11-08", 325.0, 500, 5.5, "Technology", "B+", "watchlist"),
        ("DataStream Analytics", "high_yield", "2021-04-30", 275.0, 575, 4.9, "Technology", "B+", "performing"),

        # Industrials sector deals
        ("Acme Corp", "leveraged_loan", "2022-05-18", 550.0, 450, 4.7, "Industrials", "BB-", "performing"),
        ("Acme Corp", "high_yield", "2020-08-25", 400.0, 500, 5.1, "Industrials", "B+", "performing"),
        ("Titan Manufacturing", "leveraged_loan", "2023-01-30", 700.0, 425, 4.3, "Industrials", "BB", "performing"),
        ("Sterling Industrial", "direct_lending", "2024-02-15", 150.0, 725, 6.5, "Industrials", "B-", "default"),
        ("Ironworks Capital", "clo", "2022-10-20", 450.0, 375, 4.0, "Industrials", "BB-", "performing"),

        # Consumer sector deals
        ("BrightStar Retail", "leveraged_loan", "2023-06-10", 380.0, 550, 5.3, "Consumer", "B+", "watchlist"),
        ("Evergreen Consumer Brands", "high_yield", "2021-12-05", 500.0, 475, 4.6, "Consumer", "BB-", "performing"),
        ("Pacific Coast Foods", "direct_lending", "2024-04-01", 175.0, 675, 5.9, "Consumer", "B", "performing"),

        # Energy sector deals
        ("Meridian Energy Partners", "leveraged_loan", "2023-09-14", 650.0, 500, 5.0, "Energy", "B+", "performing"),
        ("Sunbelt Resources", "high_yield", "2022-03-28", 400.0, 600, 5.7, "Energy", "B", "watchlist"),
    ]

    cursor.executemany("""
        INSERT INTO deals (borrower, deal_type, deal_date, amount_mm, spread_bps,
                          leverage_at_close, sector, rating, outcome)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, deals)


def seed_portfolio(cursor):
    """Insert dummy current portfolio holdings."""
    holdings = [
        ("Summit Healthcare Partners", "Term Loan B", 45.0, 98.5, 7.2, "Healthcare", "2028-03-15", 2),
        ("GlobalTech Industries", "Senior Secured TL", 80.0, 99.0, 6.8, "Technology", "2029-07-22", 2),
        ("Acme Corp", "Term Loan B", 55.0, 97.0, 7.5, "Industrials", "2028-05-18", 2),
        ("Acme Corp", "8.5% Senior Notes", 40.0, 95.5, 9.1, "Industrials", "2027-08-25", 3),
        ("Apex Medical Group", "Term Loan B", 60.0, 99.5, 6.5, "Healthcare", "2029-09-05", 1),
        ("Evergreen Consumer Brands", "7.75% Senior Notes", 50.0, 96.0, 8.3, "Consumer", "2028-12-05", 2),
        ("Meridian Energy Partners", "Term Loan B", 65.0, 98.0, 7.0, "Energy", "2029-09-14", 2),
        ("CyberShield Solutions", "Term Loan B", 32.5, 94.0, 8.5, "Technology", "2029-11-08", 3),
        ("BrightStar Retail", "Term Loan B", 38.0, 92.0, 9.0, "Consumer", "2029-06-10", 4),
        ("MedCore Solutions", "Unitranche", 12.5, 90.0, 10.2, "Healthcare", "2029-01-10", 4),
    ]

    cursor.executemany("""
        INSERT INTO portfolio (borrower, instrument, par_amount_mm, current_price,
                              yield_pct, sector, maturity_date, risk_rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, holdings)


def main():
    # Remove existing DB to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_tables(cursor)
    seed_deals(cursor)
    seed_portfolio(cursor)

    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(*) FROM deals")
    print(f"Seeded {cursor.fetchone()[0]} deals")
    cursor.execute("SELECT COUNT(*) FROM portfolio")
    print(f"Seeded {cursor.fetchone()[0]} portfolio holdings")

    conn.close()
    print(f"Database created at {DB_PATH}")


if __name__ == "__main__":
    main()
