from fastapi import FastAPI
from controllers.users import router as UsersRouter
from controllers.products import router as ProductsRouter
from controllers.activities import router as ActivitiesRouter
from controllers.bookings import router as BookingsRouter
from controllers.favorites import router as FavoritesRouter
from fastapi.middleware.cors import CORSMiddleware
import os

frontendUrl = os.getenv("FRONTENDURL")

app = FastAPI(
    title="FarmVenture API",
    description="A farm platform API built with FastAPI",
    version="1.0.0"
)

# CORS Configuration
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173"
]

# Add production frontend URL if exists
if frontendUrl:
    origins.append(frontendUrl)
   

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specific origins
    allow_origin_regex=r"https://farm-venture-frontend-.*\.vercel\.app",  # Regex for Vercel previews
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.include_router(UsersRouter, prefix="/api", tags=["Users"])
app.include_router(ProductsRouter, prefix="/api", tags=["Products"])
app.include_router(ActivitiesRouter, prefix="/api/activities", tags=["Activities"]) 
app.include_router(FavoritesRouter, prefix="/api", tags=["Favorites"])
app.include_router(BookingsRouter, prefix="/api/bookings", tags=["Bookings"])

@app.get('/')
def home():
    return {'message': 'Welcome to FarmVenture API! Visit /docs for API documentation.'}
