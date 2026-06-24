from omega_subscription_persistence_engine_v1 import persist_subscription_state

def handle_subscription(conn, event):

    persist_subscription_state(conn, event)
