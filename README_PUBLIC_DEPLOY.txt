SATELLITE BHARAT — PUBLIC DEPLOYMENT PACKAGE
============================================

This package is prepared for public deployment of Satellite Bharat Final V1.0.

Recommended deployment configuration:
- Runtime: Python
- Build: pip install -r requirements.txt
- Start: uvicorn main:app --host 0.0.0.0 --port $PORT
- Health check: /api/health

The included render.yaml is ready for a Render Web Service.

IMPORTANT:
- External public-data services can change or become unavailable.
- Risk/alert indicators are prototype dashboard analytics, not official emergency warnings.
- Internet access is required for external data feeds and map tiles.
- A custom domain can be connected after the service is live.
