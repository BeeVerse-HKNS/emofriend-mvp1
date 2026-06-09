from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from harnessing.db.vector_store import VECTOR_DB_PATH

logger = structlog.get_logger()

_DEFAULT_KB_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "knowledge-base"
_DEFAULT_CHROMA_PATH = VECTOR_DB_PATH

_DEFINITION_KEYWORDS = frozenset({"定義", "定义", "definition", "是什麼", "是什么"})
_CASE_STUDY_KEYWORDS = frozenset({"案例", "case study", "實例", "实例", "實驗", "实验"})
_METHODOLOGY_KEYWORDS = frozenset({"方法論", "方法论", "methodology", "實踐指南", "实践指南"})


class KnowledgeFragment(BaseModel):
    source_id: str
    source_file: str
    topic: str
    category: str
    content: str
    keywords: list[str] = Field(default_factory=list)
    language: str = "zh-HK"
    section_title: str


class KnowledgeBaseEngine:
    def __init__(
        self,
        kb_path: Path | None = None,
        chroma_path: Path | None = None,
    ) -> None:
        self.kb_path = Path(kb_path) if kb_path else _DEFAULT_KB_PATH
        self.chroma_path = Path(chroma_path) if chroma_path else _DEFAULT_CHROMA_PATH
        self._fragments: list[KnowledgeFragment] = []
        self._files_loaded: int = 0
        self._chroma_available: bool = False
        self._collection: Any = None

        self._init_chroma()
        self._load_and_index()

        logger.info(
            "knowledge_base_engine_initialized",
            kb_path=str(self.kb_path),
            fragments=len(self._fragments),
            files_loaded=self._files_loaded,
            chroma_available=self._chroma_available,
        )

    def _init_chroma(self) -> None:
        try:
            import chromadb

            self.chroma_path.parent.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.chroma_path))
            try:
                client.delete_collection("knowledge_base")
            except Exception:
                pass
            self._collection = client.get_or_create_collection(
                name="knowledge_base",
                metadata={"description": "Harnessing knowledge base fragments"},
            )
            self._chroma_available = True
        except Exception as e:
            logger.warning("chromadb_unavailable", error=str(e))
            self._chroma_available = False

    def _load_and_index(self) -> None:
        if not self.kb_path.exists():
            logger.warning("kb_path_not_found", path=str(self.kb_path))
            return

        all_fragments: list[KnowledgeFragment] = []
        md_files = sorted(self.kb_path.glob("*.md"))

        for md_file in md_files:
            if md_file.name.startswith("00-"):
                continue
            fragments = self._parse_markdown(md_file)
            all_fragments.extend(fragments)
            self._files_loaded += 1

        self._fragments = all_fragments

        if self._chroma_available and all_fragments:
            self._index_to_chroma(all_fragments)

    def _parse_markdown(self, file_path: Path) -> list[KnowledgeFragment]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("failed_to_read_kb_file", file=str(file_path), error=str(e))
            return []

        filename = file_path.name
        num_match = re.match(r"(\d+)", filename)
        source_id = f"KB-{num_match.group(1)}" if num_match else f"KB-{filename}"

        lines = content.split("\n")
        topic = ""
        section = ""
        subsection = ""
        fragments: list[KnowledgeFragment] = []
        paragraph_buf: list[str] = []
        blockquote_buf: list[str] = []
        table_header: list[str] = []
        table_data: list[str] = []
        in_code_block = False

        def _make_fragment(text: str, category: str) -> KnowledgeFragment:
            return KnowledgeFragment(
                source_id=source_id,
                source_file=filename,
                topic=topic,
                category=category,
                content=text,
                keywords=self._extract_keywords(text, subsection or section),
                language="zh-HK",
                section_title=subsection or section,
            )

        def _flush_paragraph() -> None:
            nonlocal paragraph_buf
            text = " ".join(paragraph_buf).strip()
            if text and len(text) > 5:
                category = self._infer_category(section, subsection)
                fragments.append(_make_fragment(text, category))
            paragraph_buf = []

        def _flush_blockquotes() -> None:
            nonlocal blockquote_buf
            text = " ".join(blockquote_buf).strip()
            if text:
                fragments.append(_make_fragment(text, "quote"))
            blockquote_buf = []

        def _flush_table() -> None:
            nonlocal table_header, table_data
            headers: list[str] = []
            if table_header:
                headers = [c.strip() for c in table_header[0].strip("|").split("|")]
            for row in table_data:
                cells = [c.strip() for c in row.strip("|").split("|")]
                if headers:
                    parts: list[str] = []
                    for i, cell in enumerate(cells):
                        if i < len(headers) and cell:
                            parts.append(f"{headers[i]}: {cell}")
                        elif cell:
                            parts.append(cell)
                    text = " | ".join(parts)
                else:
                    text = " | ".join(cells)
                if text.strip():
                    fragments.append(_make_fragment(text.strip(), "data_point"))
            table_header = []
            table_data = []

        def _flush_all() -> None:
            _flush_paragraph()
            _flush_blockquotes()
            _flush_table()

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            if stripped.startswith("# ") and not stripped.startswith("## "):
                _flush_all()
                topic = stripped[2:].strip()
                continue

            if stripped.startswith("## "):
                _flush_all()
                section = stripped[3:].strip()
                subsection = ""
                continue

            if stripped.startswith("### "):
                _flush_all()
                subsection = stripped[4:].strip()
                continue

            if stripped.startswith("> "):
                _flush_paragraph()
                blockquote_buf.append(stripped[2:].strip())
                continue

            if stripped.startswith("|") and "|" in stripped[1:]:
                _flush_paragraph()
                _flush_blockquotes()
                if not table_header:
                    table_header = [stripped]
                elif re.match(r"^\|[\s\-:|]+\|$", stripped):
                    continue
                else:
                    table_data.append(stripped)
                continue

            if stripped == "---":
                _flush_all()
                continue

            if stripped == "":
                _flush_paragraph()
                continue

            if table_header or table_data:
                _flush_table()
            _flush_blockquotes()

            list_match = re.match(r"^([\-\*]|\d+\.)\s+(.+)", stripped)
            if list_match:
                paragraph_buf.append(list_match.group(2))
            else:
                paragraph_buf.append(stripped)

        _flush_all()
        return fragments

    def _infer_category(self, section: str, subsection: str) -> str:
        combined = (section + " " + subsection).lower()
        if any(kw in combined for kw in _DEFINITION_KEYWORDS):
            return "definition"
        if any(kw in combined for kw in _CASE_STUDY_KEYWORDS):
            return "case_study"
        if any(kw in combined for kw in _METHODOLOGY_KEYWORDS):
            return "methodology"
        return "insight"

    def _extract_keywords(self, text: str, heading: str) -> list[str]:
        keywords: set[str] = set()
        for match in re.findall(r"\*\*(.+?)\*\*", text):
            keywords.add(match.strip())
        for match in re.findall(r"`(.+?)`", text):
            keywords.add(match.strip())
        for word in heading.split():
            cleaned = word.strip("，。、：；！？「」『』（）()[]【】0123456789.")
            if len(cleaned) > 1:
                keywords.add(cleaned)
        return list(keywords)[:10]

    def _index_to_chroma(self, fragments: list[KnowledgeFragment]) -> None:
        if not self._collection:
            return
        batch_size = 100
        for i in range(0, len(fragments), batch_size):
            batch = fragments[i : i + batch_size]
            ids = [f"{f.source_id}-{i + j}" for j, f in enumerate(batch)]
            documents = [f.content for f in batch]
            metadatas = [
                {
                    "source_id": f.source_id,
                    "source_file": f.source_file,
                    "topic": f.topic,
                    "category": f.category,
                    "keywords": ", ".join(f.keywords),
                    "language": f.language,
                    "section_title": f.section_title,
                }
                for f in batch
            ]
            self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def search(
        self, query: str, n_results: int = 5, category: str | None = None
    ) -> list[KnowledgeFragment]:
        if self._chroma_available and self._collection:
            count = self._collection.count()
            if count == 0:
                return self._memory_search(query, n_results, category)
            where_filter = {"category": category} if category else None
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
                where=where_filter,
            )
            return self._chroma_results_to_fragments(results)
        return self._memory_search(query, n_results, category)

    def _chroma_results_to_fragments(self, results: dict) -> list[KnowledgeFragment]:
        fragments: list[KnowledgeFragment] = []
        docs = results.get("documents", [[]])[0] or []
        metas = results.get("metadatas", [[]])[0] or []
        for doc, meta in zip(docs, metas):
            if meta is None:
                meta = {}
            fragments.append(
                KnowledgeFragment(
                    source_id=meta.get("source_id", ""),
                    source_file=meta.get("source_file", ""),
                    topic=meta.get("topic", ""),
                    category=meta.get("category", "insight"),
                    content=doc or "",
                    keywords=meta.get("keywords", "").split(", ") if meta.get("keywords") else [],
                    language=meta.get("language", "zh-HK"),
                    section_title=meta.get("section_title", ""),
                )
            )
        return fragments

    def _memory_search(
        self, query: str, n_results: int, category: str | None = None
    ) -> list[KnowledgeFragment]:
        query_lower = query.lower()
        scored: list[tuple[int, KnowledgeFragment]] = []
        for f in self._fragments:
            if category and f.category != category:
                continue
            score = 0
            for word in query_lower.split():
                if word in f.content.lower():
                    score += 1
                if word in f.topic.lower():
                    score += 2
                if word in " ".join(f.keywords).lower():
                    score += 1
            if score > 0:
                scored.append((score, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:n_results]]

    def get_facts(self, topic: str, n: int = 5) -> list[KnowledgeFragment]:
        results: list[KnowledgeFragment] = []
        for cat in ["definition", "data_point", "quote"]:
            results.extend(self.search(topic, n_results=n, category=cat))
        return results[:n]

    def get_case_studies(self, topic: str, n: int = 3) -> list[KnowledgeFragment]:
        return self.search(topic, n_results=n, category="case_study")

    def get_definitions(self, topic: str) -> list[KnowledgeFragment]:
        return self.search(topic, n_results=5, category="definition")

    def stats(self) -> dict[str, Any]:
        categories: dict[str, int] = {}
        topics: set[str] = set()
        for f in self._fragments:
            categories[f.category] = categories.get(f.category, 0) + 1
            topics.add(f.topic)
        return {
            "total_fragments": len(self._fragments),
            "files_loaded": self._files_loaded,
            "categories": categories,
            "topics": sorted(topics),
        }
