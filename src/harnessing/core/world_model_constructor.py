from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class EntityType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    RESOURCE = "resource"
    EVENT = "event"
    ACTION = "action"
    SYSTEM = "system"


class RelationType(Enum):
    DEPENDS_ON = "depends_on"
    AFFECTS = "affects"
    CAUSES = "causes"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class Entity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    attributes: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = 1.0


@dataclass
class Relation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    strength: float = 1.0
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CausalChain:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    events: list[str] = field(default_factory=list)
    causal_links: list[tuple[int, int, float]] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class TemporalEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration: float = 0.0
    related_entities: list[str] = field(default_factory=list)
    sequence_order: int = 0


@dataclass
class Goal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    parent_goal_id: Optional[str] = None
    sub_goals: list[str] = field(default_factory=list)
    progress: float = 0.0
    status: GoalStatus = GoalStatus.PENDING


@dataclass
class WorldModelSummary:
    total_entities: int = 0
    total_relations: int = 0
    total_chains: int = 0
    total_events: int = 0
    active_goals: int = 0
    coverage_score: float = 0.0


@dataclass
class EntitySummary:
    entity: Optional[Entity] = None
    relations: list[Relation] = field(default_factory=list)
    chains: list[CausalChain] = field(default_factory=list)
    timeline: list[TemporalEvent] = field(default_factory=list)
    related_goals: list[Goal] = field(default_factory=list)


class EntityGraph:
    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
        self._outgoing: dict[str, list[str]] = defaultdict(list)
        self._incoming: dict[str, list[str]] = defaultdict(list)

    def add_entity(self, entity: Entity) -> str:
        self._entities[entity.id] = entity
        return entity.id

    def add_relation(self, relation: Relation) -> str:
        self._relations[relation.id] = relation
        self._outgoing[relation.source_id].append(relation.id)
        self._incoming[relation.target_id].append(relation.id)
        return relation.id

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def get_relations(self, entity_id: str) -> list[Relation]:
        result = []
        for rid in self._outgoing.get(entity_id, []):
            if rid in self._relations:
                result.append(self._relations[rid])
        for rid in self._incoming.get(entity_id, []):
            if rid in self._relations:
                result.append(self._relations[rid])
        return result

    def find_path(self, from_id: str, to_id: str) -> list[str]:
        if from_id not in self._entities or to_id not in self._entities:
            return []
        if from_id == to_id:
            return [from_id]
        visited: set[str] = set()
        queue: deque[tuple[str, list[str]]] = deque()
        queue.append((from_id, [from_id]))
        visited.add(from_id)
        while queue:
            current, path = queue.popleft()
            for rid in self._outgoing.get(current, []):
                rel = self._relations.get(rid)
                if rel is None:
                    continue
                neighbor = rel.target_id
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == to_id:
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        return []

    def get_neighbors(self, entity_id: str, max_depth: int = 1) -> dict[str, list[Relation]]:
        result: dict[str, list[Relation]] = {}
        visited: set[str] = {entity_id}
        current_level = {entity_id}
        for depth in range(1, max_depth + 1):
            next_level: set[str] = set()
            for eid in current_level:
                for rel in self.get_relations(eid):
                    other_id = rel.target_id if rel.source_id == eid else rel.source_id
                    if other_id not in visited:
                        visited.add(other_id)
                        next_level.add(other_id)
                        key = f"depth_{depth}"
                        if key not in result:
                            result[key] = []
                        result[key].append(rel)
            current_level = next_level
        return result

    def update_entity(self, entity_id: str, attributes: dict) -> bool:
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        entity.attributes.update(attributes)
        entity.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relation_count(self) -> int:
        return len(self._relations)

    def find_entity_by_name(self, name: str) -> Entity | None:
        for entity in self._entities.values():
            if entity.name == name:
                return entity
        return None


