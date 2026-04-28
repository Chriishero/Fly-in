from .Map import Location, Hub, Connection, Drone, Map, HubType, Zone
from pydantic import BaseModel, PrivateAttr, model_validator
from typing import cast
from colored import Fore, Style
from collections import defaultdict
import heapq
import numpy as np


class Simulation(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    map: Map

    _state: bool = PrivateAttr(default=True)
    _drones: list[Drone] = PrivateAttr(default_factory=list)
    _planned_moves: dict[Drone, Location] = PrivateAttr(
        default_factory=dict)
    _turn_count: int = PrivateAttr(default=0)
    _current_turn: int = PrivateAttr(default=0)

    @model_validator(mode='after')
    def validator(self) -> "Simulation":
        if not all(isinstance(drone.location, Hub)
                   and drone.location.type == HubType.START
                   for drone in self._drones):
            raise ValueError("All drones must start at the start_hub.")
        return (self)

    @property
    def state(self) -> bool:
        return self._state

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def current_turn(self) -> int:
        return self._current_turn

    @staticmethod
    def distance(pos1: tuple[int, int], pos2: tuple[int, int]) -> int:
        distance = np.sqrt((pos2[0] - pos1[0])**2 + (pos2[1] - pos1[1])**2)
        return (distance)

    def start(self) -> None:
        if len(self._drones) == 0:
            self.load_drones()
        if self._current_turn < self._turn_count:
            self.next_step()
        elif self._state is True:
            if not all(drone.location == self.map.get_end_hub()
                       for drone in self._drones):
                self._plan_turn()
                self._execute_turn()
            else:
                print("Turn count: ", self._turn_count)
                self._state = False

    def load_drones(self) -> None:
        for i in range(self.map.nb_drones):
            location = self.map.get_start_hub()
            location.n_drones += 1
            drone = Drone(id=i, location=location, state=True)
            drone.add_path(drone.location)
            self._drones.append(drone)

    def next_step(self) -> None:
        if self._current_turn < self._turn_count:
            self._current_turn += 1
            for drone in self._drones:
                self._print_deplacement(
                    drone,
                    drone.location,
                    drone.to_next_location())
                drones_loc = {drone: drone.location for drone in self._drones}
                self._update_capacities(drones_loc)
        elif self._current_turn == self._turn_count and self._state is True:
            self.start()

    def previous_step(self) -> None:
        if self._current_turn > 0:
            self._current_turn -= 1
            for drone in self._drones:
                self._print_deplacement(
                    drone,
                    drone.location,
                    drone.to_previous_location())
                drones_loc = {drone: drone.location for drone in self._drones}
                self._update_capacities(drones_loc)

    def _plan_turn(self) -> None:
        planned: dict[Drone, Location] = {}
        for drone in self._drones:
            next_loc = self._get_next_location(drone)
            planned[drone] = next_loc
            self._update_capacities(planned)
        self._planned_moves = planned

    def _execute_turn(self) -> None:
        for drone, next_loc in self._planned_moves.items():
            if drone.location != self.map.get_end_hub() and \
                    drone.location != next_loc:
                self._print_deplacement(
                    drone,
                    drone.location,
                    next_loc)
            drone.prev_location = drone.location
            drone.add_path(next_loc)
            drone.to_next_location()
        self._turn_count += 1
        self._current_turn += 1

    def _print_deplacement(
            self,
            drone: Drone,
            curr_loc: Location,
            next_loc: Location) -> None:
        if curr_loc != next_loc:
            curr_color = ""
            next_color = ""
            if isinstance(curr_loc, Hub):
                curr_color = Fore.rgb(*curr_loc.color.value[1])
            if isinstance(next_loc, Hub):
                next_color = Fore.rgb(*next_loc.color.value[1])
            print(f"Drone {drone.id}:",
                  curr_color + curr_loc.name + Style.reset,
                  "->", next_color + next_loc.name + Style.reset)

    def _update_capacities(self, drones_loc: dict[Drone, Location]) -> None:
        for hub in self.map.hubs:
            hub.n_drones = 0
        for conn in self.map.connections:
            conn.n_drones = 0
        for drone, loc in drones_loc.items():
            loc.n_drones += 1
        for drone in self._drones:
            if drone not in drones_loc.keys():
                drone.location.n_drones += 1

    def _get_next_location(self, drone: Drone) -> Location:
        location = drone.location
        if location == self.map.get_end_hub():
            return location
        if isinstance(location, Connection):
            return self._next_location_from_conn(drone)
        return self._next_location_from_hub(drone)

    def _next_location_from_conn(self, drone: Drone) -> Hub:
        if not isinstance(drone.location, Connection):
            return cast(Hub, drone.location)
        next = drone.location.next_hub
        prev = drone.location.prev_hub
        if next == drone.prev_location and prev.n_drones < prev.max_drones:
            return prev
        return (next if next.n_drones < next.max_drones else prev)

    def _next_location_from_hub(self, drone: Drone) -> Location:
        if not isinstance(drone.location, Hub):
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
                if next_loc.n_drones >= next_loc.max_drones \
                        and next_loc.zone != Zone.restricted:
                    continue
                if next_loc.zone == Zone.blocked:
                    continue
                if distance + next_loc._get_cost() < distances[next_loc]:
                    distances[next_loc] = distance + next_loc._get_cost()
                    previous[next_loc] = curr_loc
                    counter += 1
                    heapq.heappush(h, (distances[next_loc], counter, next_loc))

        path: list[Hub] = []
        end = self.map.get_end_hub()
        head: Hub = drone.location
        for hub, prev in previous.items():
            d1 = Simulation.distance((hub.x, hub.y), (end.x, end.y))
            d2 = Simulation.distance((head.x, head.y), (end.x, end.y))
            if d1 < d2 and prev is not None:
                head = hub
        while previous[head] is not None:
            path.append(head)
            head = cast(Hub, previous[head])
        path.reverse()
        if path:
            if path[0].zone == Zone.restricted:
                for conn in drone.location.nexts:
                    if conn.next_hub == path[0] or conn.prev_hub == path[0]:
                        if conn.n_drones < conn.max_drones:
                            print(f"drone {drone.id} in conn for restricted")
                            return conn
            else:
                return path[0]
        return drone.location
