from fastapi import FastAPI
from compare_routes import router as compare_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

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

# if __name__ == "__main__":
#     import os
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

