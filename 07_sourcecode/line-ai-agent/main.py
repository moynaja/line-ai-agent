"""
Thin compatibility shim so `uvicorn main:app` keeps working unchanged (this
is what render.yaml's startCommand and any existing local dev workflow use).
The actual app now lives in app/main.py — see that file and the app/
package for all real logic.
"""
from app.main import app  # noqa: F401

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    # reload=True is a local-dev convenience only — never enable it in
    # production. Set DEV_RELOAD=1 locally if you want it back.
    dev_reload = os.getenv("DEV_RELOAD", "0") == "1"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=dev_reload)
