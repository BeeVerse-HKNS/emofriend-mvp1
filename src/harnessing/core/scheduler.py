from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import structlog

logger = structlog.get_logger()


def _run_ollama_update() -> None:
    try:
        from scripts.ollama_auto_update import OllamaAutoUpdater

        updater = OllamaAutoUpdater()
        results = updater.check_updates()
        for r in results:
            if r.updated:
                logger.info("scheduler_ollama_updated", model=r.model)
            else:
                logger.warning("scheduler_ollama_update_failed", model=r.model, error=r.error)
    except Exception as e:
        logger.error("scheduler_ollama_update_error", error=str(e))


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_ollama_update,
        CronTrigger(hour=9, minute=0),
        id="ollama_daily_update",
        name="Ollama Model Daily Update",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("scheduler_started", jobs=["ollama_daily_update"])
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler_stopped")


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler
