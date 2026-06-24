def decide(risk_score, current_limit):
    if risk_score < 30:
        return ("INCREASE", current_limit * 1.10)

    if risk_score < 60:
        return ("HOLD", current_limit)

    if risk_score < 85:
        return ("REDUCE", current_limit * 0.70)

    return ("FREEZE", 0)
