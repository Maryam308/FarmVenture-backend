from fastapi import FastAPI
from controllers.users import router as UsersRouter
from controllers.hoots import router as HootsRouter  
from fastapi.middleware.cors import CORSMiddleware
import os

frontendUrl = os.getenv("FRONTENDURL")

app = FastAPI(
    title="Hoot API",
    description="A blogging platform API built with FastAPI",
    version="1.0.0"
)

# Include localhost for development and production frontend URL
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

if frontendUrl:
    origins.append(frontendUrl)

print(f"DEBUG: Final origins list: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://farm-venture-frontend-.*\.vercel\.app",  
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(UsersRouter, prefix="/api", tags=["Users"])
app.include_router(HootsRouter, prefix="/api", tags=["Hoots"])

@app.get('/')
def home():
    return {'message': 'Welcome to Hoot API! Visit /docs for API documentation.'}