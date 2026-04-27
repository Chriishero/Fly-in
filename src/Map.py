from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Union
from enum import Enum, auto
import numpy as np


class Zone(Enum):
    normal = auto()
    blocked = auto()
    restricted = auto()
    priority = auto()


class HubType(Enum):
    NORMAL = auto()
    START = auto()
    END = auto()


class Hub(BaseModel):
    type: HubType = Field(default=HubType.NORMAL)
    name: str = Field(min_length=1)
    x: int
    y: int
    zone: Zone = Field(default=Zone.normal)
    color: Optional[str] = Field(default=None)
    max_drones: float = Field(default=1, ge=0)
    n_drones: int = Field(default=0)
    nexts: list[Connection] = Field(default_factory=list)

    @model_validator(mode='after')
    def validator(self) -> "Hub":
        if '-' in self.name:
            raise ValueError(
                f"Invalid hub name '{self.name}': cannot contain dashes."
            )
        if (self.zone == Zone.blocked and self.max_drones > 0) \
                or (self.zone != Zone.blocked and self.max_drones == 0):
            raise ValueError(
                "Incompatible zone and max_drones attributes: "
                f"'{self.zone}', '{self.max_drones}'"
            )
        if self.type in (HubType.START, HubType.END):
            self.max_drones = float("inf")
        return self

    def __hash__(self) -> int:
        return hash(self.name)

    def _get_cost(self) -> int:
        if self.zone == Zone.restricted:
            return (2)
        return (1)


class Connection(BaseModel):
    name: str = Field(min_length=1)
    prev_hub: Hub
    next_hub: Hub
    max_link_capacity: int = Field(default=1)
    n_drones: int = Field(default=0)

    def __hash__(self) -> int:
        return hash(self.name)


class Drone(BaseModel):
    id: int
    location: Union[Hub, Connection]
    state: bool = Field(default=True)

    def __hash__(self) -> int:
        return hash(self.id)


class Map(BaseModel):
    nb_drones: int = Field(ge=1)
    hubs: list[Hub]
    connections: list[Connection]

    @model_validator(mode='after')
    def validator(self) -> "Map":
        self._check_hub_duplicates()
        self._check_connection_duplicates()
        self._load_hubs_nexts()
        return self

    def _check_hub_duplicates(self) -> None:
        for i in range(0, len(self.hubs)):
            pos1 = (self.hubs[i].x, self.hubs[i].y)
            for j in range(i + 1, len(self.hubs)):
                pos2 = (self.hubs[j].x, self.hubs[j].y)
                if pos1 == pos2:
                    raise ValueError(
                        f"Invalid hubs, hub '{self.hubs[i].name}' and "
                        f"hub '{self.hubs[j].name}' cannot be at the "
                        "same position."
                    )
                elif self.hubs[i].name == self.hubs[j].name:
                    raise ValueError(
                        "Invalid hubs, two hubs cannot have the same name."
                    )

    def _check_connection_duplicates(self) -> None:
        seen = set()
        for connection in self.connections:
            hubs = frozenset({
                connection.prev_hub.name,
                connection.next_hub.name
            })
            if hubs in seen:
                raise ValueError(
                    "Invalid map, two connections has the same hubs."
                )
            seen.add(hubs)

    def _load_hubs_nexts(self) -> None:
        for conn in self.connections:
            if conn not in conn.prev_hub.nexts:
                conn.prev_hub.nexts.append(conn)
            if conn not in conn.next_hub.nexts:
                conn.next_hub.nexts.append(conn)

    def _distance(self, hub1: Hub, hub2: Hub) -> float:
        distance = np.sqrt((hub2.x - hub1.x)**2 + (hub2.y - hub1.y)**2)
        return (distance)

    def get_start_hub(self) -> Hub:
        return next(hub for hub in self.hubs if hub.type == HubType.START)

    def get_end_hub(self) -> Hub:
        return next(hub for hub in self.hubs if hub.type == HubType.END)
