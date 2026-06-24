
def check_liquidity(conn, wallet_id, amount):
    with conn.cursor() as cur:

        # 1. GLOBAL LIQUIDITY CHECK
        cur.execute("""
            SELECT available_liquidity
            FROM treasury_state
            LIMIT 1;
        """)

        treasury = cur.fetchone()
        if not treasury:
            return {"approved": False, "reason": "NO_TREASURY"}

        available = treasury[0]

        if float(amount) > float(available):
            return {"approved": False, "reason": "INSUFFICIENT_TREASURY_LIQUIDITY"}

        # 2. WALLET LIMIT CHECK
        cur.execute("""
            SELECT max_exposure, current_exposure
            FROM treasury_limits
            WHERE wallet_id = %s;
        """, (wallet_id,))

        limit = cur.fetchone()
        if not limit:
            return {"approved": False, "reason": "NO_WALLET_LIMIT"}

        max_exposure, current_exposure = limit

        if float(current_exposure) + float(amount) > float(max_exposure):
            return {"approved": False, "reason": "EXPOSURE_LIMIT_EXCEEDED"}

        # 3. RESERVE LIQUIDITY
        cur.execute("""
            UPDATE treasury_state
            SET reserved_liquidity = reserved_liquidity + %s,
                available_liquidity = available_liquidity - %s,
                updated_at = now()
        """, (amount, amount))

        # 4. UPDATE WALLET EXPOSURE
        cur.execute("""
            UPDATE treasury_limits
            SET current_exposure = current_exposure + %s,
                updated_at = now()
            WHERE wallet_id = %s;
        """, (amount, wallet_id))

        conn.commit()

        return {
            "approved": True,
            "reserved": float(amount)
        }

def release_liquidity(conn, wallet_id, amount):
    with conn.cursor() as cur:

        cur.execute("""
            UPDATE treasury_state
            SET reserved_liquidity = reserved_liquidity - %s,
                available_liquidity = available_liquidity + %s,
                updated_at = now()
        """, (amount, amount))

        cur.execute("""
            UPDATE treasury_limits
            SET current_exposure = current_exposure - %s,
                updated_at = now()
            WHERE wallet_id = %s;
        """, (amount, wallet_id))

        conn.commit()

        return {"released": amount}
