from fastapi import FastAPI, Response, Request

app = FastAPI(title="C2C Backend")

@app.middleware("http")
async def auto_head(request: Request, call_next):
    # 如果是 HEAD 并且 GET 存在，则临时改为 GET 执行，再返回无正文响应（不要留下 content-length）
    if request.method == "HEAD":
        request.scope["method"] = "GET"
        response = await call_next(request)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(content=b"", status_code=response.status_code, headers=headers, media_type=response.media_type)
    return await call_next(request)


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return {"status": "ok", "see": ["/health", "/docs"]}

