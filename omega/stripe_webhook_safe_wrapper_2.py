import traceback

def safe_handler(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print("[WEBHOOK ERROR]", str(e))
            print(traceback.format_exc())
            return {"status": "error_logged"}, 200  # IMPORTANT: never crash Stripe
    return wrapper
