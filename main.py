from fastapi import FastAPI
from compare_routes import router as compare_router
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="Lab Test Comparison API")

# Root health check
@app.get("/")
def root():
    return {"message": "Lab Comparison Service is running"}

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include compare routes
app.include_router(compare_router, tags=["compare"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
