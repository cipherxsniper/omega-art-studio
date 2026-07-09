TREASURY = {
    "reserves": 12000000.0
}

def check_liability_limit(total_liabilities):
    return total_liabilities <= TREASURY["reserves"]
