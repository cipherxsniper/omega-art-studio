from omega_db_kernel_v1 import OmegaTransaction, insert_event

def reconcile(event):
    try:
        with OmegaTransaction() as cur:
            insert_event(cur, event)
        return {"status": "RECONCILED"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
