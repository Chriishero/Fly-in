from pydantic import BaseModel, Field, model_validator
from typing import Optional
from enum import Enum, auto


class Zone(Enum):
    normal = auto()
    blocked = auto()
    restricted = auto()
    priority = auto()


class Hub(BaseModel):
    model_config = {
        "frozen": True,
    }
    name: str = Field(min_length=1)
    x: int
    y: int
    zone: Zone = Field(default=Zone.normal)
    color: Optional[str] = Field(default=None)
    max_drones: int = Field(default=1, ge=0)

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
        return self


class Connection(BaseModel):
    model_config = {
        "frozen": True,
    }
    first_hub: Hub
    second_hub: Hub
    max_link_capacity: int = Field(default=1)


class Map(BaseModel):
    nb_drones: int = Field(ge=1)
    start_hub: Hub
    end_hub: Hub
    hubs: list[Hub] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)

    @model_validator(mode='after')
    def validator(self) -> "Map":
        start_pos = (self.start_hub.x, self.start_hub.y)
        end_pos = (self.end_hub.x, self.end_hub.y)
        if start_pos == end_pos:
            raise ValueError(
                "Invalid map, start_hub and end_hub cannot "
                "be at the same position."
            )
        self._check_hub_duplicates()
        self._check_connection_duplicates()
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
                connection.first_hub.name,
                connection.second_hub.name
            })
            if hubs in seen:
                raise ValueError(
                    "Invalid map, two connections has the same hubs."
                )
            seen.add(hubs)