class CausalChainRecorder:
    def __init__(self) -> None:
        self._chains: dict[str, CausalChain] = {}
        self._event_index: dict[str, list[str]] = defaultdict(list)

    def record_chain(self, events: list[str], links: list[tuple[int, int, float]]) -> CausalChain:
        chain = CausalChain(events=events, causal_links=links)
        self._chains[chain.id] = chain
        for event in events:
            self._event_index[event].append(chain.id)
        return chain

    def get_chains_involving(self, entity_name: str) -> list[CausalChain]:
        chain_ids = set(self._event_index.get(entity_name, []))
        return [self._chains[cid] for cid in chain_ids if cid in self._chains]

    def predict_next(self, event: str) -> list[tuple[str, float]]:
        chains = self.get_chains_involving(event)
        predictions: dict[str, list[float]] = defaultdict(list)
        for chain in chains:
            for i, e in enumerate(chain.events):
                if e == event:
                    for src_idx, tgt_idx, strength in chain.causal_links:
                        if src_idx == i and tgt_idx < len(chain.events):
                            target_event = chain.events[tgt_idx]
                            predictions[target_event].append(strength)
        result = []
        for predicted_event, strengths in predictions.items():
            avg_strength = sum(strengths) / len(strengths)
            result.append((predicted_event, avg_strength))
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    @property
    def chain_count(self) -> int:
        return len(self._chains)


class TemporalSequenceTracker:
    def __init__(self) -> None:
        self._events: dict[str, TemporalEvent] = {}
        self._entity_events: dict[str, list[str]] = defaultdict(list)

    def record_event(self, event: TemporalEvent) -> str:
        self._events[event.id] = event
        for eid in event.related_entities:
            self._entity_events[eid].append(event.id)
        return event.id

    def get_timeline(self, entity_id: str) -> list[TemporalEvent]:
        event_ids = self._entity_events.get(entity_id, [])
        events = [self._events[eid] for eid in event_ids if eid in self._events]
        events.sort(key=lambda e: (e.timestamp, e.sequence_order))
        return events

    def get_duration_stats(self, entity_id: str) -> dict:
        events = self.get_timeline(entity_id)
        if not events:
            return {"count": 0, "total_duration": 0.0, "avg_duration": 0.0, "min_duration": 0.0, "max_duration": 0.0}
        durations = [e.duration for e in events if e.duration > 0]
        if not durations:
            return {"count": len(events), "total_duration": 0.0, "avg_duration": 0.0, "min_duration": 0.0, "max_duration": 0.0}
        return {
            "count": len(events),
            "total_duration": sum(durations),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
        }

    @property
    def event_count(self) -> int:
        return len(self._events)


class GoalTracker:
    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}

    def add_goal(self, goal: Goal) -> str:
        self._goals[goal.id] = goal
        if goal.parent_goal_id and goal.parent_goal_id in self._goals:
            parent = self._goals[goal.parent_goal_id]
            if goal.id not in parent.sub_goals:
                parent.sub_goals.append(goal.id)
        return goal.id

    def update_progress(self, goal_id: str, progress: float) -> bool:
        goal = self._goals.get(goal_id)
        if goal is None:
            return False
        goal.progress = max(0.0, min(1.0, progress))
        if goal.progress >= 1.0:
            goal.status = GoalStatus.COMPLETED
        elif goal.progress > 0.0:
            goal.status = GoalStatus.IN_PROGRESS
        return True

    def get_active_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS)]

    def decompose_goal(self, goal_id: str, sub_goals: list[str]) -> list[Goal]:
        parent = self._goals.get(goal_id)
        if parent is None:
            return []
        created = []
        for name in sub_goals:
            sub = Goal(name=name, parent_goal_id=goal_id)
            self._goals[sub.id] = sub
            parent.sub_goals.append(sub.id)
            created.append(sub)
        return created

    @property
    def active_goal_count(self) -> int:
        return len(self.get_active_goals())


