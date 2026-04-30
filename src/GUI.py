from .Simulation import Simulation
from .Map import Map, Connection, Hub
from pydantic import BaseModel, Field, PrivateAttr
from typing import Any
import numpy as np
import pygame


class InformationRect(BaseModel):
    """Contains all necessary information
    to show hub/connection informations"""
    model_config = {
        "arbitrary_types_allowed": True
    }
    text: str = Field(min_length=1)
    x: int
    y: int
    rect: pygame.Rect


class GUI(BaseModel):
    """Create and handle a pygame window"""
    model_config = {
        "arbitrary_types_allowed": True
    }
    width: int = Field(ge=256, default=800)
    height: int = Field(ge=144, default=600)
    fps: int = Field(ge=5, default=5)
    map: Map
    simulation: Simulation
    drone_size_scaling_factor: float = Field(ge=0, default=0.01)

    _screen: pygame.SurfaceType = PrivateAttr()
    _surface: pygame.SurfaceType = PrivateAttr()
    _scale: float = PrivateAttr(default=1.0)
    _drone: pygame.SurfaceType = PrivateAttr()
    _clock: pygame.time.Clock = PrivateAttr()
    _state: bool = PrivateAttr(default=False)
    _drone_size: tuple[int, int] = PrivateAttr(default=(0, 0))
    _auto_simulation: bool = PrivateAttr(default=False)
    _hubs_object: dict[Hub, dict[str, Any]] = PrivateAttr(default_factory=dict)
    _information_rect: InformationRect | None = PrivateAttr(default=None)

    def init(self) -> None:
        """Initialize pygame and all the necessary
        attribute"""
        try:
            pygame.init()
            self._screen = pygame.display.set_mode((self.width, self.height))
            self._surface = pygame.Surface((self.width, self.height))
            self._drone = pygame.image.load(
                "resources/drone.png").convert_alpha()
            self._drone_size = (
                int(self.width * self.drone_size_scaling_factor),
                int(self.height * self.drone_size_scaling_factor))
            self._clock = pygame.time.Clock()
            self._state = True
        except Exception as e:
            raise ValueError(f"Failed to initialize pygame: {e}")

    def run(self) -> None:
        """Launch the window"""
        self.simulation.load_drones()
        while self._state is True:
            for event in pygame.event.get():
                self._on_event(event)
            self._on_loop()
            self._on_render()
        self._on_cleanup()

    def _on_event(self, event: Any) -> None:
        """Handle all event, keydown, mouseclick and quit"""
        if event.type == pygame.QUIT:
            self._state = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._auto_simulation = not self._auto_simulation
            if event.key == pygame.K_RIGHT:
                self.simulation.next_step()
            if event.key == pygame.K_LEFT:
                self.simulation.previous_step()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._information_rect = None
            mouse_pos = pygame.mouse.get_pos()
            self._load_hub_information(mouse_pos)
            self._load_connection_information(mouse_pos)

    def _on_loop(self) -> None:
        """Run the simulation"""
        if self.simulation.current_turn == self.simulation.turn_count \
                and self.simulation.state is False:
            self._auto_simulation = False
        if self._auto_simulation is True:
            self.simulation.start()

    def _on_render(self) -> None:
        """Render the hubs, connections, drones and
        information rect."""
        try:
            self._surface.fill("white")
            self._draw_connection()
            self._draw_hub()
            self._draw_drone()
            self._draw_information_rect()
            self._show_turn_count()
            scaled_surface = pygame.transform.scale(
                self._surface,
                (int(self.width * self._scale),
                 int(self.height * self._scale)))
            self._screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()
            self._clock.tick(self.fps)
        except Exception as e:
            raise ValueError(f"{e}")

    def _on_cleanup(self) -> None:
        """Call pygame.quit()"""
        pygame.quit()

    def _load_hub_information(self, position: tuple[int, int]) -> None:
        """Load an hub informations when clicking on it"""
        for hub in self.map.hubs:
            h_pos = self._hubs_object[hub]['position']
            h_radius = self._hubs_object[hub]['radius']
            if self.simulation.distance(position, h_pos) <= h_radius:
                zones = ["priority", "normal", "restricted", "blocked"]
                text = (f"Hub '{hub.name}':\n"
                        f"- Type: {hub.type.value}\n"
                        f"- Position: {hub.x}, {hub.y}\n"
                        f"- Zone: {zones[hub.zone.value]}\n"
                        f"- Occupancy: {hub.n_drones}/{hub.max_drones:.0f}"
                        )
                w, h = self.width / 5, self.height / 5
                x, y = h_pos[0], h_pos[1] - h
                if h_pos[0] + w > self.width:
                    x = h_pos[0] - w
                if h_pos[1] - h < 0:
                    y = h_pos[1]
                self._information_rect = InformationRect(
                    text=text,
                    x=x,
                    y=y,
                    rect=pygame.Rect(x, y, w, h))

    def _load_connection_information(self, position: tuple[int, int]) -> None:
        """Load a connection informations when clicking on it"""
        if self._information_rect is not None:
            return
        for conn in self.map.connections:
            c_start_pos = self._hubs_object[conn.prev_hub]['position']
            c_end_pos = self._hubs_object[conn.next_hub]['position']
            c_width = self._hubs_object[conn.prev_hub]['radius'] / 2
            if self._distance_point_line(
                    position, c_start_pos, c_end_pos) <= c_width:
                t = self._is_between_point(position, c_start_pos, c_end_pos)
                if t < 0 or t > 1:
                    continue
                text = (f"Connection:\n"
                        f"- First hub: {conn.prev_hub.name}\n"
                        f"- Second hub: {conn.next_hub.name}\n"
                        f"- Occupancy: {conn.n_drones}/{conn.max_drones:.0f}")
                w, h = self.width / 3, self.height / 5
                x, y = position[0], position[1] - h
                if position[0] + w > self.width:
                    x = position[0] - w
                if position[1] - h < 0:
                    y = position[1]
                self._information_rect = InformationRect(
                    text=text,
                    x=int(x),
                    y=int(y),
                    rect=pygame.Rect(x, y, w, h))

    def _distance_point_line(
            self, p_pos: tuple[int, int], start_pos: tuple[int, int],
            end_pos: tuple[int, int]) -> float:
        """Compute the distance of a point from a line"""
        P = np.array(p_pos)
        A = np.array(start_pos)
        B = np.array(end_pos)
        num = np.abs(np.cross(B - A, A - P))
        denom = self.simulation.distance(end_pos, start_pos)
        return float(num / denom)

    def _is_between_point(
            self, p_pos: tuple[int, int], start_pos: tuple[int, int],
            end_pos: tuple[int, int]) -> float:
        """Check if a point is between two others and
        return a value, between 0 and 1 if its the case."""
        P = np.array(p_pos)
        A = np.array(start_pos)
        B = np.array(end_pos)
        num = np.dot(P - A, B - A)
        denom = np.dot(B - A, B - A)
        return num / denom

    def _draw_hub(self) -> None:
        """Draw all the hubs on the surface"""
        for hub in self.map.hubs:
            if hub not in self._hubs_object.keys():
                x, y = self._rescaling_positions(
                    hub.x, hub.y,
                    int(self.width / 10), int(self.height / 10)
                )
                radius = (self.width + self.height) / 100
                self._hubs_object[hub] = {'position': None, 'radius': None}
                self._hubs_object[hub]['position'] = x, y
                self._hubs_object[hub]['radius'] = radius
            pygame.draw.circle(
                self._surface,
                hub.color.value[1],
                self._hubs_object[hub]['position'],
                self._hubs_object[hub]['radius']
            )

    def _draw_connection(self) -> None:
        """Draw all the connection on the surface"""
        for conn in self.map.connections:
            x_start, y_start = self._rescaling_positions(
                conn.prev_hub.x, conn.prev_hub.y,
                int(self.width / 10), int(self.height / 10)
            )
            x_end, y_end = self._rescaling_positions(
                conn.next_hub.x, conn.next_hub.y,
                int(self.width / 10), int(self.height / 10)
            )
            pygame.draw.line(
                self._surface,
                (0, 0, 0),
                (x_start, y_start),
                (x_end, y_end)
            )

    def _draw_drone(self) -> None:
        """Draw all the drones on their current location"""
        for drone in self.simulation._drones:
            x, y = 0.0, 0.0
            if isinstance(drone.location, Connection):
                prev_hub = drone.location.prev_hub
                prev_x, prev_y = self._rescaling_positions(
                    prev_hub.x, prev_hub.y,
                    *self._drone_size
                )
                next_hub = drone.location.next_hub
                next_x, next_y = self._rescaling_positions(
                    next_hub.x, next_hub.y,
                    *self._drone_size
                )
                x = (prev_x + next_x) / 2
                y = (prev_y + next_y) / 2
            elif isinstance(drone.location, Hub):
                d_x = drone.location.x
                d_y = drone.location.y
                x, y = self._rescaling_positions(
                    d_x, d_y,
                    *self._drone_size
                )
            size_x = (self.width + self.height) / 10
            size_y = size_x
            x -= size_x / 2
            y -= size_y / 2
            picture = pygame.transform.scale(self._drone, (size_x, size_y))
            self._surface.blit(picture, (x, y))

    def _draw_information_rect(self) -> None:
        """Draw the information rect if clicking on a hub/connection"""
        if self._information_rect is None:
            return
        x, y = self._information_rect.x, self._information_rect.y
        pygame.draw.rect(
            self._surface,
            (128, 128, 128),
            self._information_rect.rect
        )
        font_size = 20
        font = pygame.font.SysFont(None, font_size)
        lines = self._information_rect.text.splitlines()
        for i in range(len(lines)):
            info_text = font.render(lines[i], True, (0, 0, 0))
            self._surface.blit(info_text, (x + 10, y + font_size * i + 10))

    def _rescaling_positions(
            self, x: float, y: float,
            x_border: int, y_border: int
            ) -> tuple[int, int]:
        """Recale the position extracting from the map file
        to position between 0, 0 and W, H"""
        x_max = max(hub.x for hub in self.map.hubs)
        x_min = min(hub.x for hub in self.map.hubs)
        y_max = max(hub.y for hub in self.map.hubs)
        y_min = min(hub.y for hub in self.map.hubs)
        range_x = x_max - x_min
        range_y = y_max - y_min
        width = self.width - 2 * x_border
        height = self.height - 2 * y_border
        if range_x == 0:
            x_scaled = width / 2
        else:
            x_scaled = (x - x_min) * (width / range_x)
        if range_y == 0:
            y_scaled = height / 2
        else:
            y_scaled = (y - y_min) * (height / range_y)
        x_scaled += x_border
        y_scaled += y_border
        return (int(x_scaled), int(y_scaled))

    def _show_turn_count(self) -> None:
        """Show the turn count on the screen"""
        font = pygame.font.SysFont(None, 30)
        turn_text = (
            f"{self.simulation.current_turn}/{self.simulation.turn_count}"
        )
        render_text = font.render(turn_text, True, (0, 0, 0))
        self._surface.blit(render_text, (0 + 10, 0 + 10))
