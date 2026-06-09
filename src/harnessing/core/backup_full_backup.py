from __future__ import annotations

import structlog

logger = structlog.get_logger()


class BackupFullBackup:
    def __init__(self) -> None:
        self._formula = "^(K)"
        self._capability = "backup_full_backup"

    def backup_full_backup(self, input_data: dict) -> dict:
        try:
            result = self._process(input_data)
            logger.info("backup_full_backup_success", capability=self._capability)
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("backup_full_backup_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def _process(self, input_data: dict) -> dict:
        return {"processed": True, "input_keys": list(input_data.keys())}
