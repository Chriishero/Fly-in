from .Map import Location, Hub, Connection, Map, Zone, Drone
from pydantic import BaseModel, Field
from typing import cast
import heapq
import numpy as np


class PathFinder(BaseModel):
    """Class containing all the necessary functions to find the
    complete path of all drones."""
    model_config = {
        "arbitrary_types_allowed": True
    }
    map: Map
    first_iter: bool = Field(default=True)

    def get_next_location(self, drone: Drone) -> Location:
        """Get the next location of a specific drone."""
        location = drone.location
        if location == self.map.get_end_hub():
            return location
        if isinstance(location, Connection):
            return self._next_location_from_conn(drone)
        return self._get_next_location_from_hub(drone)

    def _get_next_location_from_hub(self, drone: Drone) -> Location:
        """If the drone is actually located on an hub, use A*
        to find the next location."""
        if not isinstance(drone.location, Hub):
            return drone.location
        start = drone.location
        end = self.map.get_end_hub()
        prev_forward = self._a_star_search(drone=drone, from_end=False)
        if self.first_iter is True and prev_forward[end] is None:
            raise ValueError(
                "Invalid map, not solvable."
            )
        self.first_iter = False
        if prev_forward[end] is not None:
            return self._reconstruct_next_step(start, end, prev_forward, drone)
        reachable = [
            h for h in self.map.hubs
            if prev_forward[h] is not None
        ]
        if len(reachable) == 0:
            return drone.location
        best = min(
            reachable,
            key=lambda h: self._euclidian_distance(h, end)
        )
        return self._reconstruct_next_step(start, best, prev_forward, drone)

    def _next_location_from_conn(self, drone: Drone) -> Hub:
        """If the drone is in a connection, chose between
        the previous and the next hub for its next location."""
        if not isinstance(drone.location, Connection):
            return cast(Hub, drone.location)
        next = drone.location.next_hub
        prev = drone.location.prev_hub
        if next == drone.prev_location and prev.n_drones < prev.max_drones:
            return prev
        return (next if next.n_drones < next.max_drones else prev)

    def _a_star_search(
            self, drone: Drone, from_end: bool
            ) -> dict[Hub, Hub | None]:
        """A* algorithm that return a 'previous' dict."""
        open_list: list[tuple[float, int, int, Hub]] = []
        start = cast(Hub, drone.location)
        end = self.map.get_end_hub()
        if from_end is True:
            origin = end
            target = start
        else:
            origin = start
            target = end
        g_score = {hub: float("inf") for hub in self.map.hubs}
        f_score = {hub: float("inf") for hub in self.map.hubs}
        prev: dict[Hub, Hub | None] = {hub: None for hub in self.map.hubs}

        g_score[origin] = 0
        f_score[origin] = self._euclidian_distance(origin, target)
        counter = 0
        heapq.heappush(
            open_list, (f_score[origin], origin.zone.value, counter, origin)
        )
        while open_list:
            f, _, _, loc = heapq.heappop(open_list)
            if f > f_score[loc]:
                continue
            for conn in loc.nexts:
                next_loc = conn.next_hub if conn.next_hub != loc \
                    else conn.prev_hub
                if next_loc.zone == Zone.blocked:
                    continue
                if from_end is False \
                        and next_loc.n_drones >= next_loc.max_drones \
                        and next_loc.zone != Zone.restricted:
                    continue
                g_new = g_score[loc] + next_loc.get_cost()
                h = 0
                f_new = g_new + h
                if g_new < g_score[next_loc]:
                    g_score[next_loc] = g_new
                    f_score[next_loc] = f_new
                    prev[next_loc] = loc
                    counter += 1
                    heapq.heappush(
                        open_list,
                        (f_new, next_loc.zone.value, counter, next_loc)
                    )
        return (prev)

    def _reconstruct_next_step(
            self, origin: Hub, target: Hub,
            prev: dict[Hub, Hub | None], drone: Drone
            ) -> Location:
        """Get the next location of the drone from the reversed path"""
        path: list[Hub] = []
        head: Hub | None = target
        while head is not None:
            path.append(head)
            head = prev[head]
        path.reverse()
        if len(path) < 2:
            return drone.location
        next_hub = path[1]
        if next_hub.zone == Zone.restricted:
            for conn in origin.nexts:
                if conn.next_hub == next_hub or conn.prev_hub == next_hub:
                    if conn.n_drones < conn.max_drones:
                        return (conn)
            return (drone.location)
        return next_hub

    def _distance_in_prev(
            self, prev: dict[Hub, Hub | None],
            origin: Hub, target: Hub
            ) -> float:
        """Number of hub which separate origin from target
        using 'prev' dict."""
        d = 0
        head: Hub | None = target
        while head != origin:
            head = prev[cast(Hub, head)]
            d += 1
            if head is None:
                return (float("inf"))
        return (d)

    def _euclidian_distance(self, hub1: Hub, hub2: Hub) -> float:
        """compute the euclidian distance between two hubs"""
        A = np.array([hub1.x, hub1.y])
        B = np.array([hub2.x, hub2.y])
        dist = np.linalg.norm(A - B)
        return float(dist)
