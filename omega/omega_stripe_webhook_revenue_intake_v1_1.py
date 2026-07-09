def process_stripe_event(payload):
    conn = connect_db()
    cur = conn.cursor()

    try:
        event = build_stripe_event(payload)

        # STRIPE EVENT ROUTER (minimal safe hook)
        if event.get("type") == "payment_intent.succeeded":
            create_subscription(event)

        result = insert_event(cur, event)

        conn.commit()
        return result

    except Exception as e:
        print('[SUBSCRIPTION INSERT ERROR]', str(e))
        conn.rollback()
        return None

    finally:
        conn.close()


