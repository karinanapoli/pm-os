"""Routes for installation-wide custom AI provider management."""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from pm_os.web import config_operations as config_ops


def create_provider_router(
    *,
    config_manager,
    templates,
    context_builder: Callable,
    require_admin: Callable[[Request], None],
) -> APIRouter:
    router = APIRouter(prefix="/config/provider")

    @router.post("/add", response_class=HTMLResponse)
    async def add_custom_provider(
        request: Request,
        name: str = Form(...),
        model: str = Form(...),
        api_key: str = Form(""),
        base_url: str = Form(...),
    ):
        require_admin(request)
        config_manager.transaction(
            lambda config: config_ops.upsert_custom_provider(
                config,
                {
                    "name": name,
                    "model": model,
                    "api_key": api_key,
                    "base_url": base_url,
                },
            )
        )
        return templates.TemplateResponse(
            request,
            "config.html",
            context_builder(request, saved=False, notice="config.provider_added"),
        )

    @router.post("/delete", response_class=HTMLResponse)
    async def delete_custom_provider(
        request: Request,
        name: str = Form(...),
    ):
        require_admin(request)
        config_manager.transaction(
            lambda config: config_ops.remove_custom_provider(config, name)
        )
        return templates.TemplateResponse(
            request,
            "config.html",
            context_builder(request, saved=False, notice="config.provider_removed"),
        )

    return router
