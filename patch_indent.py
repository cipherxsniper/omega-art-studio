path = "/data/data/com.termux/files/home/omega_marketplace.py"
with open(path) as f:
    lines = f.readlines()

# Find the line index (0-based) where the broken block starts
start = None
for i, line in enumerate(lines):
    if line.startswith("if '--test-bid' in sys.argv:"):
        start = i
        break

if start is None:
    raise SystemExit("PATCH FAILED: start marker not found")

# Everything before 'start' stays as-is
head = lines[:start]

new_tail = '''    if '--test-bid' in sys.argv:
        print("[*] Testing bid on active auction...\\n")

        wallet2 = "a7889956-ca14-432a-9cb7-7dc17530b7d9"

        auctions = get_active_auctions()
        if auctions:
            listing = auctions[0]
            listing_id = listing['listing_id']
            print(f"Found auction #{listing_id}: NFT #{listing['token_id']} @ {listing['starting_price']} OMG\\n")

            print(f"Wallet 2 before bid: {get_wallet_balance(wallet2)} OMG")

            print(f"\\n[*] Placing bid of 600 OMG...")
            success, msg = place_bid(listing_id, wallet2, 600.0)
            print(f"    {msg}")

            print(f"\\nWallet 2 after bid: {get_wallet_balance(wallet2)} OMG")

            print(f"\\n[*] Updated auction:")
            for auction in get_active_auctions():
                if auction['listing_id'] == listing_id:
                    print(f"    Listing #{auction['listing_id']}: NFT #{auction['token_id']} | Bids: {auction['bid_count']} | Highest: {auction['highest_bid']} OMG")
        else:
            print("No active auctions found")

    if '--settle-auction' in sys.argv:
        idx = sys.argv.index('--settle-auction')
        listing_id = int(sys.argv[idx + 1])
        print(f"[*] Settling auction #{listing_id}...\\n")
        success, msg = settle_auction(listing_id)
        print(f"    {msg}")
'''

with open(path, "w") as f:
    f.writelines(head)
    f.write(new_tail)

print("PATCH APPLIED")
