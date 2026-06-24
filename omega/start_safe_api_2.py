import uvicorn

# IMPORTANT: bypass broken module startup
if __name__ == "__main__":
    try:
        uvicorn.run("omega_bank_api:app", host="0.0.0.0", port=8000)
    except Exception as e:
        print("[API BOOT FAILED SAFE MODE]", e)
