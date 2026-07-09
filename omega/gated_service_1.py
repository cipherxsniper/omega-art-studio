from fastapi import FastAPI, HTTPException
from security.access_control import has_access

app = FastAPI()


@app.get("/service/{user_id}")
def service(user_id: str):

    if not has_access(user_id):
        raise HTTPException(status_code=403, detail="No subscription")

    return {
        "status": "active",
        "service": "Omega AI Engine",
        "features": ["automation", "crm", "outreach"]
    }
