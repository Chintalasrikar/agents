from fastapi import FastAPI
from email_agent import router as email_agent_router

app = FastAPI()

app.include_router(email_agent_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

