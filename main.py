from fastapi import FastAPI
from controllers.users import router as UsersRouter
from controllers.hoots import router as HootsRouter  # NEW
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Hoot API",
    description="A blogging platform API built with FastAPI",
    version="1.0.0"
)

origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routers
app.include_router(UsersRouter, prefix="/api", tags=["Users"])
app.include_router(HootsRouter, prefix="/api", tags=["Hoots"])  # NEW

@app.get('/')
def home():
    return {'message': 'Welcome to Hoot API! Visit /docs for API documentation.'}