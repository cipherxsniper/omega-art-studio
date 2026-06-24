def build_system_health_view(result, recon, run_fraud_scan):
    fraud = run_fraud_scan()
    high_risk = [r for r in fraud if r.get("risk_score", 0) >= 0.7]

    lines = ["🏥 *System Health Command Center*\n"]

    for k, v in (result or {}).items():
        status = str(v).lower()

        if status in ("ok", "online", "synced", "settled", "true"):
            icon = "✅"
        elif status in ("warning", "degraded", "drift"):
            icon = "⚠️"
        else:
            icon = "❌"

        lines.append(f"  {icon} `{k}`: `{v}`")

    lines.append("\n📊 *Reconciliation*")

    drift = recon.get("drift") if recon else None
    parity = recon.get("parity_score", 0.0) if recon else 0.0

    lines.append(f"  Drift: `{drift}` | Parity: `{parity:.4f}`")

    lines.append("\n🚨 *Fraud Summary*")
    lines.append(
        f"  Wallets scanned: `{len(fraud)}` | High risk: `{len(high_risk)}`"
    )

    for r in high_risk[:3]:
        lines.append(
            f"  ⚠️ `{r.get('wallet_id','unknown')}` score: `{r.get('risk_score',0)}`"
        )

    return "\n".join(lines)
