import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import create_document, get_documents, db
from schemas import Wish

app = FastAPI(title="Krishnali 20th Birthday API", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Birthday API running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Wishes endpoints
class WishOut(BaseModel):
    id: str
    name: str
    message: str
    relation: Optional[str] = None
    created_at: str


def _to_iso(dt_value):
    try:
        if isinstance(dt_value, str):
            return dt_value
        if isinstance(dt_value, datetime):
            return dt_value.isoformat()
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc: dict) -> dict:
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name", "Anonymous"),
        "message": doc.get("message", ""),
        "relation": doc.get("relation"),
        "created_at": _to_iso(doc.get("created_at")),
    }


@app.post("/api/wishes")
def create_wish(payload: Wish):
    try:
        wish_id = create_document("wish", payload)
        return {"success": True, "id": wish_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/wishes", response_model=List[WishOut])
def list_wishes(limit: int = 25):
    try:
        docs = get_documents("wish", {}, limit)
        def sort_key(d):
            v = d.get("created_at")
            if isinstance(v, datetime):
                return v
            try:
                return datetime.fromisoformat(v)
            except Exception:
                return datetime.min
        docs_sorted = sorted(docs, key=sort_key, reverse=True)
        return [_serialize(d) for d in docs_sorted]
    except Exception as e:
        # If database isn't configured, return empty list gracefully
        if 'Database not available' in str(e):
            return []
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
