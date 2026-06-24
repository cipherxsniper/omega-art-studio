from omega_db_kernel_v1 import insert_event

def append_event(cur, event):
    insert_event(cur, event)
