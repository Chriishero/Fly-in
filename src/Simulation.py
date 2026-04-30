from .Map import Location, Hub, Drone, Map, HubType
from .PathFinder import PathFinder
from pydantic import BaseModel, PrivateAttr, model_validator
from colored import Fore, Style
import numpy as np


class Simulation(BaseModel):
    """
    Handle all the simulation process by using the shortest pathfinding
    algorithm and resolve conflicts between drones.
    """
    model_config = {
        "arbitrary_types_allowed": True
    }
    map: Map
    pathfinder: PathFinder

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
        """Getter of '_state' private attribute"""
        return self._state

    @property
    def turn_count(self) -> int:
        """Getter of '_turn_count' private attribute"""
        return self._turn_count

    @property
    def current_turn(self) -> int:
        """Getter of '_current_turn' private attribute"""
        return self._current_turn

    @staticmethod
    def distance(pos1: tuple[int, int], pos2: tuple[int, int]) -> float:
        """Compute the distance between two points
        in a 2D coordinates system"""
        distance: float = np.sqrt(
            (pos2[0] - pos1[0])**2 + (pos2[1] - pos1[1])**2)
        return (distance)

    def start(self) -> None:
        """Start one iteration of the simulation, execute '_plan_turn()'
        and '_execute_turn()', or go to the next turn with 'next_step()'
        if this turn has already been compute.
        """
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
                print("Turn count:", self._turn_count)
                self._state = False

    def load_drones(self) -> None:
        """Load all the drones with 'self.map.nb_drones'
        and save them in a list."""
        for i in range(self.map.nb_drones):
            location = self.map.get_start_hub()
            location.n_drones += 1
            drone = Drone(id=i, location=location, state=True)
            drone.add_path(drone.location)
            self._drones.append(drone)

    def next_step(self) -> None:
        """Go to the next turn of the simulation,
        and if not already computed, use 'start()'"""
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
        """Go to the previous turn of the simulation"""
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
        """Plan the next location of each drone."""
        planned: dict[Drone, Location] = {}
        for drone in self._drones:
            next_loc = self.pathfinder.get_next_location(drone)
            planned[drone] = next_loc
            self._update_capacities(planned)
        self._planned_moves = planned

    def _execute_turn(self) -> None:
        """Move the drones to their planned location."""
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
        """Terminal output of the drones deplacements."""
        if curr_loc != next_loc:
            next_color = ""
            if isinstance(next_loc, Hub):
                next_color = Fore.rgb(*next_loc.color.value[1])
            print(f"D{drone.id}-",
                  next_color + next_loc.name + Style.reset, sep="")

    def _update_capacities(self, drones_loc: dict[Drone, Location]) -> None:
        """Update the 'n_drones' attribute of each location."""
        for hub in self.map.hubs:
            hub.n_drones = 0
        for conn in self.map.connections:
            conn.n_drones = 0
        for drone, loc in drones_loc.items():
            loc.n_drones += 1
        for drone in self._drones:
            if drone not in drones_loc.keys():
                drone.location.n_drones += 1
