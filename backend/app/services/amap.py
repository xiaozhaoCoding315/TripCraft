from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.services.cache import cache_service


@dataclass
class AmapPoi:
    id: str
    name: str
    type: str
    address: str | None
    location: tuple[float | None, float | None]
    rating: str | None = None
    cost: str | None = None


class AmapService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = "https://restapi.amap.com/v3"

    @property
    def enabled(self) -> bool:
        return bool(self.settings.amap_api_key)

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("AMAP_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(f"{self.base_url}{path}", params={**params, "key": self.settings.amap_api_key})
            res.raise_for_status()
            data = res.json()
        if data.get("status") != "1":
            raise RuntimeError(data.get("info") or "Amap request failed")
        return data

    async def geocode(self, city: str) -> tuple[float | None, float | None]:
        data = await self._get("/geocode/geo", {"address": city})
        geocodes = data.get("geocodes") or []
        if not geocodes:
            return None, None
        lng, lat = geocodes[0].get("location", ",").split(",")[:2]
        return float(lng), float(lat)

    async def geocode_address(self, address: str, city: str = "") -> tuple[float | None, float | None]:
        """解析具体地址为坐标，可选加上城市前缀提高命中率"""
        # 优先用城市+地址组合
        full = f"{city}{address}" if city and city not in address else address
        try:
            data = await self._get("/geocode/geo", {"address": full, "city": city or ""})
            geocodes = data.get("geocodes") or []
            if geocodes:
                lng, lat = geocodes[0].get("location", ",").split(",")[:2]
                return float(lng), float(lat)
        except Exception:
            pass
        # 回退：只用地址
        try:
            data = await self._get("/geocode/geo", {"address": address})
            geocodes = data.get("geocodes") or []
            if geocodes:
                lng, lat = geocodes[0].get("location", ",").split(",")[:2]
                return float(lng), float(lat)
        except Exception:
            pass
        return None, None

    async def weather(self, city: str) -> dict[str, Any]:
        # Check cache first
        cache_key = f"weather:{city}"
        cached = await cache_service.get_cached_amap_response(cache_key)
        if cached:
            return cached
        data = await self._get("/weather/weatherInfo", {"city": city, "extensions": "all"})
        forecasts = data.get("forecasts") or []
        result = forecasts[0] if forecasts else {"city": city, "casts": []}
        # Cache the result
        await cache_service.cache_amap_response(cache_key, result, ttl=cache_service.TTL_MEDIUM)
        return result

    async def search_pois(self, city: str, keywords: str, types: str | None = None, offset: int = 12) -> list[AmapPoi]:
        # Check cache first
        cache_key = f"pois:{city}:{keywords}:{types}:{offset}"
        cached = await cache_service.get_cached_amap_response(cache_key)
        if cached:
            return [self._parse_poi(item) for item in cached]

        params: dict[str, Any] = {"city": city, "keywords": keywords, "offset": offset, "page": 1, "extensions": "all"}
        if types:
            params["types"] = types
        data = await self._get("/place/text", params)
        pois = data.get("pois", [])
        # Cache the result
        await cache_service.cache_amap_response(cache_key, pois, ttl=cache_service.TTL_MEDIUM)
        return [self._parse_poi(item) for item in pois]

    def fallback_pois(self, city: str, category: str) -> list[AmapPoi]:
        samples = {
            "attraction": ["城市地标", "历史街区", "城市公园", "博物馆"],
            "hotel": ["市中心舒适酒店", "景区附近酒店", "交通枢纽酒店"],
            "food": ["本地特色餐厅", "老字号餐馆", "轻食简餐"],
        }
        return [
            AmapPoi(
                id=f"fallback_{category}_{idx}",
                name=f"{city}{name}",
                type=category,
                address=f"{city}核心区域",
                location=(None, None),
            )
            for idx, name in enumerate(samples.get(category, ["推荐地点"]), start=1)
        ]

    @staticmethod
    def _parse_poi(item: dict[str, Any]) -> AmapPoi:
        lng: float | None = None
        lat: float | None = None
        location = item.get("location") or ""
        if "," in location:
            raw_lng, raw_lat = location.split(",")[:2]
            lng, lat = float(raw_lng), float(raw_lat)
        biz_ext = item.get("biz_ext") or {}
        return AmapPoi(
            id=item.get("id") or item.get("name") or "unknown",
            name=item.get("name") or "未知地点",
            type=item.get("type") or "",
            address=item.get("address") if isinstance(item.get("address"), str) else None,
            location=(lng, lat),
            rating=biz_ext.get("rating"),
            cost=biz_ext.get("cost"),
        )
