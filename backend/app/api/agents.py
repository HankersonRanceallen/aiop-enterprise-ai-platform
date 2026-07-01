import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.user import User
from app.schemas.agents import AgentRunRequest, AgentRunOut, AgentRunListOut
from app.api.deps import get_current_user
from app.services.agents.graph import stream_agent_run

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/run/stream")
async def run_agent_stream(
    payload: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the multi-agent workflow and stream progress via SSE.

    Connect with EventSource on the frontend:
        const es = new EventSource('/api/v1/agents/run/stream')

    Events:
        {type: "started"}
        {type: "step_done", agent: "planner", message: "..."}
        {type: "step_done", agent: "retriever", ...}
        {type: "step_done", agent: "analysis", ...}
        {type: "step_done", agent: "report", ...}
        {type: "complete", report: "...", step_log: [...]}
        {type: "error", message: "..."}
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must belong to an organization to run agents",
        )

    # Create a run record in DB
    run = AgentRun(
        task=payload.task,
        status=AgentRunStatus.RUNNING,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    run_id = run.id
    start = time.monotonic()

    async def event_generator():
        step_log = []
        final_report = ""
        total_tokens = 0
        succeeded = False

        try:
            async for event_str in stream_agent_run(
                task=payload.task,
                organization_id=current_user.organization_id,
                db=db,
                document_ids=payload.document_ids,
            ):
                yield event_str

                # Parse event to capture final state for DB save
                import json
                try:
                    event = json.loads(event_str.replace("data: ", "").strip())
                    if event["type"] == "step_done":
                        step_log.append(event)
                    elif event["type"] == "complete":
                        final_report = event.get("report", "")
                        step_log = event.get("step_log", step_log)
                        total_tokens = event.get("total_tokens", 0)
                        succeeded = True
                except Exception:
                    pass

        except Exception as e:
            import json
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Save final state to DB
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import update

            latency_ms = (time.monotonic() - start) * 1000

            async with AsyncSessionLocal() as save_db:
                await save_db.execute(
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=AgentRunStatus.COMPLETE if succeeded else AgentRunStatus.FAILED,
                        step_log=step_log,
                        final_report=final_report,
                        total_tokens=total_tokens,
                        latency_ms=round(latency_ms, 1),
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await save_db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Run-Id": str(run_id),
        },
    )


@router.get("/runs", response_model=list[AgentRunListOut])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/runs/{run_id}", response_model=AgentRunOut)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == current_user.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run
