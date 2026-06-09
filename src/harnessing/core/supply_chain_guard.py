from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class VendorHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class PackageSafety(str, Enum):
    SAFE = "safe"
    DEPRECATED = "deprecated"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


class GuardDecision(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


@dataclass
class VendorRecord:
    name: str
    endpoint: str
    fallback_endpoint: str | None = None
    status: VendorHealthStatus = VendorHealthStatus.UNKNOWN
    last_checked: str | None = None
    consecutive_failures: int = 0
    response_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PackageRecord:
    name: str
    version: str
    safety: PackageSafety = PackageSafety.UNKNOWN
    reason: str = ""
    checked_at: str | None = None


@dataclass
class LicenseRecord:
    name: str
    expiry_date: datetime
    vendor: str
    alert_sent: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardResult:
    decision: GuardDecision
    operation: str
    reasons: list[str] = field(default_factory=list)
    vendor_status: VendorHealthStatus | None = None
    package_issues: list[dict[str, Any]] = field(default_factory=list)
    license_valid: bool | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class VendorMonitor:
    def __init__(self, failure_threshold: int = 3, recovery_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self._vendors: dict[str, VendorRecord] = {}
        self._health_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._alerts: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def register_vendor(self, name: str, endpoint: str, fallback_endpoint: str | None = None) -> VendorRecord:
        record = VendorRecord(
            name=name,
            endpoint=endpoint,
            fallback_endpoint=fallback_endpoint,
        )
        self._vendors[name] = record
        self.logger.info("vendor_registered", extra={"vendor_name": name, "vendor_endpoint": endpoint})
        return record

    def check_vendor_health(self, vendor_name: str) -> dict[str, Any]:
        if vendor_name not in self._vendors:
            return {"vendor": vendor_name, "status": VendorHealthStatus.UNKNOWN.value, "error": "not_registered"}

        vendor = self._vendors[vendor_name]
        start = time.monotonic()
        is_reachable = self._ping_endpoint(vendor.endpoint)
        elapsed_ms = (time.monotonic() - start) * 1000

        if is_reachable:
            vendor.consecutive_failures = max(0, vendor.consecutive_failures - 1)
            vendor.response_time_ms = elapsed_ms
            if vendor.consecutive_failures == 0:
                vendor.status = VendorHealthStatus.HEALTHY
            else:
                vendor.status = VendorHealthStatus.DEGRADED
        else:
            vendor.consecutive_failures += 1
            if vendor.consecutive_failures >= self.failure_threshold:
                vendor.status = VendorHealthStatus.DOWN
                self._trigger_alert(vendor_name, "vendor_down", f"Vendor {vendor_name} is DOWN after {vendor.consecutive_failures} consecutive failures")
            else:
                vendor.status = VendorHealthStatus.DEGRADED
                self._trigger_alert(vendor_name, "vendor_degraded", f"Vendor {vendor_name} is DEGRADED ({vendor.consecutive_failures} failures)")

        vendor.last_checked = datetime.now().isoformat()

        health_entry = {
            "timestamp": vendor.last_checked,
            "status": vendor.status.value,
            "response_time_ms": elapsed_ms,
            "reachable": is_reachable,
        }
        self._health_history[vendor_name].append(health_entry)

        result = {
            "vendor": vendor_name,
            "status": vendor.status.value,
            "response_time_ms": round(elapsed_ms, 2),
            "consecutive_failures": vendor.consecutive_failures,
            "last_checked": vendor.last_checked,
            "fallback_available": vendor.fallback_endpoint is not None,
        }

        if not is_reachable and vendor.fallback_endpoint:
            fallback_reachable = self._ping_endpoint(vendor.fallback_endpoint)
            result["fallback_status"] = "reachable" if fallback_reachable else "unreachable"

        return result

    def get_vendor_status(self, name: str) -> dict[str, Any]:
        if name not in self._vendors:
            return {"name": name, "status": VendorHealthStatus.UNKNOWN.value, "error": "not_registered"}
        v = self._vendors[name]
        return {
            "name": v.name,
            "endpoint": v.endpoint,
            "fallback_endpoint": v.fallback_endpoint,
            "status": v.status.value,
            "last_checked": v.last_checked,
            "consecutive_failures": v.consecutive_failures,
            "response_time_ms": v.response_time_ms,
        }

    def get_all_vendors(self) -> dict[str, dict[str, Any]]:
        return {name: self.get_vendor_status(name) for name in self._vendors}

    def get_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._alerts[-limit:]

    def _ping_endpoint(self, endpoint: str) -> bool:
        try:
            from urllib.request import urlopen, Request
            from urllib.error import URLError
            req = Request(endpoint, method="HEAD")
            with urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def _trigger_alert(self, vendor_name: str, alert_type: str, message: str) -> None:
        alert = {
            "timestamp": datetime.now().isoformat(),
            "vendor": vendor_name,
            "type": alert_type,
            "alert_message": message,
        }
        self._alerts.append(alert)
        self.logger.warning("vendor_alert", extra={"alert_vendor": vendor_name, "alert_type": alert_type})


class DependencyScanner:
    def __init__(self):
        self._malicious_packages: dict[str, str] = {}
        self._deprecated_packages: dict[str, dict[str, str]] = {}
        self._version_conflicts: dict[str, list[str]] = defaultdict(list)
        self._scan_cache: dict[str, PackageRecord] = {}
        self._scan_history: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def add_malicious_list(self, packages: dict[str, str] | list[str]) -> None:
        if isinstance(packages, list):
            for pkg in packages:
                self._malicious_packages[pkg] = "known_malicious"
        else:
            self._malicious_packages.update(packages)
        self.logger.info("malicious_list_updated", extra={"count": len(self._malicious_packages)})

    def add_deprecated_list(self, packages: dict[str, dict[str, str]] | list[str]) -> None:
        if isinstance(packages, list):
            for pkg in packages:
                self._deprecated_packages[pkg] = {"reason": "deprecated", "replacement": "unknown"}
        else:
            self._deprecated_packages.update(packages)
        self.logger.info("deprecated_list_updated", extra={"count": len(self._deprecated_packages)})

    def add_version_conflict(self, package_name: str, conflicting_versions: list[str]) -> None:
        self._version_conflicts[package_name] = conflicting_versions
        self.logger.info("version_conflict_added", extra={"package": package_name, "versions": conflicting_versions})

    def scan_package(self, package_name: str, version: str = "") -> dict[str, Any]:
        cache_key = f"{package_name}@{version}" if version else package_name
        if cache_key in self._scan_cache:
            cached = self._scan_cache[cache_key]
            return {
                "package": package_name,
                "version": version,
                "safety": cached.safety.value,
                "reason": cached.reason,
                "checked_at": cached.checked_at,
                "from_cache": True,
            }

        safety = PackageSafety.SAFE
        reason = ""

        if package_name in self._malicious_packages:
            safety = PackageSafety.MALICIOUS
            reason = self._malicious_packages[package_name]
        elif package_name in self._deprecated_packages:
            safety = PackageSafety.DEPRECATED
            dep_info = self._deprecated_packages[package_name]
            reason = dep_info.get("reason", "deprecated")
            replacement = dep_info.get("replacement", "")
            if replacement:
                reason += f" (replace with: {replacement})"

        if package_name in self._version_conflicts:
            conflicts = self._version_conflicts[package_name]
            if safety == PackageSafety.SAFE:
                safety = PackageSafety.DEPRECATED
                reason = f"version conflict: {', '.join(conflicts)}"
            else:
                reason += f" | version conflict: {', '.join(conflicts)}"

        now = datetime.now().isoformat()
        record = PackageRecord(
            name=package_name,
            version=version,
            safety=safety,
            reason=reason,
            checked_at=now,
        )
        self._scan_cache[cache_key] = record

        scan_result = {
            "package": package_name,
            "version": version,
            "safety": safety.value,
            "reason": reason,
            "checked_at": now,
            "from_cache": False,
        }
        self._scan_history.append(scan_result)

        self.logger.info("package_scanned", extra={"package": package_name, "safety": safety.value})
        return scan_result

    def scan_packages(self, packages: list[dict[str, str]]) -> list[dict[str, Any]]:
        results = []
        for pkg in packages:
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            results.append(self.scan_package(name, version))
        return results

    def get_scan_summary(self) -> dict[str, Any]:
        safety_counts = defaultdict(int)
        for record in self._scan_cache.values():
            safety_counts[record.safety.value] += 1

        return {
            "total_scanned": len(self._scan_cache),
            "malicious_count": safety_counts.get(PackageSafety.MALICIOUS.value, 0),
            "deprecated_count": safety_counts.get(PackageSafety.DEPRECATED.value, 0),
            "safe_count": safety_counts.get(PackageSafety.SAFE.value, 0),
            "unknown_count": safety_counts.get(PackageSafety.UNKNOWN.value, 0),
            "version_conflicts": len(self._version_conflicts),
            "malicious_list_size": len(self._malicious_packages),
            "deprecated_list_size": len(self._deprecated_packages),
        }


class LicenseTracker:
    def __init__(self, default_alert_days: int = 30):
        self.default_alert_days = default_alert_days
        self._licenses: dict[str, LicenseRecord] = {}
        self._alerts: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def register_license(self, name: str, expiry_date: datetime, vendor: str) -> LicenseRecord:
        record = LicenseRecord(
            name=name,
            expiry_date=expiry_date,
            vendor=vendor,
        )
        self._licenses[name] = record
        self.logger.info("license_registered", extra={"license_name": name, "license_vendor": vendor, "license_expiry": expiry_date.isoformat()})
        return record

    def check_expiring(self, days_ahead: int = 30) -> list[dict[str, Any]]:
        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)
        expiring = []

        for name, record in self._licenses.items():
            if record.expiry_date <= cutoff:
                days_remaining = (record.expiry_date - now).days
                is_expired = days_remaining <= 0

                entry = {
                    "name": name,
                    "vendor": record.vendor,
                    "expiry_date": record.expiry_date.isoformat(),
                    "days_remaining": days_remaining,
                    "expired": is_expired,
                    "urgency": self._calculate_urgency(days_remaining),
                }

                if not record.alert_sent and days_remaining <= self.default_alert_days:
                    self._trigger_expiry_alert(name, days_remaining, record.vendor)
                    record.alert_sent = True

                expiring.append(entry)

        expiring.sort(key=lambda x: x["days_remaining"])
        return expiring

    def is_license_valid(self, name: str) -> bool:
        if name not in self._licenses:
            return False
        return datetime.now() < self._licenses[name].expiry_date

    def get_license_info(self, name: str) -> dict[str, Any]:
        if name not in self._licenses:
            return {"name": name, "valid": False, "error": "not_found"}
        record = self._licenses[name]
        now = datetime.now()
        days_remaining = (record.expiry_date - now).days
        return {
            "name": name,
            "vendor": record.vendor,
            "expiry_date": record.expiry_date.isoformat(),
            "valid": now < record.expiry_date,
            "days_remaining": days_remaining,
            "alert_sent": record.alert_sent,
        }

    def get_all_licenses(self) -> list[dict[str, Any]]:
        return [self.get_license_info(name) for name in self._licenses]

    def get_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._alerts[-limit:]

    def _calculate_urgency(self, days_remaining: int) -> str:
        if days_remaining <= 0:
            return "expired"
        elif days_remaining <= 7:
            return "critical"
        elif days_remaining <= 14:
            return "high"
        elif days_remaining <= 30:
            return "medium"
        return "low"

    def _trigger_expiry_alert(self, name: str, days_remaining: int, vendor: str) -> None:
        alert = {
            "timestamp": datetime.now().isoformat(),
            "license": name,
            "vendor": vendor,
            "days_remaining": days_remaining,
            "urgency": self._calculate_urgency(days_remaining),
            "alert_message": f"License {name} (vendor: {vendor}) expires in {days_remaining} days",
        }
        self._alerts.append(alert)
        self.logger.warning("license_expiry_alert", extra={"alert_license": name, "alert_vendor": vendor, "alert_days": days_remaining})


class SupplyChainGuard:
    def __init__(self, data_path: str | Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data" / "supply_chain"
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        self.vendor_monitor = VendorMonitor()
        self.dependency_scanner = DependencyScanner()
        self.license_tracker = LicenseTracker()
        self._guard_history: list[GuardResult] = []
        self._blocked_operations: list[GuardResult] = []
        self.logger = logging.getLogger(__name__)

    def guard_operation(
        self,
        operation_name: str,
        vendor: str | None = None,
        packages: list[dict[str, str]] | None = None,
        license_name: str | None = None,
    ) -> GuardResult:
        reasons: list[str] = []
        vendor_status: VendorHealthStatus | None = None
        package_issues: list[dict[str, Any]] = []
        license_valid: bool | None = None

        if vendor:
            health = self.vendor_monitor.check_vendor_health(vendor)
            vendor_status = VendorHealthStatus(health["status"])
            if vendor_status == VendorHealthStatus.DOWN:
                fallback = health.get("fallback_status")
                if fallback != "reachable":
                    reasons.append(f"Vendor {vendor} is DOWN with no reachable fallback")
                else:
                    reasons.append(f"Vendor {vendor} is DOWN but fallback is reachable (degraded mode)")
            elif vendor_status == VendorHealthStatus.DEGRADED:
                reasons.append(f"Vendor {vendor} is DEGRADED")

        if packages:
            for pkg in packages:
                name = pkg.get("name", "")
                version = pkg.get("version", "")
                result = self.dependency_scanner.scan_package(name, version)
                if result["safety"] == PackageSafety.MALICIOUS.value:
                    reasons.append(f"Package {name}@{version} is MALICIOUS: {result['reason']}")
                    package_issues.append(result)
                elif result["safety"] == PackageSafety.DEPRECATED.value:
                    reasons.append(f"Package {name}@{version} is DEPRECATED: {result['reason']}")
                    package_issues.append(result)

        if license_name:
            license_valid = self.license_tracker.is_license_valid(license_name)
            if not license_valid:
                reasons.append(f"License {license_name} is invalid or expired")

        decision = GuardDecision.BLOCKED if reasons else GuardDecision.ALLOWED

        guard_result = GuardResult(
            decision=decision,
            operation=operation_name,
            reasons=reasons,
            vendor_status=vendor_status,
            package_issues=package_issues,
            license_valid=license_valid,
        )

        self._guard_history.append(guard_result)
        if decision == GuardDecision.BLOCKED:
            self._blocked_operations.append(guard_result)

        self.logger.info(
            "guard_operation",
            extra={"operation": operation_name, "decision": decision.value, "reasons": reasons},
        )

        return guard_result

    def get_supply_chain_status(self) -> dict[str, Any]:
        vendor_statuses = self.vendor_monitor.get_all_vendors()
        healthy_vendors = sum(1 for v in vendor_statuses.values() if v.get("status") == VendorHealthStatus.HEALTHY.value)
        total_vendors = len(vendor_statuses)

        scan_summary = self.dependency_scanner.get_scan_summary()

        expiring_licenses = self.license_tracker.check_expiring(days_ahead=30)
        expired_count = sum(1 for lic in expiring_licenses if lic.get("expired", False))

        all_licenses = self.license_tracker.get_all_licenses()
        valid_licenses = sum(1 for lic in all_licenses if lic.get("valid", False))
        total_licenses = len(all_licenses)

        overall_healthy = (
            healthy_vendors == total_vendors
            and scan_summary["malicious_count"] == 0
            and expired_count == 0
        )

        return {
            "overall_status": "healthy" if overall_healthy else "at_risk",
            "vendors": {
                "total": total_vendors,
                "healthy": healthy_vendors,
                "degraded": sum(1 for v in vendor_statuses.values() if v.get("status") == VendorHealthStatus.DEGRADED.value),
                "down": sum(1 for v in vendor_statuses.values() if v.get("status") == VendorHealthStatus.DOWN.value),
                "details": vendor_statuses,
            },
            "dependencies": scan_summary,
            "licenses": {
                "total": total_licenses,
                "valid": valid_licenses,
                "expired": expired_count,
                "expiring_soon": len(expiring_licenses) - expired_count,
                "details": all_licenses,
            },
            "guard_stats": {
                "total_operations": len(self._guard_history),
                "blocked_operations": len(self._blocked_operations),
                "allowed_operations": len(self._guard_history) - len(self._blocked_operations),
            },
            "timestamp": datetime.now().isoformat(),
        }

    def get_guard_history(self, limit: int = 100) -> list[dict[str, Any]]:
        results = self._guard_history[-limit:]
        return [
            {
                "operation": r.operation,
                "decision": r.decision.value,
                "reasons": r.reasons,
                "vendor_status": r.vendor_status.value if r.vendor_status else None,
                "license_valid": r.license_valid,
                "timestamp": r.timestamp,
            }
            for r in results
        ]


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=" * 60)
    print("SupplyChainGuard Demo")
    print("=" * 60)

    guard = SupplyChainGuard()

    print("\n--- 1. VendorMonitor Demo ---")
    guard.vendor_monitor.register_vendor("openai_api", "https://api.openai.com", "https://api.openai.com/fallback")
    guard.vendor_monitor.register_vendor("anthropic_api", "https://api.anthropic.com")
    guard.vendor_monitor.register_vendor("local_ollama", "http://localhost:11434")

    for name in ["openai_api", "anthropic_api", "local_ollama"]:
        health = guard.vendor_monitor.check_vendor_health(name)
        print(f"  {name}: status={health['status']}, response_time={health['response_time_ms']:.1f}ms")

    status = guard.vendor_monitor.get_vendor_status("openai_api")
    print(f"  openai_api detail: {json.dumps(status, indent=2, default=str)}")

    print("\n--- 2. DependencyScanner Demo ---")
    guard.dependency_scanner.add_malicious_list({
        "evil-package": "known_malware_exfiltrates_data",
        "typosquat-reqeusts": "typosquatting_attack",
    })
    guard.dependency_scanner.add_deprecated_list({
        "old-lib": {"reason": "security_vulnerability", "replacement": "new-lib"},
        "legacy-sdk": {"reason": "end_of_life", "replacement": "modern-sdk"},
    })
    guard.dependency_scanner.add_version_conflict("conflicting-pkg", ["1.0.0", "2.0.0"])

    test_packages = [
        {"name": "requests", "version": "2.31.0"},
        {"name": "evil-package", "version": "1.0.0"},
        {"name": "old-lib", "version": "0.9.0"},
        {"name": "conflicting-pkg", "version": "1.5.0"},
    ]

    for pkg in test_packages:
        result = guard.dependency_scanner.scan_package(pkg["name"], pkg["version"])
        print(f"  {pkg['name']}@{pkg['version']}: safety={result['safety']}, reason={result['reason']}")

    summary = guard.dependency_scanner.get_scan_summary()
    print(f"  Scan summary: {json.dumps(summary, indent=2)}")

    print("\n--- 3. LicenseTracker Demo ---")
    now = datetime.now()
    guard.license_tracker.register_license("openai_api_key", now + timedelta(days=90), "openai")
    guard.license_tracker.register_license("anthropic_api_key", now + timedelta(days=5), "anthropic")
    guard.license_tracker.register_license("expired_cert", now - timedelta(days=10), "internal")

    for name in ["openai_api_key", "anthropic_api_key", "expired_cert"]:
        info = guard.license_tracker.get_license_info(name)
        print(f"  {name}: valid={info['valid']}, days_remaining={info['days_remaining']}")

    expiring = guard.license_tracker.check_expiring(days_ahead=30)
    print(f"  Expiring within 30 days: {len(expiring)}")
    for lic in expiring:
        print(f"    - {lic['name']}: {lic['days_remaining']} days remaining ({lic['urgency']})")

    alerts = guard.license_tracker.get_alerts()
    print(f"  License alerts: {len(alerts)}")

    print("\n--- 4. SupplyChainGuard guard_operation Demo ---")

    result1 = guard.guard_operation(
        operation_name="safe_deploy",
        vendor="local_ollama",
        packages=[{"name": "requests", "version": "2.31.0"}],
        license_name="openai_api_key",
    )
    print(f"  safe_deploy: decision={result1.decision.value}, reasons={result1.reasons}")

    result2 = guard.guard_operation(
        operation_name="risky_deploy",
        vendor="openai_api",
        packages=[{"name": "evil-package", "version": "1.0.0"}],
        license_name="expired_cert",
    )
    print(f"  risky_deploy: decision={result2.decision.value}, reasons={result2.reasons}")

    result3 = guard.guard_operation(
        operation_name="partial_risk",
        packages=[{"name": "old-lib", "version": "0.9.0"}],
    )
    print(f"  partial_risk: decision={result3.decision.value}, reasons={result3.reasons}")

    print("\n--- 5. Supply Chain Status ---")
    status = guard.get_supply_chain_status()
    print(json.dumps(status, indent=2, default=str))

    print("\n--- 6. Guard History ---")
    history = guard.get_guard_history()
    for entry in history:
        print(f"  {entry['operation']}: {entry['decision']} | reasons={entry['reasons']}")

    print("\n" + "=" * 60)
    print("SupplyChainGuard Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