class ModelUpdater:
    def __init__(self, entity_graph: EntityGraph, causal_recorder: CausalChainRecorder) -> None:
        self._graph = entity_graph
        self._causal = causal_recorder

    def update_from_interaction(self, interaction: dict) -> list[str]:
        updated_ids: list[str] = []
        if "entities" in interaction:
            for ent_data in interaction["entities"]:
                name = ent_data.get("name", "")
                entity_type_str = ent_data.get("entity_type", "concept").upper()
                try:
                    entity_type = EntityType[entity_type_str]
                except KeyError:
                    entity_type = EntityType.CONCEPT
                attributes = ent_data.get("attributes", {})
                eid = self.learn_entity(name, entity_type, attributes)
                updated_ids.append(eid)
        if "relations" in interaction:
            for rel_data in interaction["relations"]:
                source = rel_data.get("source", "")
                target = rel_data.get("target", "")
                rt_str = rel_data.get("relation_type", "related_to").upper()
                try:
                    relation_type = RelationType[rt_str]
                except KeyError:
                    relation_type = RelationType.RELATED_TO
                rid = self.learn_relation(source, target, relation_type)
                updated_ids.append(rid)
        if "causal_chain" in interaction:
            chain_data = interaction["causal_chain"]
            events = chain_data.get("events", [])
            links = [tuple(l) for l in chain_data.get("links", [])]
            chain = self._causal.record_chain(events, links)
            updated_ids.append(chain.id)
        return updated_ids

    def learn_entity(self, name: str, entity_type: EntityType, attributes: dict) -> str:
        existing = self._graph.find_entity_by_name(name)
        if existing is not None:
            self._graph.update_entity(existing.id, attributes)
            return existing.id
        entity = Entity(name=name, entity_type=entity_type, attributes=attributes)
        return self._graph.add_entity(entity)

    def learn_relation(self, source: str, target: str, relation_type: RelationType) -> str:
        source_entity = self._graph.find_entity_by_name(source)
        target_entity = self._graph.find_entity_by_name(target)
        if source_entity is None:
            source_entity = Entity(name=source, entity_type=EntityType.CONCEPT)
            self._graph.add_entity(source_entity)
        if target_entity is None:
            target_entity = Entity(name=target, entity_type=EntityType.CONCEPT)
            self._graph.add_entity(target_entity)
        relation = Relation(source_id=source_entity.id, target_id=target_entity.id, relation_type=relation_type)
        return self._graph.add_entity(relation) if False else self._graph.add_relation(relation)


class WorldModelConstructor:
    def __init__(self) -> None:
        self.entity_graph = EntityGraph()
        self.causal_recorder = CausalChainRecorder()
        self.temporal_tracker = TemporalSequenceTracker()
        self.goal_tracker = GoalTracker()
        self.model_updater = ModelUpdater(self.entity_graph, self.causal_recorder)

    def construct_from_interactions(self, interactions: list[dict]) -> WorldModelSummary:
        for interaction in interactions:
            self.model_updater.update_from_interaction(interaction)
        total_entities = self.entity_graph.entity_count
        total_relations = self.entity_graph.relation_count
        total_chains = self.causal_recorder.chain_count
        total_events = self.temporal_tracker.event_count
        active_goals = self.goal_tracker.active_goal_count
        max_possible = max(total_entities + total_relations + total_chains + total_events, 1)
        actual = total_entities + total_relations + total_chains + total_events
        coverage_score = min(actual / max(max_possible, 1), 1.0) if actual > 0 else 0.0
        coverage_score = 1.0 if actual > 0 else 0.0
        return WorldModelSummary(
            total_entities=total_entities,
            total_relations=total_relations,
            total_chains=total_chains,
            total_events=total_events,
            active_goals=active_goals,
            coverage_score=coverage_score,
        )

    def query(self, entity_name: str) -> EntitySummary:
        entity = self.entity_graph.find_entity_by_name(entity_name)
        if entity is None:
            return EntitySummary()
        relations = self.entity_graph.get_relations(entity.id)
        chains = self.causal_recorder.get_chains_involving(entity_name)
        timeline = self.temporal_tracker.get_timeline(entity.id)
        related_goals = []
        for goal in self.goal_tracker.get_active_goals():
            if entity_name in goal.name or any(entity_name in sg for sg in goal.sub_goals):
                related_goals.append(goal)
        return EntitySummary(
            entity=entity,
            relations=relations,
            chains=chains,
            timeline=timeline,
            related_goals=related_goals,
        )


