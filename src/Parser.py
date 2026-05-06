from .Map import Map, Hub, Connection, Zone, HubType
from .Color import Color
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from typing import Optional, Any
import re


class Parser(BaseModel):
    """Validate input maps files and extract all
    the value to create a Map object."""
    model_config = {
        "arbitrary_types_allowed": True
    }
    map_path: str = Field(min_length=1)

    _map_str: str = PrivateAttr(default="")
    _nb_drones: int = PrivateAttr(default=0)
    _hubs: list[Hub] = PrivateAttr(default_factory=list)
    _connections: list[Connection] = PrivateAttr(default_factory=list)
    _map: Optional[Map] = PrivateAttr(default=None)

    @model_validator(mode='after')
    def validator(self) -> 'Parser':
        """Model validator, check if the file is readable"""
        try:
            with open(self.map_path, 'r') as f:
                self._map_str = f.read()
        except FileNotFoundError as e:
            raise ValueError(e)
        return self

    @property
    def map(self) -> Optional[Map]:
        """Getter for '_map' attribute."""
        return self._map

    def parse(self) -> None:
        """Extract value from the map file"""
        hubs_regex = re.compile(
            r"^(start_hub|end_hub|hub):\s+"
            r"(\w+)\s+(-?\d+)\s+(-?\d+)\s*"
            r"(?:\[([^\]]*)\])?\s*$",
            flags=re.MULTILINE
        )
        connections_regex = re.compile(
            r"connection:\s+(\w+)-(\w+)\s*"
            r"(?:\[([^\]]*)\])?\s*$",
            flags=re.MULTILINE
        )
        map_no_comments: str = self._delete_comments(self._map_str)
        clean_map: str = self._delete_empty_line(map_no_comments)
        self._check_field(clean_map)
        self._load_nb_drones(clean_map)
        self._load_hubs(hubs_regex, clean_map)
        self._load_connections(connections_regex, clean_map)
        try:
            self._map = Map(
                nb_drones=self._nb_drones,
                hubs=self._hubs,
                connections=self._connections
            )
        except Exception as e:
            raise ValueError(f"{e}")

    def _delete_comments(self, map: str) -> str:
        """Delete comments from the map file content"""
        res: str = ""
        skip: bool = False
        for c in map:
            if c == '#':
                skip = True
            elif c == '\n':
                res += c
                skip = False
            elif skip is False:
                res += c
        return (res)

    def _delete_empty_line(self, map: str) -> str:
        """Delete empty lines from the map file content"""
        lines = map.splitlines()
        res: str = ""
        for line in lines:
            if line.strip() != "":
                res += line + "\n"
        return (res)

    def _check_field(self, map: str) -> None:
        """Check if there are only 'nb_drones', 'hub'
        'connection', 'start_hub', or 'end_hub' in
        the map fields"""
        lines = map.splitlines()
        for line in lines:
            res = line.split(":")
            if res[0] not in ("nb_drones", "hub",
                              "start_hub", "end_hub",
                              "connection"):
                l_n = self._check_line_number(
                    line, self._delete_comments(self._map_str)
                )
                raise ValueError(
                    f"Invalid field '{res[0]}' (l.{l_n})")

    def _load_nb_drones(self, map: str) -> None:
        """Extract the parameter 'nb_drones'"""
        m = re.match(r"nb_drones:\s+(\d+)\s*$", map.splitlines()[0])
        if not m:
            raise ValueError(
                "The first line must be 'nb_drones: <numbers>'"
            )
        self._check_number_of_occurences("nb_drones", map)
        try:
            self._nb_drones = int(m.group(1))
        except Exception as e:
            raise ValueError(f"{e}")

    def _load_hubs(
            self, hubs_regex: Any, map: str) -> None:
        """Extract all the hubs attributes and create them"""
        matches = list(hubs_regex.finditer(map))
        all_hub = list(re.finditer(
            r"^(start_hub|end_hub|hub):(.*)", map, flags=re.MULTILINE))
        matches_lines = {m.group(0).strip() for m in matches}
        all_hub_lines = {m.group(0).strip() for m in all_hub}
        for hub_line in all_hub_lines:
            if hub_line not in matches_lines:
                l_n = self._check_line_number(
                    hub_line, self._delete_comments(self._map_str)
                )
                raise ValueError(
                    f"Invalid hub (l.{l_n}): '{hub_line}', syntax is: \n"
                    "<hub_type>: <name> <x> <y> [<zone> <color> <max_drones>]"
                    "\nWhere [metadata] is optional."
                )
        found_any = False
        self._check_number_of_occurences("start_hub", map)
        self._check_number_of_occurences("end_hub", map)
        for match in matches:
            found_any = True
            raw = match.group(5) or ""
            tokens = raw.split()
            allowed = {"zone", "color", "max_drones"}
            zone = "normal"
            color = "red"
            max_drones = 1.0
            for token in tokens:
                l_n = self._check_line_number(
                        match.group(0), self._delete_comments(self._map_str)
                    )
                if "=" not in token:
                    l_n = self._check_line_number(
                        match.group(0), self._delete_comments(self._map_str)
                    )
                    raise ValueError(
                        f"Invalid metadata '{token}' (missing '=') (l.{l_n}).")
                key, value = token.split("=", 1)
                if key not in allowed:
                    raise ValueError(
                        f"Now invalid metadata key '{key}' (l.{l_n}). "
                        f"Allowed: {', '.join(allowed)}"
                    )
                allowed.remove(key)
                if key == "zone":
                    zone = value
                elif key == "color":
                    color = value
                elif key == "max_drones":
                    max_drones = float(value)
            parameters = {
                "name": match.group(2),
                "x": int(match.group(3)),
                "y": int(match.group(4)),
                "zone": Zone[zone],
                "color": Color.from_str(color),
                "max_drones": max_drones
            }
            if match.group(1) == "start_hub":
                hub = Hub(type=HubType.START, **parameters)
            elif match.group(1) == "end_hub":
                hub = Hub(type=HubType.END, **parameters)
            else:
                hub = Hub(type=HubType.NORMAL, **parameters)
            self._hubs.append(hub)
        if not found_any:
            raise ValueError(
                "No hub found, syntaxe is :\n"
                "<hub_type>: <name> <x> <y> [<zone> <color> <max_drones>]\n"
                "Where [metadata] is optional."
            )

    def _load_connections(
            self, connections_regex: Any, map: str) -> None:
        """Extract all the connections attributes and create them."""
        for line in map.splitlines():
            if line.startswith("connection"):
                s = line.split(":")[1]
                if "-" not in s:
                    l_n = self._check_line_number(
                        line, self._delete_comments(self._map_str)
                    )
                    raise ValueError(
                        f"Invalid connection '{line}' (l.{l_n})"
                    )
        matches = connections_regex.finditer(map)
        found_any = False
        for match in matches:
            found_any = True
            hub1 = self._get_hub(match.group(1), match.group(0))
            hub2 = self._get_hub(match.group(2), match.group(0))
            max_link_capacity = 1
            allowed = ["max_link_capacity"]
            raw = match.group(3) or ""
            tokens = raw.split()
            for token in tokens:
                l_n = self._check_line_number(
                        match.group(0), self._delete_comments(self._map_str)
                    )
                if "=" not in token:
                    l_n = self._check_line_number(
                        match.group(0), self._delete_comments(self._map_str)
                    )
                    raise ValueError(
                        f"Invalid metadata '{token}' (missing '=') (l.{l_n}).")
                key, value = token.split("=", 1)
                if key not in allowed:
                    l_n = self._check_line_number(
                        match.group(0), self._delete_comments(self._map_str)
                    )
                    raise ValueError(
                        f"Now invalid metadata key '{key}' (l.{l_n}). "
                        f"Allowed: {', '.join(allowed)}"
                    )
                allowed.remove(key)
                max_link_capacity = int(value)
            self._connections.append(
                Connection(
                    name=f"{hub1.name}-{hub2.name}",
                    prev_hub=hub1,
                    next_hub=hub2,
                    max_drones=float(max_link_capacity))
            )
        if not found_any:
            raise ValueError(
                "No connection found, syntaxe is:\n"
                "connection: <hub1>-<hub2> [<max_link_capacity]\n"
                "Where [metadata] is optional."
            )

    def _get_hub(self, name: str, match: str) -> Hub:
        """Get an specific hub by its name."""
        for hub in self._hubs:
            if hub.name == name:
                return hub
        l_n = self._check_line_number(
            match, self._delete_comments(self._map_str)
        )
        raise ValueError(
            f"Invalid connection, hub '{name}' not found (l.{l_n})"
        )

    def _check_number_of_occurences(self, text: str, map: str) -> None:
        """Check if a field appear more or less than one time in the map"""
        occurences = re.findall(
            fr"^{text}:", map, flags=re.MULTILINE)
        if len(occurences) != 1:
            raise ValueError(
                f"The field '{text}' must appear exactly once."
            )

    def _check_line_number(self, text: str, map: str) -> int:
        """return the line number where a specific text is contained
        in the map file."""
        lines = map.splitlines()
        for i in range(0, len(lines), 1):
            if text in lines[i]:
                return i + 1
        return -1
