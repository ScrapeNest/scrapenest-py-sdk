"""Minimal FastAPI webhook receiver that verifies ScrapeNest signatures.

    pip install fastapi uvicorn
    SCRAPENEST_WEBHOOK_SECRET=whsec_... uvicorn examples.webhook_receiver:app
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, Response

from scrapenest import WebhookVerificationError, verify_webhook

app = FastAPI()
SECRET = os.environ["SCRAPENEST_WEBHOOK_SECRET"]


@app.post("/webhooks/scrapenest")
async def receive(request: Request) -> Response:
    body = await request.body()
    try:
        event = verify_webhook(body, request.headers, SECRET)
    except WebhookVerificationError:
        return Response(status_code=400, content="invalid signature")

    # Trust the payload only after verification succeeds.
    print("received event:", event.get("type"))
    return Response(status_code=204)
