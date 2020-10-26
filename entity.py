import pygame
import tilemap

# entity is an object that renders to the map and does not move


class Entity:

    def __init__(self, position, entity_data):
        # load appearance
        self.appearance = pygame.image.load(entity_data["appearance"]).convert()
        self.appearance.set_colorkey(pygame.Color("black"))
        # position is real gameplay position, in path coordinates
        self.position = [position[0], position[1]]
        self.height = entity_data["height"] * tilemap.tile_extent[1]
        # determines whether you can currently command this entity
        self.ally = False
        self.accepting_input = False
        self.intelligent = False

    def __lt__(self, other):
        return self.get_z() < other.get_z()

    def __gt__(self, other):
        return self.get_z() > other.get_z()

    def get_z(self):
        return self.position[0] + self.position[1]

    def get_render_pos(self):
        return self.position

    def upkeep(self, deltatime):
        pass

    def render(self, screen, masks=None):
        screen_pos = tilemap.path_to_screen(self.position)
        screen.blit(self.appearance, (screen_pos[0], screen_pos[1] - self.height))
