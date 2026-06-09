#!/usr/bin/env python3

import json
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


class PowerState(Enum):
    ON = "on"
    OFF = "off"
    ON_UPS = "on_ups"


class DisasterType(Enum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    TYPHOON = "typhoon"
    FIRE = "fire"
    POWER_OUTAGE = "power_outage"
    NETWORK_OUTAGE = "network_outage"
    COOLING_FAILURE = "cooling_failure"
    PANDEMIC = "pandemic"


class RecoveryStatus(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PowerStatus:
    state: PowerState
    ups_battery_pct: Optional[float]
    timestamp: str
    outage_count: int = 0


@dataclass
class TemperatureReading:
    zone: str
    temp_celsius: float
    timestamp: str
    is_overheating: bool


@dataclass
class RecoveryPlan:
    disaster_type: DisasterType
    recovery_steps: List[str]
    rto_hours: float
    rpo_hours: float
    status: RecoveryStatus = RecoveryStatus.INACTIVE
    activated_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class EnvironmentalEvent:
    event_type: str
    details: Dict[str, Any]
    timestamp: str
    handled: bool = False
    recovery_attempted: bool = False
    recovery_success: bool = False


class PowerMonitor:
    def __init__(self):
        self._current_status: Optional[PowerStatus] = None
        self._history: List[PowerStatus] = []
        self._outage_count: int = 0
        self._last_outage_time: Optional[str] = None

    def report_power_status(self, is_on: bool, ups_battery_pct: Optional[float] = None) -> PowerStatus:
        if is_on:
            if self._current_status and self._current_status.state == PowerState.OFF:
                self._outage_count += 1
                self._last_outage_time = self._current_status.timestamp
            state = PowerState.ON
        else:
            state = PowerState.ON_UPS if ups_battery_pct is not None and ups_battery_pct > 0 else PowerState.OFF

        status = PowerStatus(
            state=state,
            ups_battery_pct=ups_battery_pct,
            timestamp=datetime.now().isoformat(),
            outage_count=self._outage_count,
        )
        self._current_status = status
        self._history.append(status)
        return status

    def is_power_on(self) -> bool:
        if self._current_status is None:
            return True
        return self._current_status.state in (PowerState.ON, PowerState.ON_UPS)

    def get_ups_status(self) -> Dict[str, Any]:
        if self._current_status is None:
            return {"available": False, "battery_pct": None, "on_ups": False}
        return {
            "available": self._current_status.ups_battery_pct is not None,
            "battery_pct": self._current_status.ups_battery_pct,
            "on_ups": self._current_status.state == PowerState.ON_UPS,
        }

    def get_outage_count(self) -> int:
        return self._outage_count

    def get_history(self) -> List[PowerStatus]:
        return list(self._history)


class CoolingMonitor:
    def __init__(self):
        self._temperatures: Dict[str, TemperatureReading] = {}
        self._history: Dict[str, List[TemperatureReading]] = defaultdict(list)
        self._alert_zones: List[str] = []

    def report_temperature(self, zone: str, temp_celsius: float) -> TemperatureReading:
        is_overheating = temp_celsius > 35.0
        reading = TemperatureReading(
            zone=zone,
            temp_celsius=temp_celsius,
            timestamp=datetime.now().isoformat(),
            is_overheating=is_overheating,
        )
        self._temperatures[zone] = reading
        self._history[zone].append(reading)
        if is_overheating and zone not in self._alert_zones:
            self._alert_zones.append(zone)
        elif not is_overheating and zone in self._alert_zones:
            self._alert_zones.remove(zone)
        return reading

    def is_overheating(self, zone: str, threshold: float = 35.0) -> bool:
        if zone not in self._temperatures:
            return False
        return self._temperatures[zone].temp_celsius > threshold

    def get_all_temperatures(self) -> Dict[str, float]:
        return {zone: reading.temp_celsius for zone, reading in self._temperatures.items()}

    def get_alert_zones(self) -> List[str]:
        return list(self._alert_zones)

    def get_zone_history(self, zone: str) -> List[TemperatureReading]:
        return list(self._history.get(zone, []))


class DisasterRecoveryPlan:
    def __init__(self):
        self._plans: Dict[DisasterType, RecoveryPlan] = {}
        self._active_plans: List[DisasterType] = []

    def register_plan(self, disaster_type: str, recovery_steps: List[str], rto_hours: float, rpo_hours: float) -> RecoveryPlan:
        dtype = DisasterType(disaster_type) if isinstance(disaster_type, str) else disaster_type
        plan = RecoveryPlan(
            disaster_type=dtype,
            recovery_steps=recovery_steps,
            rto_hours=rto_hours,
            rpo_hours=rpo_hours,
        )
        self._plans[dtype] = plan
        return plan

    def activate_plan(self, disaster_type: str) -> Optional[Dict[str, Any]]:
        dtype = DisasterType(disaster_type) if isinstance(disaster_type, str) else disaster_type
        if dtype not in self._plans:
            return None
        plan = self._plans[dtype]
        plan.status = RecoveryStatus.ACTIVE
        plan.activated_at = datetime.now().isoformat()
        if dtype not in self._active_plans:
            self._active_plans.append(dtype)
        return {
            "disaster_type": dtype.value,
            "recovery_steps": plan.recovery_steps,
            "rto_hours": plan.rto_hours,
            "rpo_hours": plan.rpo_hours,
            "activated_at": plan.activated_at,
        }

    def complete_plan(self, disaster_type: str) -> bool:
        dtype = DisasterType(disaster_type) if isinstance(disaster_type, str) else disaster_type
        if dtype not in self._plans:
            return False
        plan = self._plans[dtype]
        plan.status = RecoveryStatus.COMPLETED
        plan.completed_at = datetime.now().isoformat()
        if dtype in self._active_plans:
            self._active_plans.remove(dtype)
        return True

    def get_active_plans(self) -> List[Dict[str, Any]]:
        result = []
        for dtype in self._active_plans:
            plan = self._plans[dtype]
            result.append({
                "disaster_type": dtype.value,
                "recovery_steps": plan.recovery_steps,
                "rto_hours": plan.rto_hours,
                "rpo_hours": plan.rpo_hours,
                "status": plan.status.value,
                "activated_at": plan.activated_at,
            })
        return result

    def get_plan(self, disaster_type: str) -> Optional[RecoveryPlan]:
        dtype = DisasterType(disaster_type) if isinstance(disaster_type, str) else disaster_type
        return self._plans.get(dtype)

    def get_all_plans(self) -> Dict[str, RecoveryPlan]:
        return {dtype.value: plan for dtype, plan in self._plans.items()}


class EnvironmentalResilience:
    def __init__(self):
        self.power_monitor = PowerMonitor()
        self.cooling_monitor = CoolingMonitor()
        self.dr_plan = DisasterRecoveryPlan()
        self._event_log: List[EnvironmentalEvent] = []
        self._last_event: Optional[EnvironmentalEvent] = None
        self._recovery_attempts: int = 0
        self._successful_recoveries: int = 0

    def handle_environmental_event(self, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        event = EnvironmentalEvent(
            event_type=event_type,
            details=details,
            timestamp=datetime.now().isoformat(),
        )
        self._event_log.append(event)
        self._last_event = event

        handling_result = {
            "event_type": event_type,
            "timestamp": event.timestamp,
            "actions_taken": [],
            "status": "handled",
        }

        if event_type == "power_outage":
            self.power_monitor.report_power_status(False, details.get("ups_battery_pct"))
            handling_result["actions_taken"].append("power_status_recorded")
            if details.get("ups_battery_pct", 0) > 0:
                handling_result["actions_taken"].append("ups_active")
            activation = self.dr_plan.activate_plan("power_outage")
            if activation:
                handling_result["actions_taken"].append("dr_plan_activated")
                handling_result["recovery_steps"] = activation["recovery_steps"]

        elif event_type == "power_restored":
            self.power_monitor.report_power_status(True)
            handling_result["actions_taken"].append("power_restored")
            self.dr_plan.complete_plan("power_outage")

        elif event_type == "overheating":
            zone = details.get("zone", "default")
            temp = details.get("temperature", 0)
            self.cooling_monitor.report_temperature(zone, temp)
            handling_result["actions_taken"].append("temperature_recorded")
            if self.cooling_monitor.is_overheating(zone):
                handling_result["actions_taken"].append("overheat_alert")
                handling_result["status"] = "alert"
            activation = self.dr_plan.activate_plan("cooling_failure")
            if activation:
                handling_result["actions_taken"].append("cooling_dr_plan_activated")

        elif event_type == "temperature_update":
            zone = details.get("zone", "default")
            temp = details.get("temperature", 0)
            reading = self.cooling_monitor.report_temperature(zone, temp)
            handling_result["actions_taken"].append("temperature_updated")
            if reading.is_overheating:
                handling_result["actions_taken"].append("overheat_detected")
                handling_result["status"] = "alert"

        elif event_type in [dt.value for dt in DisasterType]:
            activation = self.dr_plan.activate_plan(event_type)
            if activation:
                handling_result["actions_taken"].append(f"dr_plan_activated_for_{event_type}")
                handling_result["recovery_steps"] = activation["recovery_steps"]
            else:
                handling_result["actions_taken"].append("no_dr_plan_found")
                handling_result["status"] = "no_plan"

        event.handled = True
        return handling_result

    def get_resilience_status(self) -> Dict[str, Any]:
        power_on = self.power_monitor.is_power_on()
        ups = self.power_monitor.get_ups_status()
        temps = self.cooling_monitor.get_all_temperatures()
        alert_zones = self.cooling_monitor.get_alert_zones()
        active_plans = self.dr_plan.get_active_plans()

        overall = "healthy"
        if not power_on and not ups.get("on_ups", False):
            overall = "critical"
        elif alert_zones or ups.get("on_ups", False):
            overall = "degraded"
        elif active_plans:
            overall = "recovering"

        return {
            "overall": overall,
            "power": {
                "on": power_on,
                "ups": ups,
                "outage_count": self.power_monitor.get_outage_count(),
            },
            "cooling": {
                "temperatures": temps,
                "alert_zones": alert_zones,
            },
            "disaster_recovery": {
                "active_plans": len(active_plans),
                "plans": active_plans,
            },
            "events": {
                "total": len(self._event_log),
                "recovery_attempts": self._recovery_attempts,
                "successful_recoveries": self._successful_recoveries,
            },
        }

    def perform_auto_recovery(self) -> Dict[str, Any]:
        if self._last_event is None:
            return {"status": "no_event", "message": "No event to recover from"}

        self._recovery_attempts += 1
        event = self._last_event
        result = {
            "status": "attempted",
            "event_type": event.event_type,
            "actions": [],
        }

        if event.event_type == "power_outage":
            result["actions"].append("checking_power_status")
            if self.power_monitor.is_power_on():
                result["actions"].append("power_restored_automatically")
                result["status"] = "recovered"
                self._successful_recoveries += 1
                self.dr_plan.complete_plan("power_outage")
                event.recovery_success = True
            else:
                result["actions"].append("power_still_off")
                result["status"] = "still_failed"

        elif event.event_type == "overheating":
            result["actions"].append("checking_temperatures")
            alert_zones = self.cooling_monitor.get_alert_zones()
            if not alert_zones:
                result["actions"].append("temperatures_normalized")
                result["status"] = "recovered"
                self._successful_recoveries += 1
                self.dr_plan.complete_plan("cooling_failure")
                event.recovery_success = True
            else:
                result["actions"].append(f"zones_still_overheating: {alert_zones}")
                result["status"] = "still_failed"

        elif event.event_type in [dt.value for dt in DisasterType]:
            plan = self.dr_plan.get_plan(event.event_type)
            if plan and plan.status == RecoveryStatus.ACTIVE:
                result["actions"].append(f"executing_recovery_steps_for_{event.event_type}")
                result["recovery_steps"] = plan.recovery_steps
                result["status"] = "recovery_in_progress"

        event.recovery_attempted = True
        return result

    def get_event_log(self) -> List[Dict[str, Any]]:
        return [
            {
                "event_type": e.event_type,
                "details": e.details,
                "timestamp": e.timestamp,
                "handled": e.handled,
                "recovery_attempted": e.recovery_attempted,
                "recovery_success": e.recovery_success,
            }
            for e in self._event_log
        ]


def main():
    print("=" * 60)
    print("EnvironmentalResilience 系統演示")
    print("=" * 60)

    er = EnvironmentalResilience()

    print("\n--- 1. PowerMonitor 測試 ---")
    er.power_monitor.report_power_status(True, ups_battery_pct=100.0)
    print(f"電源狀態: {'ON' if er.power_monitor.is_power_on() else 'OFF'}")
    print(f"UPS 狀態: {er.power_monitor.get_ups_status()}")

    print("\n--- 2. CoolingMonitor 測試 ---")
    er.cooling_monitor.report_temperature("server_room", 28.5)
    er.cooling_monitor.report_temperature("data_center", 32.0)
    er.cooling_monitor.report_temperature("network_closet", 38.2)
    print(f"所有溫度: {er.cooling_monitor.get_all_temperatures()}")
    print(f"server_room 過熱: {er.cooling_monitor.is_overheating('server_room')}")
    print(f"network_closet 過熱: {er.cooling_monitor.is_overheating('network_closet')}")
    print(f"警報區域: {er.cooling_monitor.get_alert_zones()}")

    print("\n--- 3. DisasterRecoveryPlan 測試 ---")
    er.dr_plan.register_plan(
        "power_outage",
        ["切換至 UPS", "通知運維團隊", "啟動備用發電機", "恢復主電源"],
        rto_hours=4.0,
        rpo_hours=1.0,
    )
    er.dr_plan.register_plan(
        "cooling_failure",
        ["啟動備用空調", "降低伺服器負載", "通知設施管理", "修復主冷卻系統"],
        rto_hours=2.0,
        rpo_hours=0.5,
    )
    er.dr_plan.register_plan(
        "flood",
        ["啟動防水閘門", "轉移設備至高層", "啟動異地備份", "通知緊急聯絡人"],
        rto_hours=24.0,
        rpo_hours=4.0,
    )
    print(f"已註冊計劃: {list(er.dr_plan.get_all_plans().keys())}")

    print("\n--- 4. EnvironmentalResilience 事件處理 ---")
    result = er.handle_environmental_event("power_outage", {"ups_battery_pct": 75.0})
    print(f"停電事件處理: {json.dumps(result, indent=2, ensure_ascii=False)}")

    result = er.handle_environmental_event("overheating", {"zone": "network_closet", "temperature": 38.2})
    print(f"過熱事件處理: {json.dumps(result, indent=2, ensure_ascii=False)}")

    print("\n--- 5. 系統狀態 ---")
    status = er.get_resilience_status()
    print(f"整體狀態: {status['overall']}")
    print(f"電源: {status['power']}")
    print(f"冷卻: {status['cooling']}")
    print(f"災難恢復: {status['disaster_recovery']}")

    print("\n--- 6. 自動恢復嘗試 ---")
    recovery = er.perform_auto_recovery()
    print(f"恢復結果: {json.dumps(recovery, indent=2, ensure_ascii=False)}")

    print("\n--- 7. 恢復電源後 ---")
    er.handle_environmental_event("power_restored", {})
    er.cooling_monitor.report_temperature("network_closet", 30.0)
    recovery = er.perform_auto_recovery()
    print(f"恢復結果: {json.dumps(recovery, indent=2, ensure_ascii=False)}")

    status = er.get_resilience_status()
    print(f"最終狀態: {status['overall']}")
    print(f"事件日誌: {len(er.get_event_log())} 條記錄")

    print("\n--- 8. 自然災害事件 ---")
    result = er.handle_environmental_event("flood", {"severity": "high", "location": "basement"})
    print(f"水災事件處理: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print(f"活躍計劃: {er.dr_plan.get_active_plans()}")

    print("\n" + "=" * 60)
    print("EnvironmentalResilience 系統演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
