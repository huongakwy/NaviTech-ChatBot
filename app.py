import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from app_environment import AppEnvironment
from env import env
import alembic.config
from fastapi.middleware.cors import CORSMiddleware
from controllers import (
    chatbot,
    chat,
    user,
    message,
    product,
    pipeline_endpoint,
    file_upload,
    personality
)

from agent import (
    product_agent,
    recomendation_agent,
    compose_history,
    chat_pipeline,
    document_retrieval_agent,
    personality_agent
                   )
from starlette.middleware.base import BaseHTTPMiddleware
from env import env

# Migrate the database to its latest version
# Not thread safe, so it should be update once we are running multiple instances
alembic.config.main(argv=["--raiseerr", "upgrade", "head"])

app = FastAPI(debug=env.DEBUG)

if AppEnvironment.is_local_env(env.APP_ENV):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(chat_pipeline.router, prefix="/api")
app.include_router(compose_history.router, prefix="/api")
app.include_router(recomendation_agent.router, prefix="/api")
app.include_router(product_agent.router, prefix="/api")
app.include_router(document_retrieval_agent.router, prefix="/api")
app.include_router(personality_agent.router, prefix="/api")

app.include_router(chatbot.router, prefix="/api")
# app.include_router(ani_chat.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(message.router, prefix="/api")
app.include_router(product.router, prefix="/api")
app.include_router(pipeline_endpoint.router, prefix="/api")
app.include_router(file_upload.router, prefix="/api")
app.include_router(personality.router)

class StaticFileMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        static_dir = "static"

        file_path = os.path.join(static_dir, path.lstrip("/"))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Nếu không tìm thấy trong static, chuyển đến next middleware
        return await call_next(request)


app.add_middleware(StaticFileMiddleware)
