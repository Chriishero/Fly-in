from .Map import Hub, Connection, Drone, Map, HubType, Zone
from pydantic import BaseModel, PrivateAttr, model_validator
from typing import Union, cast
import heapq


class Simulation(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    map: Map

    _drones: list[Drone] = PrivateAttr(default_factory=list)
    _planned_moves: dict[Drone, Hub | Connection] = PrivateAttr(
        default_factory=dict)
    _turn_count: int = PrivateAttr(default=0)

    @model_validator(mode='after')
    def validator(self) -> "Simulation":
        if not all(isinstance(drone.location, Hub)
                   and drone.location.type == HubType.START
                   for drone in self._drones):
            raise ValueError("All drones must start at the start_hub.")
        return (self)

    @property
    def turn_count(self) -> int:
        return self._turn_count

    def start(self) -> None:
        if len(self._drones) == 0:
            self.load_drones()
        if not all(drone.location == self.map.get_end_hub()
                   for drone in self._drones):
            self._plan_turn()
            self._execute_turn()
        else:
            print("Turn count: ", self._turn_count)

    def load_drones(self) -> None:
        for i in range(self.map.nb_drones):
            drone = Drone(id=i, location=self.map.get_start_hub(), state=True)
            self._drones.append(drone)

    def _plan_turn(self) -> None:
        planned: dict[Drone, Hub | Connection] = {}
        for drone in self._drones:
            if drone.location != self.map.get_end_hub():
                next_loc = self._get_next_location(drone)
                drone.location.n_drones -= 1
                planned[drone] = next_loc
                next_loc.n_drones += 1
        planned = self._resolve_conflicts(planned)
        self._planned_moves = planned

    def _execute_turn(self) -> None:
        for drone, next_loc in self._planned_moves.items():
            if drone.location != self.map.get_end_hub():
                print(
                    f"Drone {drone.id}: {drone.location.name} -> "
                    f"{next_loc.name}"
                )
                drone.location = next_loc
        self._turn_count += 1

    def _get_next_location(self, drone: Drone) -> Union[Hub, Connection]:
        location = drone.location
        if isinstance(location, Connection):
            return self._next_location_from_conn(drone)
        return self._next_location_from_hub(drone)

    def _next_location_from_conn(self, drone: Drone) -> Hub:
        if isinstance(drone.location, Hub):
            return drone.location
        next = drone.location.next_hub
        prev = drone.location.prev_hub
        return (next if next.n_drones < next.max_drones else prev)

    def _next_location_from_hub(self, drone: Drone) -> Hub | Connection:
        if isinstance(drone.location, Connection):
            return drone.location
        h: list = []
        distances = {hub: float("inf") for hub in self.map.hubs}
        previous: dict[Hub, Hub | None] = {hub: None for hub in self.map.hubs}
        distances[drone.location] = 0
        """in heappush and heappop function, if two distances are equal,
        the locations of type 'Hub' will be compared, and raise an error.
        'counter' prevents that"""
        counter = 0
        heapq.heappush(h, (distances[drone.location], counter, drone.location))
        while h:
            distance, _, curr_loc = heapq.heappop(h)
            if distance > distances[curr_loc]:
                continue
            for conn in curr_loc.nexts:
                next_loc = conn.next_hub if conn.next_hub != curr_loc \
                    else conn.prev_hub
                if next_loc.n_drones >= next_loc.max_drones:
                    continue
                if next_loc.zone == Zone.blocked:
                    continue
                if distance + next_loc._get_cost() < distances[next_loc]:
                    distances[next_loc] = distance + next_loc._get_cost()
                    previous[next_loc] = curr_loc
                    counter += 1
                    heapq.heappush(h, (distances[next_loc], counter, next_loc))

        path: list[Hub] = []
        head: Hub = self.map.get_end_hub()
        while previous[head] is not None:
            path.append(head)
            head = cast(Hub, previous[head])
        path.reverse()
        if path:
            if path[0].zone == Zone.restricted:
                for conn in drone.location.nexts:
                    if conn.next_hub == path[0] or conn.prev_hub == path[0]:
                        return conn
            else:
                return path[0]
        return drone.location

    def _resolve_conflicts(
            self, planned: dict[Drone, Hub | Connection]
            ) -> dict[Drone, Hub | Connection]:
        return planned
