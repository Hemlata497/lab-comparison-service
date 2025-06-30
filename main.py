from fastapi import FastAPI
from compare_routes import router as compare_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

app = FastAPI(title="Lab Test Comparison API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the comparison routes
app.include_router(compare_router, tags=["compare"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