class RegionalWorldModelMixin:
    HK_CROSS_BORDER_ENTITIES = [
        {"name": "HongKongUser", "entity_type": "PERSON", "attributes": {"jurisdiction": "HK", "data_category": "personal"}},
        {"name": "OverseasServer", "entity_type": "SYSTEM", "attributes": {"jurisdiction": "US", "data_category": "cloud"}},
    ]

    CN_DATA_LOCALIZATION_ENTITIES = [
        {"name": "ChinaUserData", "entity_type": "RESOURCE", "attributes": {"jurisdiction": "CN", "localization_required": True}},
        {"name": "ForeignCloud", "entity_type": "SYSTEM", "attributes": {"jurisdiction": "US", "can_receive_china_data": False}},
    ]

    EU_GDPR_ENTITIES = [
        {"name": "EUDataSubject", "entity_type": "PERSON", "attributes": {"jurisdiction": "EU", "gdpr_rights": True}},
        {"name": "DataProcessor", "entity_type": "ORGANIZATION", "attributes": {"gdpr_article_28": True}},
    ]

    SG_FRAMEWORK_ENTITIES = [
        {"name": "AgentSystem", "entity_type": "SYSTEM", "attributes": {"governance_level": "IMDA_compliant"}},
        {"name": "HumanOversight", "entity_type": "CONCEPT", "attributes": {"required": True}},
    ]

    def test_hk_cross_border_awareness(self) -> dict:
        engine = WorldModelConstructor()
        engine.construct_from_interactions([{"entities": self.HK_CROSS_BORDER_ENTITIES}])
        hk_entity = engine.query("HongKongUser")
        overseas_entity = engine.query("OverseasServer")
        has_cross_border = hk_entity.entity is not None and overseas_entity.entity is not None
        return {
            "region": "HK",
            "cross_border_tracked": has_cross_border,
            "total_entities": engine.entity_graph.entity_count,
            "jurisdiction_awareness": has_cross_border,
        }

    def test_cn_data_localization(self) -> dict:
        engine = WorldModelConstructor()
        engine.construct_from_interactions([{"entities": self.CN_DATA_LOCALIZATION_ENTITIES}])
        china_data = engine.query("ChinaUserData")
        foreign_cloud = engine.query("ForeignCloud")
        can_transfer = (
            china_data.entity is not None and
            foreign_cloud.entity is not None and
            china_data.entity.attributes.get("localization_required") and
            not foreign_cloud.entity.attributes.get("can_receive_china_data")
        )
        return {
            "region": "CN",
            "data_localization_tracked": china_data.entity is not None,
            "transfer_restriction": can_transfer,
            "requires_approval": can_transfer,
        }

    def test_eu_gdpr_restrictions(self) -> dict:
        engine = WorldModelConstructor()
        engine.construct_from_interactions([
            {"entities": self.EU_GDPR_ENTITIES},
            {"relations": [
                {"source": "EUDataSubject", "target": "DataProcessor", "relation_type": "DEPENDS_ON"}
            ]}
        ])
        subject = engine.query("EUDataSubject")
        processor = engine.query("DataProcessor")
        has_data_controller = subject.entity is not None and processor.entity is not None
        return {
            "region": "EU",
            "gdpr_tracked": has_data_controller,
            "data_subject_entity": subject.entity is not None,
            "data_processor_entity": processor.entity is not None,
        }

    def test_sg_agent_framework(self) -> dict:
        engine = WorldModelConstructor()
        engine.construct_from_interactions([
            {"entities": self.SG_FRAMEWORK_ENTITIES},
            {"relations": [
                {"source": "AgentSystem", "target": "HumanOversight", "relation_type": "DEPENDS_ON"}
            ]}
        ])
        agent = engine.query("AgentSystem")
        oversight = engine.query("HumanOversight")
        has_governance = agent.entity is not None and oversight.entity is not None
        return {
            "region": "SG",
            "agent_tracked": agent.entity is not None,
            "human_oversight_tracked": oversight.entity is not None,
            "governance_compliant": has_governance,
        }

    def test_multiple_jurisdiction_tracking(self) -> dict:
        engine = WorldModelConstructor()
        all_entities = self.HK_CROSS_BORDER_ENTITIES + self.CN_DATA_LOCALIZATION_ENTITIES
        engine.construct_from_interactions([{"entities": all_entities}])
        jurisdictions = set()
        for entity in engine.entity_graph._entities.values():
            if "jurisdiction" in entity.attributes:
                jurisdictions.add(entity.attributes["jurisdiction"])
        return {
            "regions": list(jurisdictions),
            "total_jurisdictions": len(jurisdictions),
            "cross_region_tracking": len(jurisdictions) > 1,
        }

    def run_all_regional_tests(self) -> dict:
        return {
            "world_model_constructor": {
                "HK_CrossBorder": self.test_hk_cross_border_awareness(),
                "CN_Localization": self.test_cn_data_localization(),
                "EU_GDPR": self.test_eu_gdpr_restrictions(),
                "SG_Framework": self.test_sg_agent_framework(),
                "Multi_Jurisdiction": self.test_multiple_jurisdiction_tracking(),
            }
        }
