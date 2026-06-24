def settle_auction(listing_id):
    """End auction, transfer NFT and settle payment"""
    try:
        conn = psycopg2.connect(PG_LEDGER)
        cur = conn.cursor()

        cur.execute("""
            SELECT token_id, seller_wallet, status, auction_end FROM nft_listings WHERE id = %s
        """, (listing_id,))
        listing = cur.fetchone()
        if not listing:
            return False, "Listing not found"

        token_id, seller_wallet, status, auction_end = listing
        if status != 'active':
            return False, f"Listing already {status}"
        if auction_end and auction_end > datetime.now():
            return False, f"Auction still running until {auction_end}"

        cur.execute("""
            SELECT bidder_wallet, bid_amount FROM nft_bids
            WHERE listing_id = %s
            ORDER BY bid_amount DESC LIMIT 1
        """, (listing_id,))
        bid = cur.fetchone()
        if not bid:
            cur.execute("UPDATE nft_listings SET status = 'no_bids' WHERE id = %s", (listing_id,))
            conn.commit()
            return True, "No bids received"

        winner_wallet, winning_bid = bid
        system_fee = winning_bid * 0.05
        seller_amount = winning_bid * 0.95

        ok1, msg1 = transfer_tokens(winner_wallet, seller_wallet, seller_amount, "NFT_SALE")
        if not ok1:
            return False, f"Seller transfer failed: {msg1}"

        system_wallet = "0b608cb6-6745-4b75-bb9d-fa60e8a1b051"
        ok2, msg2 = transfer_tokens(winner_wallet, system_wallet, system_fee, "MARKETPLACE_FEE")
        if not ok2:
            return False, f"Fee transfer failed (seller already paid: {msg1}): {msg2}"

        cur.execute("""
            UPDATE nft_registry
            SET owner_account_id = %s, sale_status = 'sold', sold_at = NOW()
            WHERE token_id = %s
        """, (winner_wallet, token_id))
        cur.execute("UPDATE nft_listings SET status = 'sold' WHERE id = %s", (listing_id,))

        conn.commit()
        cur.close()
        conn.close()
        return True, f"NFT #{token_id} sold for {winning_bid} OMG"
    except Exception as e:
        return False, str(e)
