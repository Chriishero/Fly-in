from .Map import Map, Hub, Connection, Zone
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from typing import Optional, Any
import re


class Parser(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    map_path: str = Field(min_length=1)

    _map_str: str = PrivateAttr(default="")
    _nb_drones: int = PrivateAttr(default=0)
    _start_hub: Optional[Hub] = PrivateAttr(default=None)
    _end_hub: Optional[Hub] = PrivateAttr(default=None)
    _hubs: list[Hub] = PrivateAttr(default_factory=list)
    _connections: list[Connection] = PrivateAttr(default_factory=list)
    _map: Optional[Map] = PrivateAttr(default=None)

    @model_validator(mode='after')
    def validator(self) -> 'Parser':
        try:
            with open(self.map_path, 'r') as f:
                self._map_str = f.read()
        except FileNotFoundError as e:
            raise ValueError(e)
        return self

    @property
    def map(self) -> Optional[Map]:
        return self._map

    def parse(self) -> None:
        hubs_regex = re.compile(
            r"^(start_hub|end_hub|hub):\s+"
            r"(\w+)\s+(\d+)\s+(\d+)"
            r"(?:\s*"
            r"\[\s*"
            r"(?:(?:zone=(\w+)))?\s*"
            r"(?:(?:color=(\w+)))?\s*"
            r"(?:(?:max_drones=(\d+)))?\s*"
            r"\]"
            r")?"
            r"\s*$",
            flags=re.MULTILINE
        )
        map_no_comments: str = self.delete_comments()
        self._load_nb_drones(map_no_comments)
        self._load_hubs(hubs_regex, map_no_comments)
        if self._start_hub is None:
            return
        for hub in self._hubs:
            print(hub.name)
            print("  ", hub.x)
            print("  ", hub.y)
            print("  ", hub.zone)
            print("  ", hub.color)
            print("  ", hub.max_drones)

    def delete_comments(self) -> str:
        res: str = ""
        skip: bool = False
        for c in self._map_str:
            if c == '#':
                skip = True
            elif skip is False:
                res += c
            elif c == '\n':
                skip = False
        return (res)

    def _load_nb_drones(self, map: str) -> None:
        m = re.match(r"nb_drones:\s+(\d+)\s*$", map.splitlines()[0])
        if not m:
            raise ValueError(
                "The first line must be 'nb_drones: <numbers>'"
            )
        self.check_number_of_occurences("nb_drones", map)
        try:
            self._nb_drones = int(m.group(1))
        except Exception as e:
            raise ValueError(f"{e}")

    def _load_hubs(
            self, hubs_regex: Any, map: str) -> None:
        matches = hubs_regex.finditer(map)
        found_any = False

        self.check_number_of_occurences("start_hub", map)
        self.check_number_of_occurences("end_hub", map)
        for match in matches:
            found_any = True
            zone = match.group(5)
            max_drones = match.group(7)
            parameters = {
                "name": match.group(2),
                "x": int(match.group(3)),
                "y": int(match.group(4)),
                "zone": Zone.normal if zone is None else Zone[zone],
                "color": match.group(6),
                "max_drones": 1 if max_drones is None else max_drones
            }
            hub = Hub(**parameters)
            if match.group(1) == "start_hub":
                self._start_hub = hub
            elif match.group(1) == "end_hub":
                self._end_hub = hub
            else:
                self._hubs.append(hub)
        if not found_any:
            raise ValueError(
                "No hub found, syntaxe is :\n"
                "<hub_type>: <name> <x> <y> [<zone> <color> <max_drones>]\n"
                "With [metadata] optional."
            )

    def check_number_of_occurences(self, text: str, map: str) -> None:
        occurences = re.findall(fr"\b{text}\b", map)
        if len(occurences) != 1:
            raise ValueError(
                f"The field '{text}' must appear exactly once."
            )
