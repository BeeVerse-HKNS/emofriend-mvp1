from __future__ import annotations

import hashlib
import logging
import math
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QuorumOutcome(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEADLOCK = "deadlock"
    EXPANDED = "expanded"
    UNANIMOUS = "unanimous"


@dataclass
class Decision:
    result: str
    confidence: float
    voter_count: int
    votes: List[str]
    outcome: QuorumOutcome
    entropy: float
    expanded: bool
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "confidence": round(self.confidence, 4),
            "voter_count": self.voter_count,
            "votes": list(self.votes),
            "outcome": self.outcome.value,
            "entropy": round(self.entropy, 4),
            "expanded": self.expanded,
            "timestamp": self.timestamp,
        }


@dataclass
class QuorumStats:
    total_decisions: int = 0
    expansions: int = 0
    approvals: int = 0
    rejections: int = 0
    deadlocks: int = 0
    unanimous: int = 0
    total_votes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_decisions": self.total_decisions,
            "expansions": self.expansions,
            "approvals": self.approvals,
            "rejections": self.rejections,
            "deadlocks": self.deadlocks,
            "unanimous": self.unanimous,
            "total_votes": self.total_votes,
            "expansion_rate": round(self.expansions / self.total_decisions, 4) if self.total_decisions > 0 else 0.0,
        }


