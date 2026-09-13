from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import os
from datetime import datetime, timezone
from math import radians, sin, cos, asin, sqrt

app = FastAPI(title="Satellite Bharat Final V1.0")


# =========================================================
# COMMON API HELPER
# =========================================================

async def fetch_json(url, params=None):
    try:
        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "SatelliteBharat/Phase35-38"}
        ) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    except Exception as e:
        return {"error": str(e)}


# =========================================================
# LOCATION SEARCH / GEOCODING
# =========================================================

async def geocode_location(query: str):
    query = (query or "").strip()

    if not query:
        return {"error": "Location is required"}

    data = await fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {
            "name": query,
            "count": 5,
            "language": "en",
            "format": "json"
        }
    )

    if not isinstance(data, dict):
        return {"error": "Invalid geocoding response"}

    results = data.get("results") or []

    if not results:
        return {
            "error": f"Location not found: {query}",
            "query": query,
            "results": []
        }

    locations = []

    for x in results:
        locations.append({
            "name": x.get("name"),
            "latitude": x.get("latitude"),
            "longitude": x.get("longitude"),
            "country": x.get("country"),
            "country_code": x.get("country_code"),
            "admin1": x.get("admin1"),
            "admin2": x.get("admin2"),
            "timezone": x.get("timezone"),
            "population": x.get("population"),
        })

    return {
        "query": query,
        "count": len(locations),
        "results": locations
    }


@app.get("/api/location-search")
async def location_search(q: str = ""):
    """
    Search any city/place and return real coordinates.
    Example:
      /api/location-search?q=Mumbai
    """
    return await geocode_location(q)


# =========================================================
# HOME / DASHBOARD
# =========================================================


@app.get("/", response_class=HTMLResponse)
async def home():
    return (Path(__file__).resolve().parent / "dashboard.html").read_text(encoding="utf-8")


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "phase": "FINAL-V1.0",
        "updated": datetime.now(timezone.utc).isoformat()
    }


# =========================================================
# WEATHER
# =========================================================

@app.get("/api/weather")
async def weather(
    lat: float = 28.6139,
    lon: float = 77.2090
):
    return await fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "wind_speed_10m,"
                "precipitation"
            ),
            "hourly": (
                "temperature_2m,"
                "precipitation_probability,"
                "wind_speed_10m"
            ),
            "forecast_days": 2,
            "timezone": "auto"
        }
    )


# =========================================================
# EARTHQUAKES
# =========================================================

@app.get("/api/earthquakes")
async def earthquakes():

    data = await fetch_json(
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    )

    events = []

    for f in data.get("features", []) if isinstance(data, dict) else []:

        p = f.get("properties") or {}

        c = (
            f.get("geometry") or {}
        ).get(
            "coordinates"
        ) or [None, None, None]

        events.append({
            "place": p.get("place"),
            "mag": p.get("mag"),
            "time": p.get("time"),
            "lat": c[1],
            "lon": c[0],
            "depth": c[2],
            "url": p.get("url")
        })

    return {
        "count": len(events),
        "events": events
    }


# =========================================================
# NASA EONET NATURAL EVENTS
# =========================================================

@app.get("/api/eonet")
async def eonet(limit: int = 100):

    data = await fetch_json(
        "https://eonet.gsfc.nasa.gov/api/v3/events",
        {
            "status": "open",
            "limit": max(1, min(limit, 200))
        }
    )

    events = []

    for e in data.get("events", []) if isinstance(data, dict) else []:

        geom = e.get("geometry") or []

        latest = geom[-1] if geom else {}

        coords = latest.get("coordinates")

        events.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "categories": e.get("categories") or [],
            "date": latest.get("date"),
            "coordinates": coords,
            "closed": e.get("closed"),
            "link": e.get("link"),
            "source": "NASA EONET"
        })

    return {
        "count": len(events),
        "events": events
    }


# =========================================================
# NEWS
# =========================================================

@app.get("/api/news")
async def news(q: str = "world"):

    data = await fetch_json(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        {
            "query": q,
            "mode": "artlist",
            "maxrecords": 30,
            "format": "json",
            "sort": "datedesc"
        }
    )

    articles = []

    for a in data.get("articles", []) if isinstance(data, dict) else []:

        articles.append({
            "title": a.get("title"),
            "url": a.get("url"),
            "domain": a.get("domain"),
            "date": a.get("seendate"),
            "language": a.get("language")
        })

    return {
        "count": len(articles),
        "articles": articles
    }


# =========================================================
# TIMELINE
# =========================================================

@app.get("/api/timeline")
async def timeline(q: str = "Delhi"):

    data = await fetch_json(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        {
            "query": q,
            "mode": "timelinevol",
            "format": "json",
            "maxrecords": 250
        }
    )

    return {
        "query": q,
        "data": data
    }


