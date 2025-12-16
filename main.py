from fastapi import FastAPI
from controllers.users import router as UsersRouter
from controllers.products import router as ProductsRouter

from fastapi.middleware.cors import CORSMiddleware
import os
from controllers.activities import router as ActivitiesRouter
frontendUrl = os.getenv("FRONTENDURL")

app = FastAPI(
    title="FarmVenture API",
    description="A farm platform API built with FastAPI",
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
app.include_router(ProductsRouter, prefix="/api", tags=["Products"])
app.include_router(ActivitiesRouter, prefix="/api", tags=["Activities"])

@app.get('/')
def home():
    return {'message': 'Welcome to FarmVenture API! Visit /docs for API documentation.'}