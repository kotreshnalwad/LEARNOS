"""
Ranking Agent: Deduplicates, scores, and ranks resources using a
multi-dimensional scoring model: authority × popularity × freshness × completeness × community.
"""
from typing import List, Dict, Set, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse
import re
import math
import structlog

from app.agents.search_agent import RawResource
from app.schemas.schemas import ResourceType

logger = structlog.get_logger()


# Authority scores by platform (0–1)
PLATFORM_AUTHORITY: Dict[str, float] = {
    "YouTube": 0.85,
    "Coursera": 0.95,
    "edX": 0.95,
    "Udemy": 0.80,
    "freeCodeCamp": 0.90,
    "Khan Academy": 0.92,
    "MDN": 0.98,
    "GitHub": 0.85,
    "Pluralsight": 0.88,
    "DataCamp": 0.85,
    "Real Python": 0.90,
    "javascript.info": 0.92,
    "Semantic Scholar": 0.88,
    "Dev.to": 0.72,
    "Medium": 0.68,
    "Toward Data Science": 0.75,
}

# Resource type quality multipliers
TYPE_QUALITY: Dict[ResourceType, float] = {
    ResourceType.COURSE: 1.0,
    ResourceType.DOCUMENTATION: 0.95,
    ResourceType.PAPER: 0.88,
    ResourceType.VIDEO: 0.85,
    ResourceType.GITHUB: 0.80,
    ResourceType.BOOK: 0.90,
    ResourceType.BLOG: 0.70,
    ResourceType.PODCAST: 0.65,
}


class ScoredResource(RawResource):
    authority_score: float = 0.0
    popularity_score: float = 0.0
    freshness_score: float = 0.0
    completeness_score: float = 0.0
    community_score: float = 0.0
    composite_score: float = 0.0
    is_primary: bool = False