# =========================================================
# SATELLITE
# =========================================================

@app.get("/api/satellite")
async def satellite():

    return {
        "provider": "NASA GIBS",
        "layer": "MODIS Terra Corrected Reflectance True Color",
        "map_url": "https://worldview.earthdata.nasa.gov/",
        "note": (
            "Latest-available public imagery; "
            "product timing varies by layer and region."
        )
    }


# =========================================================
# BRIEF
# =========================================================

@app.get("/api/brief")
async def brief(
    q: str = "Delhi",
    lat: float | None = None,
    lon: float | None = None
):
    # If the browser sends only a city name, resolve its real coordinates.
    if lat is None or lon is None:
        geo = await geocode_location(q)

        if geo.get("results"):
            first = geo["results"][0]
            q = first.get("name") or q
            lat = first.get("latitude")
            lon = first.get("longitude")

    # Safe fallback only when geocoding failed.
    if lat is None or lon is None:
        lat = 28.6139
        lon = 77.2090

    w, e, n, x = await asyncio.gather(
        weather(lat, lon),
        earthquakes(),
        news(q),
        eonet(50)
    )

    current = w.get("current") or {}

    return {
        "location": q,
        "latitude": lat,
        "longitude": lon,
        "weather": current,
        "earthquakes_today": e.get("count", 0),
        "news_results": n.get("count", 0),
        "natural_events": x.get("count", 0),

        "source_status": {
            "weather": "Open-Meteo",
            "earthquakes": "USGS",
            "news": "GDELT",
            "natural_events": "NASA EONET",
            "satellite": "NASA GIBS"
        },

        "confidence": "source-backed summary",

        "disclaimer": (
            "यह intelligence summary है; "
            "official emergency warning नहीं।"
        )
    }



# =========================================================
# AI SEARCH / LIVE ANSWER
# =========================================================

@app.post("/api/ai-search")
async def ai_search(payload: dict):
    """
    Answer a user's question using the OpenAI Responses API with web search.
    The API key is read only from the server-side OPENAI_API_KEY environment
    variable and is never exposed to the browser.
    """
    question = str((payload or {}).get("question") or "").strip()
    location = str((payload or {}).get("location") or current_location_for_ai())

    if not question:
        return {"ok": False, "error": "Please enter a question."}

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "ok": False,
            "setup_required": True,
            "error": "AI Search is not connected yet. Add OPENAI_API_KEY in Render Environment Variables."
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

        prompt = f"""You are Satellite Bharat's live Earth-intelligence assistant.
Current user location: {location}
User question: {question}

Answer the question using current web information when the question is time-sensitive,
location-specific, news-related, or asks what is happening now. Prefer authoritative
and primary sources. For India, prioritize IMD, NDMA/SACHET, National Centre for Seismology,
ISRO, government departments, and other official agencies when relevant. For global events,
prefer USGS, NASA, NOAA, WHO, national governments, and other primary sources. Avoid weak
aggregators, scraped pages, social-media mirrors, or SEO sites when a reliable primary source
is available. Do not invent facts. Clearly distinguish confirmed facts from uncertainty.
For emergencies, do not present yourself as an official warning system. Keep the answer concise.
Use this exact structure when web sources are used:
1. ANSWER — the useful answer in 2-6 short paragraphs or bullets.
2. STATUS — one short line saying Confirmed, Developing, or Unverified where useful.
3. SOURCES — a short bullet list. Each source line MUST contain a normal URL beginning with https://.
Do not wrap URLs in Markdown link syntax and do not put brackets around URLs. Use only sources
actually consulted for the answer. If no web source was needed, omit SOURCES."""

        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            input=prompt,
            max_output_tokens=900
        )

        return {
            "ok": True,
            "question": question,
            "location": location,
            "answer": response.output_text or "No answer was returned.",
            "model": model
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"AI Search error: {str(e)}"
        }


def current_location_for_ai():
    return "Delhi"

# =========================================================
# DISTANCE CALCULATION
# =========================================================

def distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    try:

        p1 = radians(float(lat1))
        p2 = radians(float(lat2))

        dlat = p2 - p1

        dlon = (
            radians(float(lon2))
            - radians(float(lon1))
        )

        a = (
            sin(dlat / 2) ** 2
            +
            cos(p1)
            * cos(p2)
            * sin(dlon / 2) ** 2
        )

        return 6371.0 * 2 * asin(sqrt(a))

    except Exception:

        return None


# =========================================================
# LOCATION CONTEXT
# =========================================================

