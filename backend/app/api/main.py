from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.api.services import Services, build_services
from app.config import PROJECT_ROOT, Settings, get_settings
from app.contracts import DecisionEnvelope
from app.contracts.schemas import DashboardFeedResponse, DecisionListResponse, SimulationRequest
from app.errors import NotFoundError, RagexError


def _services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(_services)]


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    api = FastAPI(title="Ragex Pricing Guardrail API", version="0.1.0")
    api.state.services = build_services(resolved_settings)

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.exception_handler(RagexError)
    async def handle_domain_error(_: Request, exc: RagexError) -> Any:
        status_code = 404 if isinstance(exc, NotFoundError) else 400
        return _error_response(status_code, "domain_error", str(exc))

    @api.get("/api/health")
    async def health(services: ServicesDep) -> dict[str, str]:
        return {
            "status": "ok",
            "repository_mode": services.settings.repository_mode,
            "vector_backend": services.settings.vector_backend,
        }

    @api.get("/api/decisions", response_model=DecisionListResponse)
    async def list_decisions(
        services: ServicesDep,
        limit: int = 100,
        flagged_only: bool = False,
    ) -> DecisionListResponse:
        decisions = await run_in_threadpool(
            services.repository.list_decisions,
            min(max(limit, 1), 500),
            flagged_only,
        )
        return DecisionListResponse(decisions=decisions)

    @api.post("/api/simulator/decisions", response_model=DecisionListResponse)
    async def simulate_decisions(
        request: SimulationRequest,
        services: ServicesDep,
    ) -> DecisionListResponse:
        decisions = await run_in_threadpool(
            services.simulator.generate,
            request.count,
            request.anomaly_mode,
        )
        return DecisionListResponse(decisions=decisions)

    @api.post("/api/guardrail/evaluate", response_model=DecisionEnvelope)
    async def evaluate_guardrail(
        decision: DecisionEnvelope,
        services: ServicesDep,
    ) -> DecisionEnvelope:
        result = await run_in_threadpool(services.guardrail.evaluate, decision)
        return decision.model_copy(update={"guardrail": result})

    @api.post("/api/regret/score")
    async def score_regret(
        decision: DecisionEnvelope,
        services: ServicesDep,
    ) -> dict[str, Any]:
        result = await run_in_threadpool(services.regret.score, decision)
        return result.model_dump(mode="json")

    @api.post("/api/explain")
    async def explain_decision(
        decision: DecisionEnvelope,
        services: ServicesDep,
    ) -> dict[str, Any]:
        result = await run_in_threadpool(services.explanation.explain, decision)
        return result.model_dump(mode="json")

    @api.get("/api/dashboard/feed", response_model=DashboardFeedResponse)
    async def dashboard_feed(
        services: ServicesDep,
        limit: int = 100,
    ) -> DashboardFeedResponse:
        decisions = await run_in_threadpool(services.dashboard.feed, min(max(limit, 1), 500))
        return DashboardFeedResponse(generated_at=datetime.now(UTC), decisions=decisions)

    static_dir = PROJECT_ROOT / "web" / "out"
    if static_dir.exists():
        api.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next-static")

        @api.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            requested = static_dir / full_path
            if requested.is_file():
                return FileResponse(requested)
            return FileResponse(static_dir / "index.html")

    return api


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"detail": {"code": code, "message": message}}
    )


app = create_app()
