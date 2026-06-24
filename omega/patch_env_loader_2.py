from dotenv import load_dotenv
import os

load_dotenv()

print("ENV LOADED:", bool(os.getenv("STRIPE_SECRET_KEY")))