@app.get("/api/location")
async def location(
    q: str = "Delhi",
    lat: float | None = None,
    lon: float | None = None
):
    """
    Return the active location and real coordinates.
    If coordinates are not supplied, geocode the location name.
    """
    if lat is None or lon is None:
        geo = await geocode_location(q)

        if geo.get("results"):
            first = geo["results"][0]
            return {
                "location": first.get("name") or q,
                "latitude": first.get("latitude"),
                "longitude": first.get("longitude"),
                "country": first.get("country"),
                "country_code": first.get("country_code"),
                "admin1": first.get("admin1"),
                "timezone": first.get("timezone"),
                "results": geo.get("results", [])
            }

        return {
            "location": q,
            "latitude": None,
            "longitude": None,
            "results": []
        }

    return {
        "location": q,
        "latitude": lat,
        "longitude": lon,
        "results": []
    }


# =========================================================
# CORRELATION
# =========================================================


@app.get("/api/correlate")
async def correlate(
    lat: float = 28.6139,
    lon: float = 77.2090,
    radius_km: float = 500
):

    eq, eo = await asyncio.gather(
        earthquakes(),
        eonet(150)
    )

    signals = []

    # -----------------------------
    # Earthquake signals
    # -----------------------------

    for x in eq.get("events", []):

        d = distance_km(
            lat,
            lon,
            x.get("lat"),
            x.get("lon")
        )

        if d is not None and d <= radius_km:

            signals.append({
                "type": "earthquake",
                "title": x.get("place"),
                "magnitude": x.get("mag"),
                "distance_km": round(d, 1),
                "url": x.get("url")
            })


    # -----------------------------
    # NASA natural events
    # -----------------------------

    for x in eo.get("events", []):

        c = x.get("coordinates")

        if isinstance(c, list) and len(c) >= 2:

            d = distance_km(
                lat,
                lon,
                c[1],
                c[0]
            )

            if d is not None and d <= radius_km:

                signals.append({
                    "type": "natural_event",
                    "title": x.get("title"),
                    "distance_km": round(d, 1),
                    "date": x.get("date"),
                    "url": x.get("link")
                })


    signals.sort(
        key=lambda x: x.get(
            "distance_km",
            999999
        )
    )

    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
        "count": len(signals),
        "signals": signals[:100]
    }


# =========================================================
# RISK
# =========================================================

@app.get("/api/risk")
async def risk(
    lat: float = 28.6139,
    lon: float = 77.2090
):

    c = await correlate(
        lat,
        lon,
        500
    )

    score = 0

    reasons = []

    for x in c.get("signals", []):

        if x["type"] == "earthquake":

            mag = float(
                x.get("magnitude") or 0
            )

            score += min(
                40,
                max(
                    0,
                    (mag - 3) * 8
                )
            )

            if mag >= 5:

                reasons.append(
                    f"Earthquake M{mag:g} "
                    f"within {x['distance_km']} km"
                )

        else:

            score += 4


    score = min(
        100,
        round(score)
    )


    if score < 25:

        level = "LOW"

    elif score < 55:

        level = "MODERATE"

    elif score < 80:

        level = "HIGH"

    else:

        level = "CRITICAL"


    return {
        "score": score,
        "level": level,
        "reasons": reasons[:8],
        "signals": c.get("count", 0),

        "disclaimer": (
            "Prototype risk indicator; "
            "not an official emergency warning."
        )
    }


# =========================================================
# ALERT CENTER
# =========================================================

@app.get("/api/alert-center")
async def alert_center(
    lat: float = 28.6139,
    lon: float = 77.2090
):

    r = await risk(
        lat,
        lon
    )

    return {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "risk": r,

        "recommended_actions": [

            "Verify with official local authorities for emergencies",

            "Review nearby event signals",

            "Keep monitoring enabled"
        ]
    }


# =========================================================
# ALERT EVALUATION
# =========================================================

@app.get("/api/alert-evaluate")
async def alert_evaluate(
    location: str = "Delhi",
    category: str = "earthquake",
    priority: str = "any"
):

    e = await earthquakes()

    events = e.get(
        "events",
        []
    )


    if category == "earthquake":

        minimum_magnitude = (
            5
            if priority == "high"
            else 0
        )

        matches = [

            x
            for x in events

            if (
                x.get("mag") or 0
            ) >= minimum_magnitude
        ]


    else:

        x = await eonet(100)

        matches = x.get(
            "events",
            []
        )

        key = category.lower()

        filtered = []

        for v in matches:

            title = (
                v.get("title")
                or ""
            ).lower()

            categories = v.get(
                "categories",
                []
            )

            category_match = any(

                key in (
                    c.get("title")
                    or ""
                ).lower()

                for c in categories
            )

            if (
                key in title
                or category_match
            ):

                filtered.append(v)

        matches = filtered


    return {

        "location": location,

        "category": category,

        "priority": priority,

        "matches": matches[:25],

        "checked_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }
