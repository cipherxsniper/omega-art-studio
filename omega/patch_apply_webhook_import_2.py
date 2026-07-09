"""
PATCH INSTRUCTIONS:

Inside omega_bank_api.py add:

from patch_add_webhook_to_api import attach_webhook
attach_webhook(app)

This must be placed AFTER app = FastAPI()
"""

print("Apply manually inside omega_bank_api.py:")
print("from patch_add_webhook_to_api import attach_webhook")
print("attach_webhook(app)")
