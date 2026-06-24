from omega_state_machine import WalletState, AuthState

class StateRules:

    wallet_transitions = {
        WalletState.ACTIVE: [WalletState.FROZEN, WalletState.RESTRICTED, WalletState.CLOSED],
        WalletState.FROZEN: [WalletState.ACTIVE, WalletState.CLOSED],
        WalletState.RESTRICTED: [WalletState.ACTIVE, WalletState.CLOSED],
        WalletState.CLOSED: []
    }

    auth_transitions = {
        AuthState.INITIATED: [AuthState.AUTHORIZED, AuthState.EXPIRED],
        AuthState.AUTHORIZED: [AuthState.CAPTURED, AuthState.REVERSED],
        AuthState.CAPTURED: [AuthState.SETTLED, AuthState.DISPUTED],
        AuthState.SETTLED: [],
        AuthState.REVERSED: [],
        AuthState.EXPIRED: [],
        AuthState.DISPUTED: [AuthState.SETTLED, AuthState.REVERSED]
    }

    def validate_wallet(self, from_state, to_state):
        return to_state in self.wallet_transitions.get(from_state, [])

    def validate_auth(self, from_state, to_state):
        return to_state in self.auth_transitions.get(from_state, [])