class Quorum:
    DEFAULT_VOTERS = 3
    EXPANSION_VOTERS = 5
    DEFAULT_ENTROPY_THRESHOLD = 0.5
    CANDIDATE_VOTES = ("yes", "no", "abstain")

    def __init__(
        self,
        default_voters: int = DEFAULT_VOTERS,
        expansion_voters: int = EXPANSION_VOTERS,
        entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    ) -> None:
        self.default_voters = default_voters
        self.expansion_voters = expansion_voters
        self.entropy_threshold = entropy_threshold
        self._stats = QuorumStats()
        logger.info(
            f"quorum_initialized default_voters={default_voters} expansion_voters={expansion_voters} "
            f"entropy_threshold={entropy_threshold}"
        )

    def _compute_entropy(self, votes: List[str]) -> float:
        if not votes:
            return 0.0
        counts = Counter(votes)
        total = len(votes)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log(p)
        return entropy

    def _simulated_votes(self, proposal: str, voter_count: int) -> List[str]:
        proposal_hash = hashlib.sha256(proposal.encode("utf-8")).hexdigest()
        votes: List[str] = []
        for i in range(voter_count):
            segment = proposal_hash[i * 4 : (i + 1) * 4] if i * 4 + 4 <= len(proposal_hash) else proposal_hash
            try:
                bucket = int(segment, 16) % len(self.CANDIDATE_VOTES)
            except ValueError:
                bucket = i % len(self.CANDIDATE_VOTES)
            votes.append(self.CANDIDATE_VOTES[bucket])
        return votes

    def _majority(self, votes: List[str]) -> tuple:
        counts = Counter(votes)
        total = len(votes)
        if not counts:
            return "abstain", 0.0, QuorumOutcome.DEADLOCK
        top_label, top_count = counts.most_common(1)[0]
        confidence = top_count / total if total > 0 else 0.0
        if top_count == total:
            outcome = QuorumOutcome.UNANIMOUS
        else:
            outcome = QuorumOutcome.APPROVED if top_label == "yes" else (
                QuorumOutcome.REJECTED if top_label == "no" else QuorumOutcome.DEADLOCK
            )
        return top_label, confidence, outcome

    def decide(
        self,
        proposal: str,
        voters: Optional[int] = None,
        vote_fn: Optional[Callable[[str, int], List[str]]] = None,
    ) -> Decision:
        if not proposal or not proposal.strip():
            raise ValueError("proposal must be a non-empty string")
        voter_count = voters if voters is not None else self.default_voters
        if voter_count < 1:
            raise ValueError("voter_count must be >= 1")
        expanded = False
        if vote_fn is not None:
            try:
                votes = list(vote_fn(proposal, voter_count))
            except Exception as exc:
                logger.error(f"quorum_vote_fn_failed error={exc} falling_back_to_simulated")
                votes = self._simulated_votes(proposal, voter_count)
        else:
            votes = self._simulated_votes(proposal, voter_count)
        votes = [str(v).strip().lower() for v in votes if v is not None]
        if len(votes) < voter_count:
            filler_count = voter_count - len(votes)
            votes.extend(self._simulated_votes(proposal + "_fill", filler_count))
        entropy = self._compute_entropy(votes)
        if entropy > self.entropy_threshold and voter_count < self.expansion_voters:
            extra = self.expansion_voters - voter_count
            logger.info(
                f"quorum_expanding entropy={entropy:.4f} threshold={self.entropy_threshold} adding={extra}"
            )
            if vote_fn is not None:
                try:
                    extra_votes = list(vote_fn(proposal, extra))
                except Exception as exc:
                    logger.error(f"quorum_vote_fn_expansion_failed error={exc}")
                    extra_votes = self._simulated_votes(proposal + "_expand", extra)
            else:
                extra_votes = self._simulated_votes(proposal + "_expand", extra)
            extra_votes = [str(v).strip().lower() for v in extra_votes if v is not None]
            votes.extend(extra_votes)
            voter_count = len(votes)
            entropy = self._compute_entropy(votes)
            expanded = True
        result, confidence, outcome = self._majority(votes)
        decision = Decision(
            result=result,
            confidence=confidence,
            voter_count=voter_count,
            votes=votes,
            outcome=outcome,
            entropy=entropy,
            expanded=expanded,
            metadata={"proposal_length": len(proposal)},
        )
        self._stats.total_decisions += 1
        self._stats.total_votes += voter_count
        if expanded:
            self._stats.expansions += 1
        if outcome == QuorumOutcome.APPROVED:
            self._stats.approvals += 1
        elif outcome == QuorumOutcome.REJECTED:
            self._stats.rejections += 1
        elif outcome == QuorumOutcome.DEADLOCK:
            self._stats.deadlocks += 1
        elif outcome == QuorumOutcome.UNANIMOUS:
            self._stats.unanimous += 1
        logger.info(
            f"quorum_decided result={result} confidence={confidence:.4f} voters={voter_count} "
            f"entropy={entropy:.4f} outcome={outcome.value} expanded={expanded}"
        )
        return decision

    def reset_stats(self) -> None:
        self._stats = QuorumStats()
        logger.info("quorum_stats_reset")

    def stats(self) -> Dict[str, Any]:
        base = self._stats.to_dict()
        base["default_voters"] = self.default_voters
        base["expansion_voters"] = self.expansion_voters
        base["entropy_threshold"] = self.entropy_threshold
        return base


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    q = Quorum(default_voters=3, expansion_voters=5, entropy_threshold=0.5)

    print("=== Single decision (simulated) ===")
    d1 = q.decide("Should we deploy the new feature?", voters=3)
    print(f"Decision 1: {d1.to_dict()}")

    print("\n=== Custom vote_fn ===")
    def custom_vote_fn(proposal: str, n: int) -> List[str]:
        return ["yes"] * n

    d2 = q.decide("Approve merger?", voters=4, vote_fn=custom_vote_fn)
    print(f"Decision 2: {d2.to_dict()}")

    print("\n=== Conflict (high entropy triggers expansion) ===")
    def split_vote_fn(proposal: str, n: int) -> List[str]:
        return ["yes", "no", "abstain"][:n]

    d3 = q.decide("Adopt new framework?", voters=3, vote_fn=split_vote_fn)
    print(f"Decision 3: {d3.to_dict()}")

    print(f"\nFinal stats: {q.stats()}")


if __name__ == "__main__":
    main()
