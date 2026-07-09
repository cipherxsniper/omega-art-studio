import json

def compute_net_profit(conn):
    cur = conn.cursor()

    # -----------------------
    # TOTAL STRIPE REVENUE
    # -----------------------
    cur.execute("""
        SELECT COALESCE(SUM(json_extract(payload, '$.amount')), 0)
        FROM stripe_event_log
        WHERE event_type = 'checkout.session.completed'
    """)
    revenue = cur.fetchone()[0] or 0

    # -----------------------
    # REFUNDS / FAILURES
    # -----------------------
    cur.execute("""
        SELECT COALESCE(SUM(json_extract(payload, '$.amount')), 0)
        FROM stripe_event_log
        WHERE event_type IN ('charge.refunded', 'payment_intent.payment_failed')
    """)
    losses = cur.fetchone()[0] or 0

    # -----------------------
    # SIMPLE NET PROFIT MODEL
    # -----------------------
    net = revenue - losses

    return {
        "revenue": revenue,
        "losses": losses,
        "net_profit": net
    }


def reconcile_system(conn):
    profit = compute_net_profit(conn)

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            revenue REAL,
            losses REAL,
            net_profit REAL,
            created_at REAL
        )
    """)

    cur.execute("""
        INSERT INTO reconciliation_report (
            revenue, losses, net_profit, created_at
        ) VALUES (?, ?, ?, ?)
    """, (
        profit["revenue"],
        profit["losses"],
        profit["net_profit"],
        __import__("time").time()
    ))

    conn.commit()

    return profit
