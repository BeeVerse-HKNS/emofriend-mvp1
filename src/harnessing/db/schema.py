from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "harnessing.db"

SCHEMA = {
    "decisions": {
        "id": str,
        "category": str,
        "decision": str,
        "rationale": str,
        "created_at": str,
        "status": str,
    },
    "knowledge_entries": {
        "id": str,
        "topic": str,
        "content": str,
        "source": str,
        "category": str,
        "created_at": str,
        "updated_at": str,
    },
    "learning_logs": {
        "id": str,
        "session_id": str,
        "topic": str,
        "key_insights": str,
        "questions": str,
        "created_at": str,
    },
    "feedback_records": {
        "id": str,
        "agent_id": str,
        "task": str,
        "error_type": str,
        "error_detail": str,
        "rule_created": str,
        "rule_id": str,
        "created_at": str,
    },
    "upload_analytics": {
        "id": str,
        "timestamp": str,
        "platform": str,
        "publish_time": str,
        "content_type": str,
        "views_24h": str,
        "watch_time_hours": str,
        "ctr": str,
        "engagement_rate": str,
        "composite_score": str,
    },
    "optimal_times": {
        "id": str,
        "platform": str,
        "day_of_week": str,
        "hour": str,
        "content_type": str,
        "composite_score": str,
        "sample_count": str,
        "updated_at": str,
    },
}
