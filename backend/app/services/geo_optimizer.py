"""
TripCraft Geographic Route Optimizer

Optimizes attraction order within each day to minimize travel distance
using clustering and nearest-neighbor algorithms.
"""

import math
from typing import Any

from app.models.travel import GeoPoint, ItineraryItem


class GeoOptimizer:
    """Geographic route optimizer for travel itineraries"""

    @staticmethod
    def haversine_distance(point1: GeoPoint, point2: GeoPoint) -> float:
        """
        Calculate the great-circle distance between two points
        on the Earth using the Haversine formula.
        Returns distance in kilometers.
        """
        if not point1.lng or not point1.lat or not point2.lng or not point2.lat:
            return float('inf')

        # Convert to radians
        lat1 = math.radians(point1.lat)
        lat2 = math.radians(point2.lat)
        dlat = math.radians(point2.lat - point1.lat)
        dlng = math.radians(point2.lng - point1.lng)

        # Haversine formula
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        r = 6371

        return r * c

    @staticmethod
    def optimize_day_route(items: list[ItineraryItem], start_location: GeoPoint | None = None) -> list[ItineraryItem]:
        """
        Optimize the order of attractions in a day to minimize travel distance.
        Uses nearest-neighbor heuristic for TSP-like optimization.
        """
        # Separate fixed items (transport, hotel) from optimizable items (attractions)
        fixed_items = []
        optimizable_items = []

        for item in items:
            if item.type in ("transport", "hotel", "rest"):
                fixed_items.append(item)
            else:
                optimizable_items.append(item)

        if len(optimizable_items) <= 2:
            return items  # No optimization needed

        # Optimize attraction order using nearest-neighbor
        optimized_attractions = GeoOptimizer._nearest_neighbor_tsp(optimizable_items, start_location)

        # Reconstruct the day with optimized order
        result = []
        attraction_idx = 0

        for item in items:
            if item.type in ("transport", "hotel", "rest"):
                result.append(item)
            else:
                if attraction_idx < len(optimized_attractions):
                    result.append(optimized_attractions[attraction_idx])
                    attraction_idx += 1

        return result

    @staticmethod
    def _nearest_neighbor_tsp(items: list[ItineraryItem], start: GeoPoint | None = None) -> list[ItineraryItem]:
        """
        Nearest-neighbor heuristic for TSP.
        Starts from the given location (or first item) and always visits the nearest unvisited item.
        """
        if not items:
            return []

        unvisited = items.copy()
        result = []

        # Determine starting point
        current_location = start
        if current_location is None:
            # Start from the item closest to city center or first item
            current_location = GeoPoint(lng=120.0, lat=30.0)  # Default to Hangzhou center
            if items[0].location and items[0].location.lng:
                current_location = items[0].location

        while unvisited:
            # Find nearest unvisited item
            nearest_idx = 0
            nearest_dist = float('inf')

            for i, item in enumerate(unvisited):
                if item.location:
                    dist = GeoOptimizer.haversine_distance(current_location, item.location)
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_idx = i

            # Add nearest item to result
            nearest_item = unvisited.pop(nearest_idx)
            result.append(nearest_item)

            # Update current location
            if nearest_item.location:
                current_location = nearest_item.location

        return result

    @staticmethod
    def cluster_attractions_by_location(
        attractions: list[ItineraryItem],
        n_clusters: int = 3,
    ) -> list[list[ItineraryItem]]:
        """
        Cluster attractions by geographic proximity using simple k-means-like approach.
        Returns clusters of attractions that should be visited on the same day.
        """
        if not attractions or n_clusters <= 0:
            return [attractions]

        # Filter attractions with valid coordinates
        valid_attractions = [a for a in attractions if a.location and a.location.lng and a.location.lat]

        if len(valid_attractions) <= n_clusters:
            return [[a] for a in valid_attractions]

        # Simple clustering: divide by longitude strips
        # Sort by longitude and divide into clusters
        sorted_attractions = sorted(valid_attractions, key=lambda a: a.location.lng if a.location else 0)

        cluster_size = len(sorted_attractions) // n_clusters
        clusters = []

        for i in range(n_clusters):
            start_idx = i * cluster_size
            end_idx = start_idx + cluster_size if i < n_clusters - 1 else len(sorted_attractions)
            clusters.append(sorted_attractions[start_idx:end_idx])

        return clusters

    @staticmethod
    def calculate_total_distance(items: list[ItineraryItem]) -> float:
        """Calculate total travel distance for a sequence of items"""
        total = 0.0
        prev_location = None

        for item in items:
            if item.location and item.location.lng and item.location.lat:
                if prev_location:
                    total += GeoOptimizer.haversine_distance(prev_location, item.location)
                prev_location = item.location

        return total

    @staticmethod
    def get_optimization_stats(items: list[ItineraryItem]) -> dict[str, Any]:
        """Get statistics about route optimization"""
        valid_items = [i for i in items if i.location and i.location.lng and i.location.lat]

        if len(valid_items) < 2:
            return {
                "has_coordinates": False,
                "total_distance_km": 0,
                "num_attractions": len(items),
            }

        total_distance = GeoOptimizer.calculate_total_distance(items)

        return {
            "has_coordinates": True,
            "total_distance_km": round(total_distance, 2),
            "num_attractions": len(items),
            "num_with_coordinates": len(valid_items),
            "avg_distance_km": round(total_distance / (len(valid_items) - 1), 2) if len(valid_items) > 1 else 0,
        }


geo_optimizer = GeoOptimizer()
