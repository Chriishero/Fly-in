from .Simulation import Simulation
from .Map import Map, Connection
from pydantic import BaseModel, Field, PrivateAttr
from typing import Any
import pygame


class GUI(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    width: int = Field(ge=256, default=800)
    height: int = Field(ge=144, default=600)
    fps: int = Field(ge=5, default=5)
    map: Map
    simulation: Simulation

    _screen: pygame.SurfaceType = PrivateAttr()
    _surface: pygame.SurfaceType = PrivateAttr()
    _scale: float = PrivateAttr(default=1.0)
    _drone: pygame.SurfaceType = PrivateAttr()
    _clock: pygame.time.Clock = PrivateAttr()
    _state: bool = PrivateAttr(default=False)

    def init(self) -> None:
        try:
            pygame.init()
            self._screen = pygame.display.set_mode((self.width, self.height))
            self._surface = pygame.Surface((self.width, self.height))
            self._drone = pygame.image.load("resources/drone.png").convert_alpha()
            self._clock = pygame.time.Clock()
            self._state = True
        except Exception as e:
            raise ValueError(f"Failed to initialize pygame: {e}")

    def run(self) -> None:
        self.simulation.load_drones()
        while self._state is True:
            for event in pygame.event.get():
                self._on_event(event)
            self._on_loop()
            self._on_render()
        self._on_cleanup()

    def _on_event(self, event: Any) -> None:
        if event.type == pygame.QUIT:
            self._state = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.simulation.start()

    def _on_loop(self) -> None:
        pass

    def _on_render(self) -> None:
        try:
            self._surface.fill("white")
            self._draw_connection()
            self._draw_hub()
            self._draw_drone()
            scaled_surface = pygame.transform.scale(
                self._surface,
                (int(self.width * self._scale),
                 int(self.height * self._scale)))
            self._screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()
            self._clock.tick(self.fps)
        except Exception as e:
            raise ValueError(f"{e}")

    def _draw_hub(self) -> None:
        for hub in self.map.hubs:
            x, y = self._rescaling_positions(
                hub.x, hub.y,
                int(self.width / 10), int(self.height / 10)
            )
            pygame.draw.circle(
                self._surface,
                (255, 0, 0),
                (x, y),
                (self.width + self.height) / 100
            )

    def _draw_connection(self) -> None:
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
        for drone in self.simulation._drones:
            if isinstance(drone, Connection):
                d_x = drone.location.prev_hub.x + drone.next_hub.x / 2
                d_y = drone.location.prev_hub.y + drone.next_hub.y / 2
            else:
                d_x = drone.location.x
                d_y = drone.location.y
            x, y = self._rescaling_positions(
                d_x, d_y,
                int(self.width / 10), int(self.height / 10)
            )
            size_x = (self.width + self.height) / 10
            size_y = size_x
            x -= size_x / 2
            y -= size_y / 2
            picture = pygame.transform.scale(self._drone, (size_x, size_y))
            self._surface.blit(picture, (x, y))

    def _rescaling_positions(
            self, x: int, y: int,
            x_border: int, y_border: int
            ) -> tuple[int, int]:
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

    def _on_cleanup(self) -> None:
        pygame.quit()
