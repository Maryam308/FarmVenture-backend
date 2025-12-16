from fastapi import FastAPI
from controllers.users import router as UsersRouter
from controllers.hoots import router as HootsRouter  
from fastapi.middleware.cors import CORSMiddleware
import os

# Debug: Print environment variable
print(f"DEBUG: FRONTENDURL = {os.getenv('FRONTENDURL')}")

frontendUrl = os.getenv("FRONTENDURL")

app = FastAPI(
    title="Hoot API",
    description="A blogging platform API built with FastAPI",
    version="1.0.0"
)

# Debug origins
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

if frontendUrl:
    print(f"DEBUG: Adding frontendUrl to origins: {frontendUrl}")
    origins.append(frontendUrl)
else:
    print("DEBUG: frontendUrl is None or empty!")

print(f"DEBUG: Final origins list: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routers
app.include_router(UsersRouter, prefix="/api", tags=["Users"])
app.include_router(HootsRouter, prefix="/api", tags=["Hoots"])

@app.get('/')
def home():
    return {'message': 'Welcome to Hoot API! Visit /docs for API documentation.'}