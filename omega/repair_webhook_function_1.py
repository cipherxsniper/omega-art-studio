from pathlib import Path

FILE = Path("omega_stripe_webhook_revenue_intake_v1.py")

text = FILE.read_text()

start = text.find("def process_stripe_event(payload):")
end = text.find("@app.route")

if start == -1 or end == -1:
    print("FAILED: function boundaries not found")
    raise SystemExit(1)

replacement = '''
def process_stripe_event(payload):
    conn = connect_db()
    cur = conn.cursor()

    event = build_stripe_event(payload)

    result = insert_event(cur, event)

    conn.commit()
    conn.close()

    return result


'''

new_text = text[:start] + replacement + text[end:]

FILE.write_text(new_text)

print("WEBHOOK FUNCTION FULLY REPAIRED")
