#!/usr/bin/env python3

def update_lead_state(conn, email, new_state):
    """
    SINGLE SOURCE CRM STATE MACHINE
    """

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS crm_state (
            email TEXT PRIMARY KEY,
            state TEXT,
            updated_at REAL
        )
    """)

    import time

    cur.execute("""
        INSERT OR REPLACE INTO crm_state (
            email,
            state,
            updated_at
        ) VALUES (?, ?, ?)
    """, (
        email,
        new_state,
        time.time()
    ))

    conn.commit()

    print(f"[CRM] {email} → {new_state}")
