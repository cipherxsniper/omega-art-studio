from omega_env_bootstrap_v1 import bootstrap_env

def run():
    env = bootstrap_env()

    print("🧪 OMEGA ENV SELF CHECK")
    print({
        "stripe": bool(env.get("STRIPE_SECRET")),
        "webhook": bool(env.get("STRIPE_WEBHOOK_SECRET")),
        "db": env.get("DB_PATH"),
        "mode": env.get("MODE"),
        "status": "ENV_BOOTSTRAP_OK"
    })

if __name__ == "__main__":
    run()
