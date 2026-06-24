class IdentityLock:

    def __init__(self):
        self.sessions = {}  # uid → wallet_id

    def bind(self, user_id, wallet_id):
        self.sessions[user_id] = wallet_id

    def get_wallet(self, user_id):
        return self.sessions.get(user_id)

    def verify(self, user_id, wallet_id):
        return self.sessions.get(user_id) == wallet_id