class RankingAgent:
    """
    Deduplicates and scores collected resources.
    Scoring formula:
        composite = (authority × 0.30) + (popularity × 0.20) +
                    (freshness × 0.20) + (completeness × 0.20) +
                    (community × 0.10)
    """

    def rank(
        self,
        resources: List[RawResource],
        max_per_type: int = 3,
        max_total: int = 20,
    ) -> List[ScoredResource]:
        """Deduplicate, score, and return top resources."""
        logger.info("Ranking resources", count=len(resources))

        # Deduplicate
        unique = self._deduplicate(resources)
        logger.info("After deduplication", count=len(unique))

        # Score each resource
        scored: List[ScoredResource] = []
        for r in unique:
            s = self._score_resource(r)
            scored.append(s)

        # Sort by composite score
        scored.sort(key=lambda x: x.composite_score, reverse=True)

        # Select top resources, capped per type
        selected = self._select_diverse(scored, max_per_type, max_total)

        # Mark primary resources (top of each type)
        seen_types: Set[ResourceType] = set()
        for r in selected:
            if r.resource_type not in seen_types:
                r.is_primary = True
                seen_types.add(r.resource_type)

        logger.info("Ranking complete", selected=len(selected))
        return selected

    def _deduplicate(self, resources: List[RawResource]) -> List[RawResource]:
        """Remove duplicate URLs and near-duplicate titles."""
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        unique: List[RawResource] = []

        for r in resources:
            normalized_url = self._normalize_url(r.url)
            normalized_title = self._normalize_title(r.title)

            if normalized_url in seen_urls:
                continue

            # Fuzzy title dedup (same platform + similar title)
            key = f"{r.platform}:{normalized_title}"
            if key in seen_titles:
                continue

            seen_urls.add(normalized_url)
            seen_titles.add(key)
            unique.append(r)

        return unique

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for dedup."""
        url = url.lower().rstrip("/")
        url = re.sub(r"\?.*$", "", url)  # strip query params
        url = re.sub(r"#.*$", "", url)   # strip fragments
        url = url.replace("http://", "https://").replace("www.", "")
        return url

    def _normalize_title(self, title: str) -> str:
        """Normalize title for fuzzy dedup."""
        title = title.lower()
        title = re.sub(r"[^a-z0-9 ]", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        # Keep only first 8 words for comparison
        return " ".join(title.split()[:8])

    def _score_resource(self, r: RawResource) -> ScoredResource:
        s = ScoredResource(**vars(r))

        s.authority_score = self._compute_authority(r)
        s.popularity_score = self._compute_popularity(r)
        s.freshness_score = self._compute_freshness(r)
        s.completeness_score = self._compute_completeness(r)
        s.community_score = self._compute_community(r)

        s.composite_score = (
            s.authority_score * 0.30
            + s.popularity_score * 0.20
            + s.freshness_score * 0.20
            + s.completeness_score * 0.20
            + s.community_score * 0.10
        )

        return s

    def _compute_authority(self, r: RawResource) -> float:
        """Platform authority × resource type quality."""
        platform_score = PLATFORM_AUTHORITY.get(r.platform or "", 0.60)
        type_mult = TYPE_QUALITY.get(r.resource_type, 0.70)
        return min(1.0, platform_score * type_mult)

    def _compute_popularity(self, r: RawResource) -> float:
        """Based on view count or star count."""
        views = r.view_count or r.metadata.get("stars") or 0
        if views == 0:
            return 0.50
        # Log scale: 1M views → 1.0, 1K views → 0.5
        return min(1.0, math.log10(views + 1) / 6)

    def _compute_freshness(self, r: RawResource) -> float:
        """Penalize old resources, reward recent ones."""
        if not r.published_date:
            return 0.60
        try:
            pub_date_str = r.published_date[:10]
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_old = (now - pub_date).days
            if days_old < 180:
                return 1.0
            elif days_old < 365:
                return 0.90
            elif days_old < 730:
                return 0.75
            elif days_old < 1095:
                return 0.60
            else:
                return max(0.30, 0.60 - (days_old - 1095) / 3650)
        except Exception:
            return 0.60

    def _compute_completeness(self, r: RawResource) -> float:
        """Score based on available metadata richness."""
        score = 0.40  # base
        if r.description and len(r.description) > 100:
            score += 0.20
        if r.author:
            score += 0.10
        if r.duration_minutes:
            score += 0.15
        if r.thumbnail_url:
            score += 0.05
        if r.resource_type in (ResourceType.COURSE, ResourceType.VIDEO):
            score += 0.10
        return min(1.0, score)

    def _compute_community(self, r: RawResource) -> float:
        """Based on citations, stars, or freeCodeCamp/MDN bonus."""
        if r.platform in ("MDN", "freeCodeCamp", "Khan Academy", "javascript.info"):
            return 0.95
        citations = r.metadata.get("citations", 0)
        if citations > 500:
            return 1.0
        if citations > 100:
            return 0.80
        stars = r.metadata.get("stars", 0)
        if stars > 10000:
            return 0.90
        if stars > 1000:
            return 0.75
        return 0.50

    def _select_diverse(
        self,
        scored: List[ScoredResource],
        max_per_type: int,
        max_total: int,
    ) -> List[ScoredResource]:
        """Select top resources with diversity across types."""
        type_counts: Dict[ResourceType, int] = {}
        selected: List[ScoredResource] = []

        # First pass: ensure at least 1 of high-value types
        priority_types = [
            ResourceType.VIDEO,
            ResourceType.COURSE,
            ResourceType.DOCUMENTATION,
        ]
        for rtype in priority_types:
            for r in scored:
                if r.resource_type == rtype and type_counts.get(rtype, 0) == 0:
                    selected.append(r)
                    type_counts[rtype] = 1
                    break

        # Second pass: fill remaining slots
        for r in scored:
            if len(selected) >= max_total:
                break
            count = type_counts.get(r.resource_type, 0)
            if count >= max_per_type:
                continue
            if r not in selected:
                selected.append(r)
                type_counts[r.resource_type] = count + 1

        return selected
