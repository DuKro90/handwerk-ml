"""
Celery Task Monitoring API Endpoints

Endpoints for:
- Task status tracking
- Queue monitoring
- Worker statistics
- Task history
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from celery.result import AsyncResult
from app.celery_app import app as celery_app

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================
# TASK STATUS ENDPOINTS
# ============================================

@router.get("/task/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a specific Celery task

    Args:
        task_id: Celery task ID

    Returns:
        Task status with result or error information
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "error": str(result.info) if result.failed() else None,
            "ready": result.ready(),
            "successful": result.successful()
        }

    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Error getting task status")

@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str) -> Dict[str, Any]:
    """
    Get full result of a completed task

    Args:
        task_id: Celery task ID

    Returns:
        Complete task result or error details
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        if not result.ready():
            raise HTTPException(
                status_code=202,
                detail=f"Task is still running (status: {result.status})"
            )

        if result.failed():
            raise HTTPException(
                status_code=400,
                detail=f"Task failed: {str(result.info)}"
            )

        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task result: {e}")
        raise HTTPException(status_code=500, detail="Error getting task result")

# ============================================
# QUEUE MONITORING
# ============================================

@router.get("/queue/stats")
async def get_queue_stats() -> Dict[str, Any]:
    """
    Get overall queue statistics

    Returns:
        Stats for all queues and active tasks
    """
    try:
        # Get active tasks from all workers
        inspect = celery_app.control.inspect()

        active_tasks = inspect.active() or {}
        stats = inspect.stats() or {}
        reserved = inspect.reserved() or {}

        total_active = sum(len(tasks) for tasks in active_tasks.values())
        total_reserved = sum(len(tasks) for tasks in reserved.values())

        return {
            "active_tasks": total_active,
            "reserved_tasks": total_reserved,
            "workers": len(stats),
            "workers_active": list(active_tasks.keys()),
            "queue_stats": {
                worker: {
                    "pool": stat.get("pool", {}).get("implementation", "unknown"),
                    "max_concurrency": stat.get("pool", {}).get("max-concurrency"),
                    "processes": stat.get("pool", {}).get("processes"),
                    "active_tasks": len(active_tasks.get(worker, [])),
                    "reserved_tasks": len(reserved.get(worker, []))
                }
                for worker, stat in stats.items()
            }
        }

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting queue stats")

@router.get("/workers/stats")
async def get_workers_stats() -> Dict[str, Any]:
    """
    Get detailed worker statistics

    Returns:
        Stats for each worker process
    """
    try:
        inspect = celery_app.control.inspect()

        stats = inspect.stats() or {}
        active = inspect.active() or {}
        registered = inspect.registered() or {}

        workers_info = {}
        for worker_name, worker_stats in stats.items():
            workers_info[worker_name] = {
                "pool": worker_stats.get("pool", {}),
                "active_tasks": len(active.get(worker_name, [])),
                "registered_tasks": registered.get(worker_name, []),
                "system": worker_stats.get("rusage", {})
            }

        return {
            "workers": workers_info,
            "total_workers": len(stats)
        }

    except Exception as e:
        logger.error(f"Error getting workers stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting workers stats")

# ============================================
# ACTIVE TASKS MONITORING
# ============================================

@router.get("/tasks/active")
async def get_active_tasks(
    worker: str = Query(None, description="Filter by worker name")
) -> Dict[str, Any]:
    """
    Get all currently active tasks

    Args:
        worker: Optional worker name to filter by

    Returns:
        List of active tasks with details
    """
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}

        if worker:
            if worker not in active_tasks:
                raise HTTPException(status_code=404, detail=f"Worker {worker} not found")
            active_tasks = {worker: active_tasks[worker]}

        tasks_list = []
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                tasks_list.append({
                    "task_id": task.get("id"),
                    "task_name": task.get("name"),
                    "worker": worker_name,
                    "args": task.get("args"),
                    "kwargs": task.get("kwargs"),
                    "time_start": task.get("time_start")
                })

        return {
            "active_tasks": tasks_list,
            "total_count": len(tasks_list)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        raise HTTPException(status_code=500, detail="Error getting active tasks")

# ============================================
# TASK EXECUTION CONTROL
# ============================================

@router.post("/task/{task_id}/revoke")
async def revoke_task(task_id: str) -> Dict[str, Any]:
    """
    Revoke (cancel) a task

    Args:
        task_id: Task ID to revoke

    Returns:
        Revocation status
    """
    try:
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')

        logger.info(f"Revoked task: {task_id}")

        return {
            "status": "revoked",
            "task_id": task_id,
            "message": f"Task {task_id} has been revoked"
        }

    except Exception as e:
        logger.error(f"Error revoking task: {e}")
        raise HTTPException(status_code=500, detail="Error revoking task")

# ============================================
# HEALTH CHECK
# ============================================

@router.get("/health")
async def celery_health() -> Dict[str, Any]:
    """
    Check Celery broker and worker health

    Returns:
        Health status of Celery infrastructure
    """
    try:
        inspect = celery_app.control.inspect()

        # Try to get stats from workers
        stats = inspect.stats()

        if stats is None:
            return {
                "status": "unhealthy",
                "message": "No workers available",
                "broker_connected": False,
                "workers": 0
            }

        active = inspect.active() or {}
        total_active = sum(len(tasks) for tasks in active.values())

        return {
            "status": "healthy",
            "broker_connected": True,
            "workers": len(stats),
            "active_tasks": total_active,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Celery health check error: {e}")

        return {
            "status": "unhealthy",
            "message": str(e),
            "broker_connected": False,
            "workers": 0
        }

# ============================================
# TASK SUMMARY
# ============================================

@router.get("/summary")
async def get_celery_summary() -> Dict[str, Any]:
    """
    Get comprehensive Celery summary

    Returns:
        Overall system status and metrics
    """
    try:
        inspect = celery_app.control.inspect()

        stats = inspect.stats() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}

        total_active = sum(len(tasks) for tasks in active.values())
        total_reserved = sum(len(tasks) for tasks in reserved.values())

        return {
            "status": "healthy" if stats else "unhealthy",
            "workers": {
                "total": len(stats),
                "active": len([w for w in active.keys()])
            },
            "tasks": {
                "active": total_active,
                "reserved": total_reserved,
                "total": total_active + total_reserved
            },
            "broker": {
                "connected": True if stats else False,
                "type": "redis"
            },
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting celery summary: {e}")

        return {
            "status": "unhealthy",
            "message": str(e),
            "workers": {"total": 0, "active": 0},
            "tasks": {"active": 0, "reserved": 0, "total": 0},
            "broker": {"connected": False, "type": "redis"}
        }
