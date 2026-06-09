import os
import re
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class MasterSelfMaintenanceScanner:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.projects_path = os.path.join(root_path, "projects")
        self.agents_md_path = os.path.join(root_path, "AGENTS.md")
        self.decision_log_path = os.path.join(root_path, "data", "decision-log.md")
        self.error_rules_path = os.path.join(root_path, "data", "error-rules.yaml")
        self.knowledge_base_path = os.path.join(root_path, "docs", "knowledge-base")

    def scan_all_subprojects(self) -> List[Dict]:
        subprojects = []
        if not os.path.exists(self.projects_path):
            return subprojects

        for item in os.listdir(self.projects_path):
            item_path = os.path.join(self.projects_path, item)
            if os.path.isdir(item_path):
                agents_md = os.path.join(item_path, "AGENTS.md")
                tasks_md = os.path.join(item_path, "tasks.md")
                
                subproject_info = {
                    "name": item,
                    "path": item_path,
                    "has_agents_md": os.path.exists(agents_md),
                    "has_tasks_md": os.path.exists(tasks_md),
                    "agents_md_path": agents_md if os.path.exists(agents_md) else None,
                    "tasks_md_path": tasks_md if os.path.exists(tasks_md) else None,
                    "last_modified": self._get_last_modified(item_path),
                    "status": self._detect_status(item_path, agents_md),
                    "pain_points": [],
                    "progress": None,
                }

                if subproject_info["has_agents_md"]:
                    content = self._read_file(agents_md)
                    if content:
                        subproject_info["pain_points"] = self.extract_pain_points(content)
                        subproject_info["progress"] = self._extract_progress(content)

                subprojects.append(subproject_info)

        subprojects.sort(key=lambda x: x.get("last_modified") or "", reverse=True)
        return subprojects

    def extract_pain_points(self, agents_content: str) -> List[str]:
        pain_points = []
        
        patterns = [
            r'痛點[:：]\s*(.+?)(?:\n|$)',
            r'Pain\s*point[:：]\s*(.+?)(?:\n|$)',
            r'問題[:：]\s*(.+?)(?:\n|$)',
            r'Issue[:：]\s*(.+?)(?:\n|$)',
            r'困難[:：]\s*(.+?)(?:\n|$)',
            r'Difficulty[:：]\s*(.+?)(?:\n|$)',
            r'-\s*\[(?:x|\s)\]\s*(.+?)(?:\n|$)',
            r'⚠️\s*(.+?)(?:\n|$)',
            r'❌\s*(.+?)(?:\n|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, agents_content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                point = match.strip()
                if point and len(point) > 5 and point not in pain_points:
                    pain_points.append(point)

        pain_point_section = re.search(
            r'(?:痛點|Pain\s*Points|困難|Difficulties)[:：]?\s*\n((?:[-*]\s*.+\n?)+)',
            agents_content,
            re.IGNORECASE | re.MULTILINE
        )
        if pain_point_section:
            items = re.findall(r'[-*]\s*(.+?)(?:\n|$)', pain_point_section.group(1))
            for item in items:
                point = item.strip()
                if point and point not in pain_points:
                    pain_points.append(point)

        return pain_points[:50]

    def sync_error_rules(self) -> Dict:
        result = {
            "total_rules": 0,
            "verified_rules": 0,
            "unverified_rules": 0,
            "rules_by_project": {},
            "rules_by_type": {},
            "unverified_list": [],
            "last_updated": None,
        }

        if not os.path.exists(self.error_rules_path):
            return result

        try:
            with open(self.error_rules_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if content.strip():
                rules_data = yaml.safe_load(content)
                if rules_data:
                    # Handle both formats: direct list or {"rules": [...]}
                    rules_list = rules_data
                    if isinstance(rules_data, dict) and "rules" in rules_data:
                        rules_list = rules_data["rules"]
                    if not isinstance(rules_list, list):
                        rules_list = []
                    result["total_rules"] = len(rules_list)

                    for rule in rules_list:
                        if isinstance(rule, dict):
                            is_verified = rule.get('verified', False)
                            if is_verified:
                                result["verified_rules"] += 1
                            else:
                                result["unverified_rules"] += 1
                                result["unverified_list"].append({
                                    "id": rule.get('id', 'unknown'),
                                    "error": rule.get('error', 'unknown'),
                                    "project": rule.get('project', 'unknown'),
                                })

                            project = rule.get('project', 'unknown')
                            result["rules_by_project"][project] = result["rules_by_project"].get(project, 0) + 1

                            error_type = rule.get('error_type', 'unknown')
                            result["rules_by_type"][error_type] = result["rules_by_type"].get(error_type, 0) + 1

            result["last_updated"] = datetime.fromtimestamp(
                os.path.getmtime(self.error_rules_path)
            ).isoformat()

        except Exception as e:
            result["error"] = str(e)

        return result

    def update_master_agents_md(self, scan_results: Dict) -> bool:
        if not os.path.exists(self.agents_md_path):
            return False

        try:
            content = self._read_file(self.agents_md_path)
            if not content:
                return False

            new_section = self._generate_subproject_section(scan_results)
            
            # Split content into lines and process without regex
            lines = content.split('\n')
            filtered_lines = []
            skip_mode = False
            
            for i, line in enumerate(lines):
                if line.strip() == '## 子項目索引':
                    skip_mode = True
                    continue
                if skip_mode and line.strip().startswith('## '):
                    skip_mode = False
                
                if not skip_mode:
                    filtered_lines.append(line)
            
            content = '\n'.join(filtered_lines)
            
            # Insert new section after first title
            if content.startswith('# Harnessing — AGENTS.md'):
                first_line_end = content.find('\n')
                if first_line_end == -1:
                    content = content + '\n\n' + new_section
                else:
                    content = content[:first_line_end] + '\n\n' + new_section + content[first_line_end:]
            else:
                content = new_section + '\n\n' + content

            with open(self.agents_md_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        except Exception as e:
            print(f"Error updating AGENTS.md: {e}")
            return False

    def generate_status_report(self) -> str:
        scan_results = self.run_full_scan()
        
        report_lines = [
            "# Master Self-Maintenance Scanner Report",
            f"\n**Generated**: {datetime.now().isoformat()}",
            f"\n---\n",
        ]

        report_lines.append("## 子項目狀態摘要\n")
        for sp in scan_results["subprojects"]:
            status_icon = {"active": "✅", "inactive": "⏸️", "unknown": "❓"}.get(sp["status"], "❓")
            report_lines.append(
                f"- {status_icon} **{sp['name']}** — {sp['status']} "
                f"({len(sp['pain_points'])} 痛點)"
            )

        report_lines.append(f"\n**統計**: {len(scan_results['subprojects'])} 個子項目\n")

        all_pain_points = scan_results["pain_points"]
        if all_pain_points:
            report_lines.append("## 所有痛點清單\n")
            for i, point in enumerate(all_pain_points[:30], 1):
                report_lines.append(f"{i}. {point}")
            if len(all_pain_points) > 30:
                report_lines.append(f"\n... 還有 {len(all_pain_points) - 30} 個痛點")

        error_rules = scan_results["error_rules"]
        report_lines.append("\n## 錯誤規則統計\n")
        report_lines.append(f"- 總規則數: {error_rules['total_rules']}")
        report_lines.append(f"- 已驗證: {error_rules['verified_rules']}")
        report_lines.append(f"- 未驗證: {error_rules['unverified_rules']}")
        
        if error_rules["unverified_list"]:
            report_lines.append("\n### 未驗證規則\n")
            for rule in error_rules["unverified_list"][:10]:
                report_lines.append(f"- {rule['id']}: {rule['error']}")

        next_actions = scan_results["next_actions"]
        if next_actions:
            report_lines.append("\n## 下步行動建議\n")
            for action in next_actions:
                report_lines.append(f"- {action}")

        return "\n".join(report_lines)

    def run_full_scan(self) -> Dict:
        subprojects = self.scan_all_subprojects()
        error_rules = self.sync_error_rules()
        
        all_pain_points = []
        for sp in subprojects:
            all_pain_points.extend(sp["pain_points"])
        
        unique_pain_points = list(dict.fromkeys(all_pain_points))

        next_actions = self._generate_next_actions(subprojects, error_rules)

        scan_results = {
            "subprojects": subprojects,
            "pain_points": unique_pain_points,
            "error_rules": error_rules,
            "next_actions": next_actions,
            "scan_timestamp": datetime.now().isoformat(),
        }

        return scan_results

    def _read_file(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def _get_last_modified(self, dir_path: str) -> Optional[str]:
        try:
            latest_time = 0
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    if f.endswith(('.py', '.md', '.yaml', '.json')):
                        file_path = os.path.join(root, f)
                        mtime = os.path.getmtime(file_path)
                        if mtime > latest_time:
                            latest_time = mtime
            
            if latest_time > 0:
                return datetime.fromtimestamp(latest_time).strftime("%Y-%m-%d")
        except Exception:
            pass
        return None

    def _detect_status(self, dir_path: str, agents_md_path: str) -> str:
        if os.path.exists(agents_md_path):
            content = self._read_file(agents_md_path)
            if content:
                if "✅" in content or "完成" in content or "Completed" in content:
                    return "active"
                if "🔄" in content or "進行中" in content or "In Progress" in content:
                    return "active"
                if "⏸️" in content or "暫停" in content or "Paused" in content:
                    return "inactive"
        
        py_files = list(Path(dir_path).rglob("*.py"))
        if py_files:
            return "active"
        
        return "unknown"

    def _extract_progress(self, content: str) -> Optional[str]:
        patterns = [
            r'進度[:：]\s*(.+?)(?:\n|$)',
            r'Progress[:：]\s*(.+?)(?:\n|$)',
            r'當前進度[:：]\s*(.+?)(?:\n|$)',
            r'狀態[:：]\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def _generate_subproject_section(self, scan_results: Dict) -> str:
        lines = [
            "## 子項目索引",
            f"\n> 自動掃描 `projects/` 目錄生成，最後更新：{datetime.now().strftime('%Y-%m-%d')}\n",
            "\n| 子項目 | 狀態 | 進度 | 最後更新 | AGENTS.md |",
            "|--------|------|------|----------|-----------|",
        ]

        for sp in scan_results["subprojects"]:
            status_icon = {"active": "✅", "inactive": "⏸️", "unknown": "❓"}.get(sp["status"], "❓")
            progress = sp.get("progress") or "-"
            last_mod = sp.get("last_modified") or "-"
            agents_link = f"[AGENTS.md]({sp['agents_md_path']})" if sp["has_agents_md"] else "—"
            
            lines.append(
                f"| {sp['name']} | {status_icon} {sp['status']} | {progress} | {last_mod} | {agents_link} |"
            )

        stats = {
            "total": len(scan_results["subprojects"]),
            "with_agents": sum(1 for sp in scan_results["subprojects"] if sp["has_agents_md"]),
            "with_tasks": sum(1 for sp in scan_results["subprojects"] if sp["has_tasks_md"]),
        }
        
        lines.append(f"**統計**：{stats['total']} 個子項目（{stats['with_agents']} 個有 AGENTS.md，{stats['with_tasks']} 個有 tasks.md）\n")
        
        return "\n".join(lines)

    def _generate_next_actions(self, subprojects: List[Dict], error_rules: Dict) -> List[str]:
        actions = []

        for sp in subprojects:
            if not sp["has_agents_md"] and sp["status"] == "active":
                actions.append(f"為 {sp['name']} 創建 AGENTS.md")
            
            if len(sp["pain_points"]) > 5:
                actions.append(f"處理 {sp['name']} 嘅 {len(sp['pain_points'])} 個痛點")

        if error_rules["unverified_rules"] > 0:
            actions.append(f"驗證 {error_rules['unverified_rules']} 條未驗證嘅錯誤規則")

        inactive_projects = [sp for sp in subprojects if sp["status"] == "inactive"]
        if inactive_projects:
            actions.append(f"檢查 {len(inactive_projects)} 個非活躍項目嘅狀態")

        return actions[:10]

    def scan_knowledge_base(self) -> Dict:
        result = {
            "total_files": 0,
            "files": [],
            "last_updated": None,
        }

        if not os.path.exists(self.knowledge_base_path):
            return result

        try:
            kb_files = list(Path(self.knowledge_base_path).glob("*.md"))
            result["total_files"] = len(kb_files)

            for kb_file in sorted(kb_files):
                stat = kb_file.stat()
                result["files"].append({
                    "name": kb_file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                })

            if result["files"]:
                latest = max(result["files"], key=lambda x: x["modified"])
                result["last_updated"] = latest["modified"]

        except Exception:
            pass

        return result

    def get_decision_log_summary(self) -> Dict:
        result = {
            "total_decisions": 0,
            "recent_decisions": [],
            "decisions_by_status": {"pending": 0, "success": 0, "failure": 0},
        }

        if not os.path.exists(self.decision_log_path):
            return result

        try:
            content = self._read_file(self.decision_log_path)
            if content:
                decision_pattern = r'D-(\d+).*?(?:結果|Outcome)[:：]?\s*(\w+)'
                matches = re.findall(decision_pattern, content, re.IGNORECASE)
                
                result["total_decisions"] = len(matches)
                
                for dec_id, status in matches[-10:]:
                    result["recent_decisions"].append({"id": f"D-{dec_id}", "status": status})
                    status_lower = status.lower()
                    if status_lower in result["decisions_by_status"]:
                        result["decisions_by_status"][status_lower] += 1

        except Exception:
            pass

        return result
