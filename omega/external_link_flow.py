import uuid
from core.external_accounts import ExternalAccountStore

store = ExternalAccountStore()

sessions = {}

def start_link(uid):
    sessions[uid] = {"step": "provider"}

def handle(uid, text):

    if sessions.get(uid, {}).get("step") == "provider":
        sessions[uid]["provider"] = text
        sessions[uid]["step"] = "label"
        return "Enter label (e.g. CashApp Main, Bank Checking)"

    if sessions.get(uid, {}).get("step") == "label":
        sessions[uid]["label"] = text
        sessions[uid]["step"] = "identifier"
        return "Enter identifier (CashTag / routing / email / IBAN)"

    if sessions.get(uid, {}).get("step") == "identifier":

        store.add_account(
            id=str(uuid.uuid4()),
            user_id=str(uid),
            provider=sessions[uid]["provider"],
            label=sessions[uid]["label"],
            identifier=text
        )

        sessions.pop(uid, None)

        return "External account linked successfully"
