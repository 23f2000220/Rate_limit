import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "23f2000220@ds.study.iitm.ac.in"

# ------------------------
# Rate Limit Configuration
# ------------------------
RATE_LIMIT = 11          # requests
WINDOW = 10              # seconds

# allowed origin assigned in question
ALLOWED_ORIGIN = "https://app-e4kt4p.example.com"

# Add the exam page origin too.
# (The grader's browser uses this.)
EXTRA_ALLOWED = [
    "https://exam.sanand.workers.dev",
]

allowed_origins = [ALLOWED_ORIGIN] + EXTRA_ALLOWED

app = FastAPI()

# ------------------------
# CORS Middleware
# ------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = defaultdict(deque)

@app.middleware("http")
async def app_middleware(request: Request, call_next):
    # ---------- Request ID ----------
    request_id = request.headers.get("x-request-id")
    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # ---------- Rate limiting ----------
    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()
    bucket = clients[client]

    while bucket and now - bucket[0] > WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )
        response.headers.append("X-Request-ID", request_id)
        return response

    bucket.append(now)

    # ---------- Continue ----------
    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# ------------------------
# Endpoint
# ------------------------

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.get("/")
async def root():
    return {"status": "running"}
