from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, List

CONFIDENCE_VERIFIED = "✅ VERIFIED"
CONFIDENCE_RESEARCHED = "🔍 RESEARCHED"
CONFIDENCE_INFERRED = "⚠️ INFERRED"
CONFIDENCE_UNCERTAIN = "❌ UNCERTAIN"

DEFAULT_TIMEOUT = 5

SERVICES: List[Dict[str, str]] = [
    {
        "name": "Streamlit Docs",
        "url": "https://docs.streamlit.io",
        "category": "streamlit_official",
        "confidence_if_ok": CONFIDENCE_RESEARCHED,
        "confidence_if_fail": CONFIDENCE_INFERRED,
        "note": "Official documentation site",
    },
    {
        "name": "Streamlit Official",
        "url": "https://streamlit.io",
        "category": "streamlit_official",
        "confidence_if_ok": CONFIDENCE_RESEARCHED,
        "confidence_if_fail": CONFIDENCE_INFERRED,
        "note": "Official website",
    },
    {
        "name": "Streamlit Community Cloud",
        "url": "https://streamlit.app",
        "category": "streamlit_cloud",
        "confidence_if_ok": CONFIDENCE_RESEARCHED,
        "confidence_if_fail": CONFIDENCE_INFERRED,
        "note": "Likely blocked by GFW",
    },
    {
        "name": "Tsinghua PyPI Mirror",
        "url": "https://pypi.tuna.tsinghua.edu.cn",
        "category": "pypi_mirror",
        "confidence_if_ok": CONFIDENCE_VERIFIED,
        "confidence_if_fail": CONFIDENCE_UNCERTAIN,
        "note": "China domestic mirror",
    },
    {
        "name": "Aliyun PyPI Mirror",
        "url": "https://mirrors.aliyun.com/pypi",
        "category": "pypi_mirror",
        "confidence_if_ok": CONFIDENCE_VERIFIED,
        "confidence_if_fail": CONFIDENCE_UNCERTAIN,
        "note": "China domestic mirror",
    },
    {
        "name": "Douban PyPI Mirror",
        "url": "https://pypi.doubanio.com",
        "category": "pypi_mirror",
        "confidence_if_ok": CONFIDENCE_VERIFIED,
        "confidence_if_fail": CONFIDENCE_UNCERTAIN,
        "note": "China domestic mirror",
    },
]


@dataclass
class ServiceCheckResult:
    name: str
    url: str
    category: str
    status: str
    response_time: float
    confidence_level: str
    note: str
    error: str | None = None


def check_service(
    name: str,
    url: str,
    category: str,
    confidence_if_ok: str,
    confidence_if_fail: str,
    note: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> ServiceCheckResult:
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "HarnessingChinaChecker/1.0"})
        with urllib.request.urlopen(req, timeout=timeout):
            elapsed = round(time.monotonic() - start, 3)
            return ServiceCheckResult(
                name=name,
                url=url,
                category=category,
                status="ok",
                response_time=elapsed,
                confidence_level=confidence_if_ok,
                note=note,
            )
    except urllib.error.HTTPError as exc:
        elapsed = round(time.monotonic() - start, 3)
        return ServiceCheckResult(
            name=name,
            url=url,
            category=category,
            status="http_error",
            response_time=elapsed,
            confidence_level=confidence_if_fail,
            note=note,
            error=f"HTTP {exc.code}",
        )
    except urllib.error.URLError as exc:
        elapsed = round(time.monotonic() - start, 3)
        return ServiceCheckResult(
            name=name,
            url=url,
            category=category,
            status="url_error",
            response_time=elapsed,
            confidence_level=confidence_if_fail,
            note=note,
            error=str(exc.reason),
        )
    except TimeoutError:
        elapsed = round(time.monotonic() - start, 3)
        return ServiceCheckResult(
            name=name,
            url=url,
            category=category,
            status="timeout",
            response_time=elapsed,
            confidence_level=confidence_if_fail,
            note=note,
            error="Connection timed out",
        )
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 3)
        return ServiceCheckResult(
            name=name,
            url=url,
            category=category,
            status="error",
            response_time=elapsed,
            confidence_level=confidence_if_fail,
            note=note,
            error=str(exc),
        )


def check_all_services(timeout: int = DEFAULT_TIMEOUT) -> List[ServiceCheckResult]:
    results: List[ServiceCheckResult] = []
    for svc in SERVICES:
        result = check_service(
            name=svc["name"],
            url=svc["url"],
            category=svc["category"],
            confidence_if_ok=svc["confidence_if_ok"],
            confidence_if_fail=svc["confidence_if_fail"],
            note=svc["note"],
            timeout=timeout,
        )
        results.append(result)
    return results


def results_to_dict(results: List[ServiceCheckResult]) -> List[Dict[str, object]]:
    return [
        {
            "name": r.name,
            "url": r.url,
            "category": r.category,
            "status": r.status,
            "response_time": r.response_time,
            "confidence_level": r.confidence_level,
            "note": r.note,
            "error": r.error,
        }
        for r in results
    ]


def format_report(results: List[ServiceCheckResult]) -> str:
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("Streamlit China Accessibility Checker")
    lines.append("=" * 70)
    lines.append("")

    categories: Dict[str, List[ServiceCheckResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    for cat, cat_results in categories.items():
        lines.append(f"[{cat}]")
        for r in cat_results:
            status_icon = "🟢" if r.status == "ok" else "🔴"
            lines.append(
                f"  {status_icon} {r.name}: {r.status} "
                f"({r.response_time}s) {r.confidence_level}"
            )
            if r.error:
                lines.append(f"     Error: {r.error}")
            lines.append(f"     URL: {r.url}")
        lines.append("")

    ok_count = sum(1 for r in results if r.status == "ok")
    lines.append(f"Summary: {ok_count}/{len(results)} services reachable")
    lines.append("=" * 70)
    return "\n".join(lines)


def main() -> None:
    results = check_all_services()
    report = format_report(results)
    print(report)

    structured = results_to_dict(results)
    print("\nStructured Results:")
    for item in structured:
        print(f"  {item}")


if __name__ == "__main__":
    main()
