"""North-up maps and authored wayfinding signs for the desktop renderer."""
import pygame
from pygame import Vector2

from shroud import interface as UI
from shroud import settings as S

FLOOR = (90, 108, 95)
BORDER = (82, 91, 76)
ENEMY = (247, 139, 114)
SEAL = (255, 221, 133)
EXIT = (161, 221, 181)
REFUGE = (145, 193, 235)


class RoomMap:
    """Fit a whole room into a reserved rectangle, keeping both axes at the same scale."""

    def __init__(self, room, area, *, compact):
        self.compact = compact
        self.scale = min(area.width / room.bounds.width, area.height / room.bounds.height)
        size = tuple(round(side * self.scale) for side in room.bounds.size)
        self.frame = pygame.Rect((0, 0), size)
        self.frame.center = area.center
        self.terrain = pygame.Surface(size)
        self.terrain.fill(UI.INK)
        for x, y in room.tiles:
            tile = pygame.FRect(x * S.TILE_SIZE, y * S.TILE_SIZE, S.TILE_SIZE, S.TILE_SIZE)
            pygame.draw.rect(self.terrain, FLOOR, self.rect(tile))
        for wall in room.static_walls:
            pygame.draw.rect(self.terrain, UI.INK, self.rect(wall))

    def rect(self, world_rect):
        # Round common edges once so adjacent floor tiles meet even at a fractional scale.
        x, y = round(world_rect.left * self.scale), round(world_rect.top * self.scale)
        return pygame.Rect(x, y, max(1, round(world_rect.right * self.scale) - x),
                           max(1, round(world_rect.bottom * self.scale) - y))

    def point(self, position):
        return Vector2(self.frame.topleft) + Vector2(position) * self.scale

    def draw(self, surface, world):
        room = world.room
        surface.blit(self.terrain, self.frame)
        for name, gate in room.gates:
            if name not in room.open_gates:
                pygame.draw.rect(surface, SEAL, self.rect(gate).move(self.frame.topleft))
        for cover in room.bamboo:
            if not cover.broken:
                pygame.draw.rect(surface, UI.SAGE, self.rect(cover.footprint).move(self.frame.topleft))
        for checkpoint in room.data.get("checkpoints", []):
            pos = self.point(Vector2(checkpoint["spawn"]) * S.TILE_SIZE)
            pygame.draw.circle(surface, REFUGE, pos, 2 if self.compact else 5, 1)
        exit_box = self.rect(room.exit_rect).move(self.frame.topleft)
        pygame.draw.rect(surface, EXIT, exit_box, 1 if self.compact else 3)
        for enemy in world.enemies:
            if enemy.alive and room.rules.visible_enemy(world.player.position, enemy.position):
                pos = self.point(enemy.position)
                pygame.draw.circle(surface, UI.INK, pos, 4 if self.compact else 6)
                pygame.draw.circle(surface, ENEMY, pos, 3 if self.compact else 4)
                if not self.compact and any(name == enemy.group for name, _ in room.gates):
                    pygame.draw.circle(surface, SEAL, pos, 7, 1)
        player_marker(surface, self.point(world.player.position), 5 if self.compact else 8)


def player_marker(surface, pos, size):
    x, y = pos
    points = [(x, y - size), (x + size, y), (x, y + size), (x - size, y)]
    pygame.draw.polygon(surface, UI.PAPER, points)
    pygame.draw.polygon(surface, UI.INK, points, 1)


def sign_art(rows):
    """Build both directional planks together so each route gets equal prominence."""
    labels = [UI.rendered(label, 21, UI.PAPER, True) for _, label in rows]
    width = max(label.get_width() for label in labels) + 54
    height = len(rows) * 31
    image = pygame.Surface((width, height + 35), pygame.SRCALPHA)
    pygame.draw.ellipse(image, (23, 26, 22, 95), (width//2-18, height+25, 37, 9))
    pygame.draw.rect(image, (76, 56, 40), (width//2-5, 3, 10, height+26))
    for i, ((direction, _), label) in enumerate(zip(rows, labels)):
        y = i * 31
        plank = [(4,y+1),(width-6,y),(width-1,y+5),(width-3,y+27),(7,y+30),(0,y+24)]
        pygame.draw.polygon(image, (57, 50, 39), plank)
        pygame.draw.lines(image, (148, 122, 84), False, plank[:3], 2)
        pygame.draw.rect(image, UI.RED, (8, y+4, 22, 22), border_radius=2)
        bearing = UI.rendered(direction[0].upper(), 18, UI.PAPER, True)
        image.blit(bearing, bearing.get_rect(center=(19, y+15)))
        image.blit(label, (39, y+(30-label.get_height())//2))
    return image
