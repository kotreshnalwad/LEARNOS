"""
Search Agent: Discovers learning resources across the internet using
Tavily, Exa, YouTube API, and Firecrawl. Returns structured resource lists.
"""
from typing import List, Optional, Dict, Any
import asyncio
import httpx
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.core.config import get_settings
from app.schemas.schemas import ResourceType

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class RawResource:
    title: str
    url: str
    resource_type: ResourceType
    description: Optional[str] = None
    author: Optional[str] = None
    platform: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_free: bool = True
    thumbnail_url: Optional[str] = None
    published_date: Optional[str] = None
    view_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SearchAgent:
    """
    Multi-source search agent that collects learning resources
    across courses, videos, documentation, papers, and GitHub repos.
    """

    def __init__(self):
        self.tavily_key = settings.TAVILY_API_KEY
        self.exa_key = settings.EXA_API_KEY
        self.firecrawl_key = settings.FIRECRAWL_API_KEY
        self.youtube_key = settings.YOUTUBE_API_KEY

    async def search_all(self, topic: str, level: str = "beginner") -> List[RawResource]:
        """
        Run all search strategies in parallel and merge results.
        """
        logger.info("Starting comprehensive search", topic=topic, level=level)

        tasks = [
            self._search_tavily_web(topic, level),
            self._search_tavily_courses(topic, level),
            self._search_youtube(topic, level),
            self._search_github(topic),
            self._search_documentation(topic),
            self._search_academic_papers(topic),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_resources: List[RawResource] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Search task {i} failed", error=str(result))
                continue
            all_resources.extend(result)

        logger.info(f"Search complete", topic=topic, total_resources=len(all_resources))
        return all_resources

    async def _search_tavily_web(self, topic: str, level: str) -> List[RawResource]:
        """General web search for tutorials, blogs, guides."""
        queries = [
            f"{topic} tutorial for {level}s",
            f"learn {topic} complete guide",
            f"{topic} best practices {level}",
        ]
        resources = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries[:2]:
                try:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": self.tavily_key,
                            "query": query,
                            "search_depth": "advanced",
                            "include_answer": False,
                            "include_raw_content": False,
                            "max_results": 8,
                            "include_domains": [
                                "medium.com", "dev.to", "freecodecamp.org",
                                "towardsdatascience.com", "css-tricks.com",
                                "smashingmagazine.com", "digitalocean.com",
                                "realpython.com", "javascript.info",
                            ],
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for r in data.get("results", []):
                            platform = self._extract_platform(r.get("url", ""))
                            resources.append(RawResource(
                                title=r.get("title", ""),
                                url=r.get("url", ""),
                                resource_type=ResourceType.BLOG,
                                description=r.get("content", "")[:500],
                                platform=platform,
                                published_date=r.get("published_date"),
                            ))
                except Exception as e:
                    logger.warning("Tavily web search failed", query=query, error=str(e))
        return resources

    async def _search_tavily_courses(self, topic: str, level: str) -> List[RawResource]:
        """Search for structured courses on major platforms."""
        course_domains = [
            "coursera.org", "udemy.com", "edx.org", "pluralsight.com",
            "linkedin.com/learning", "udacity.com", "datacamp.com",
            "codecademy.com", "frontendmasters.com", "egghead.io",
            "thoughtco.com", "khanacademy.org",
        ]
        resources = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_key,
                        "query": f"best {topic} course for {level}s",
                        "search_depth": "basic",
                        "max_results": 10,
                        "include_domains": course_domains,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        platform = self._extract_platform(r.get("url", ""))
                        resources.append(RawResource(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            resource_type=ResourceType.COURSE,
                            description=r.get("content", "")[:500],
                            platform=platform,
                            is_free=self._is_likely_free(r.get("url", "")),
                        ))
            except Exception as e:
                logger.warning("Course search failed", error=str(e))
        return resources

    async def _search_youtube(self, topic: str, level: str) -> List[RawResource]:
        """Search YouTube Data API for educational videos."""
        resources = []
        queries = [
            f"{topic} tutorial {level}",
            f"{topic} full course",
            f"learn {topic} crash course",
        ]
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries[:2]:
                try:
                    resp = await client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "key": self.youtube_key,
                            "q": query,
                            "part": "snippet",
                            "type": "video",
                            "videoDefinition": "high",
                            "videoCategoryId": "27",  # Education
                            "order": "relevance",
                            "maxResults": 8,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("items", []):
                            snippet = item.get("snippet", {})
                            video_id = item.get("id", {}).get("videoId", "")
                            duration = await self._get_youtube_duration(client, video_id)
                            resources.append(RawResource(
                                title=snippet.get("title", ""),
                                url=f"https://www.youtube.com/watch?v={video_id}",
                                resource_type=ResourceType.VIDEO,
                                description=snippet.get("description", "")[:500],
                                author=snippet.get("channelTitle"),
                                platform="YouTube",
                                duration_minutes=duration,
                                thumbnail_url=snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                                published_date=snippet.get("publishedAt"),
                                is_free=True,
                                metadata={"video_id": video_id},
                            ))
                except Exception as e:
                    logger.warning("YouTube search failed", query=query, error=str(e))
        return resources

    async def _get_youtube_duration(self, client: httpx.AsyncClient, video_id: str) -> Optional[int]:
        """Fetch video duration from YouTube API."""
        try:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "key": self.youtube_key,
                    "id": video_id,
                    "part": "contentDetails",
                },
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    duration_str = items[0].get("contentDetails", {}).get("duration", "")
                    return self._parse_iso_duration(duration_str)
        except Exception:
            pass
        return None

    def _parse_iso_duration(self, duration: str) -> Optional[int]:
        """Parse ISO 8601 duration to minutes."""
        import re
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not match:
            return None
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 60 + minutes + (1 if seconds >= 30 else 0)

    async def _search_github(self, topic: str) -> List[RawResource]:
        """Search GitHub for awesome lists and learning repositories."""
        resources = []
        queries = [
            f"awesome {topic} learning",
            f"{topic} examples tutorial",
            f"learn {topic} repository",
        ]
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries[:2]:
                try:
                    resp = await client.get(
                        "https://api.github.com/search/repositories",
                        params={
                            "q": f"{query} in:name,description,readme",
                            "sort": "stars",
                            "order": "desc",
                            "per_page": 5,
                        },
                        headers={"Accept": "application/vnd.github.v3+json"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for repo in data.get("items", []):
                            resources.append(RawResource(
                                title=repo.get("full_name", ""),
                                url=repo.get("html_url", ""),
                                resource_type=ResourceType.GITHUB,
                                description=repo.get("description", "")[:500],
                                author=repo.get("owner", {}).get("login"),
                                platform="GitHub",
                                is_free=True,
                                metadata={
                                    "stars": repo.get("stargazers_count", 0),
                                    "language": repo.get("language"),
                                    "updated_at": repo.get("updated_at"),
                                },
                            ))
                except Exception as e:
                    logger.warning("GitHub search failed", query=query, error=str(e))
        return resources

    async def _search_documentation(self, topic: str) -> List[RawResource]:
        """Search for official documentation."""
        resources = []
        doc_domains = [
            "docs.python.org", "developer.mozilla.org", "docs.microsoft.com",
            "reactjs.org", "vuejs.org", "angular.io", "docs.djangoproject.com",
            "fastapi.tiangolo.com", "pytorch.org", "tensorflow.org",
            "scikit-learn.org", "numpy.org", "pandas.pydata.org",
            "kubernetes.io", "docs.docker.com", "aws.amazon.com/documentation",
        ]
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_key,
                        "query": f"{topic} official documentation getting started",
                        "search_depth": "basic",
                        "max_results": 5,
                        "include_domains": doc_domains,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        resources.append(RawResource(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            resource_type=ResourceType.DOCUMENTATION,
                            description=r.get("content", "")[:500],
                            platform=self._extract_platform(r.get("url", "")),
                            is_free=True,
                        ))
            except Exception as e:
                logger.warning("Documentation search failed", error=str(e))
        return resources

    async def _search_academic_papers(self, topic: str) -> List[RawResource]:
        """Search for research papers via arXiv and Semantic Scholar."""
        resources = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": topic,
                        "fields": "title,abstract,url,year,authors,citationCount",
                        "limit": 5,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for paper in data.get("data", []):
                        if not paper.get("url"):
                            continue
                        authors = ", ".join(
                            a.get("name", "") for a in paper.get("authors", [])[:3]
                        )
                        resources.append(RawResource(
                            title=paper.get("title", ""),
                            url=paper.get("url", ""),
                            resource_type=ResourceType.PAPER,
                            description=paper.get("abstract", "")[:500],
                            author=authors,
                            platform="Semantic Scholar",
                            is_free=True,
                            metadata={
                                "year": paper.get("year"),
                                "citations": paper.get("citationCount", 0),
                            },
                        ))
            except Exception as e:
                logger.warning("Academic paper search failed", error=str(e))
        return resources

    def _extract_platform(self, url: str) -> str:
        """Extract platform name from URL."""
        platform_map = {
            "youtube.com": "YouTube",
            "coursera.org": "Coursera",
            "udemy.com": "Udemy",
            "edx.org": "edX",
            "medium.com": "Medium",
            "dev.to": "Dev.to",
            "github.com": "GitHub",
            "freecodecamp.org": "freeCodeCamp",
            "khanacademy.org": "Khan Academy",
            "pluralsight.com": "Pluralsight",
            "datacamp.com": "DataCamp",
            "realpython.com": "Real Python",
            "javascript.info": "javascript.info",
            "mdn": "MDN",
        }
        for domain, name in platform_map.items():
            if domain in url:
                return name
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return "Web"

    def _is_likely_free(self, url: str) -> bool:
        """Heuristic: check if resource is likely free."""
        paid_indicators = ["udemy.com/course/", "pluralsight.com/courses/"]
        return not any(ind in url for ind in paid_indicators)
