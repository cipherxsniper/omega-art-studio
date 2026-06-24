from omega_subscription_persistence_engine_v1 import persist_subscription_state

def handle_subscription_event(conn, event):
    """
    ONLY ENTRY POINT FOR SUBSCRIPTIONS
    """

    persist_subscription_state(conn, event)
