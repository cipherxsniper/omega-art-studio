path = "/data/data/com.termux/files/home/omega_marketplace.py"
with open(path) as f:
    lines = f.readlines()

def show(n1, n2):
    print(f"--- lines {n1}-{n2} ---")
    for i in range(n1-1, n2):
        print(f"{i+1}: {lines[i]!r}")

show(58, 58)
show(66, 68)
show(75, 79)
show(148, 149)
show(154, 154)
show(185, 188)

checks = [
    (lines[57], "def list_nft_for_auction(token_id, seller_wallet, starting_price_omg, days=7):\n"),
    (lines[65], "            SELECT token_id FROM nft_registry \n"),
    (lines[66], "            WHERE token_id = %s AND owner_account_id = %s\n"),
    (lines[67], "        \"\"\", (token_id, seller_wallet))\n"),
    (lines[147], "            SELECT token_id, seller_wallet, status, auction_end FROM nft_listings WHERE id = %s\n"),
    (lines[153], "        token_id, seller_wallet, status, auction_end = listing\n"),
    (lines[186], "            WHERE token_id = %s\n"),
]
for actual, expected in checks:
    assert actual == expected, f"MISMATCH:\n  actual:   {actual!r}\n  expected: {expected!r}"

print("ALL CHECKS PASSED - proceeding with patch")

lines[57] = "def list_nft_for_auction(token_id, seller_wallet, starting_price_omg, collection, days=7):\n"

lines[65:68] = [
    "            SELECT token_id FROM nft_registry\n",
    "            WHERE token_id = %s AND owner_account_id = %s AND collection = %s\n",
    "        \"\"\", (token_id, seller_wallet, collection))\n",
]

assert lines[75] == "            INSERT INTO nft_listings (token_id, seller_wallet, starting_price_omg, auction_end)\n", repr(lines[75])
lines[74:79] = [
    "        cur.execute(\"\"\"\n",
    "            INSERT INTO nft_listings (token_id, seller_wallet, starting_price_omg, auction_end, collection)\n",
    "            VALUES (%s, %s, %s, %s, %s)\n",
    "            RETURNING id\n",
    "        \"\"\", (token_id, seller_wallet, starting_price_omg, auction_end, collection))\n",
]

lines[147] = "            SELECT token_id, seller_wallet, status, auction_end, collection FROM nft_listings WHERE id = %s\n"
lines[153] = "        token_id, seller_wallet, status, auction_end, collection = listing\n"

lines[184:188] = [
    "        cur.execute(\"\"\"\n",
    "            UPDATE nft_registry\n",
    "            SET owner_account_id = %s, sale_status = 'sold', sold_at = NOW()\n",
    "            WHERE token_id = %s AND collection = %s\n",
    "        \"\"\", (winner_wallet, token_id, collection))\n",
]

with open(path, "w") as f:
    f.writelines(lines)

print("PATCH APPLIED SUCCESSFULLY")
