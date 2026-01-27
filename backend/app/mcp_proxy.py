
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response
import httpx

app = FastAPI()

TARGET = "http://127.0.0.1:8000/mcp"

@app.api_route("/mcp", methods=["GET", "POST", "OPTIONS"])
async def proxy_mcp(request: Request):
    headers = dict(request.headers)
    # rewrite host ให้เป็นของที่ server ยอมรับ
    headers["host"] = "127.0.0.1:8000"

    async with httpx.AsyncClient(timeout=None) as client:
        upstream = await client.request(
            request.method,
            TARGET,
            headers=headers,
            content=await request.body(),
        )

        # ถ้าเป็น SSE ให้ส่งแบบ streaming
        if upstream.headers.get("content-type", "").startswith("text/event-stream"):
            async def gen():
                async for chunk in upstream.aiter_raw():
                    yield chunk
            return StreamingResponse(gen(), status_code=upstream.status_code, headers=dict(upstream.headers))

        return Response(content=upstream.content, status_code=upstream.status_code, headers=dict(upstream.headers))
