import pygame
import tilemap
import dialogue


class Entity:
    def __init__(self, position, current_map, entity_data):
        self.current_map = current_map
        self.data = entity_data
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
        self.delete = False

    def __lt__(self, other):
        return self.get_z() < other.get_z()

    def __gt__(self, other):
        return self.get_z() > other.get_z()

    def get_z(self):
        return self.position[0] + self.position[1]

    def get_render_pos(self):
        return self.position

    def get_height(self, camera=True):
        tile_pos = [round(self.get_render_pos()[0]), round(self.get_render_pos()[1])]
        tile_height = self.current_map.get_tile_path(tile_pos)[tilemap.TileKeys.tiles][0][tilemap.TileKeys.height]
        height = self.height + tile_height
        if camera:
            height *= tilemap.Camera.zoom
        return height

    def update(self, deltatime):
        pass

    def render(self, screen, masks=None):
        screen_pos = tilemap.path_to_screen(self.get_render_pos())
        if masks is not None and len(masks) > 0:
            masked_image = self.appearance.copy()
            for m in masks:
                # cut out portions of the character that are overlapped by terrain tiles
                offset = (m.position[0] - self.get_render_pos()[0], m.position[1] - self.get_render_pos()[1])
                offset = tilemap.path_to_screen(offset, False)
                masked_image.blit(m.image, (offset[0], offset[1] + self.get_height(False) - m.height))
            self.render_with_zoom(masked_image, screen, (screen_pos[0], screen_pos[1] - self.get_height()))
        else:
            self.render_with_zoom(self.appearance, screen, (screen_pos[0], screen_pos[1] - self.get_height()))

    def render_with_zoom(self, image, dest, dest_pos):
        zoomed = pygame.transform.scale(
            image,
            (round(self.appearance.get_width() * tilemap.Camera.zoom),
             round(self.appearance.get_height() * tilemap.Camera.zoom)),
        )
        dest.blit(zoomed, (dest_pos[0], dest_pos[1]))

    def on_highlight(self):
        pass

    def start_of_round_update(self):
        pass

    def end_of_round_update(self):
        pass


class FreeMover(Entity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)
        self.move_speed = 0.002


class InteractiveEntity(Entity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)
        message = entity_data["message"]
        font = pygame.font.SysFont(None, 36)
        message_size = font.size(message)
        print(message_size)
        self.message_image = pygame.Surface((message_size[0], message_size[1])).convert()
        self.message_image.set_colorkey(pygame.Color("black"))
        dialogue.draw_shadowed_text(
            self.message_image,
            message,
            pygame.Color("white"),
            (0, 0, message_size[0], message_size[1]),
            font,
            True
        )
        self.interaction_range = 1
        self.message_active = False
        self.interaction_active = False

        self.dialogue = None
        if "dialogue" in entity_data.keys():
            self.dialogue = dialogue.Dialogue(entity_data["dialogue"], False)

    def active_when_adjacent(self, player_pos):
        self.interaction_active = abs(player_pos[0] - self.position[0]) <= self.interaction_range and \
                                  abs(player_pos[1] - self.position[1]) <= self.interaction_range
        self.message_active = self.interaction_active

    def interact(self):
        if self.interaction_active and self.dialogue is not None:
            self.dialogue.set_active(True)
            self.message_active = False
            return True
        return False

    def notify(self, event):
        self.dialogue.notify(event)
        if not self.dialogue.active:
            self.current_map.return_control()

    def render(self, screen, masks=None):
        super().render(screen, masks)
        if self.message_active:
            location = tilemap.path_to_screen(self.get_render_pos())
            screen.blit(self.message_image, (location[0], location[1] - tilemap.tile_extent[1] * 2))

    def second_render(self, screen):
        self.dialogue.render(screen)


class DelayedSkill(Entity):
    def __init__(self, position, entity_data, skill):
        super().__init__(position, skill.current_map, entity_data)
        self.skill = skill

    def start_of_round_update(self):
        if self.skill.exec_skill(self.position):
            self.delete = True

    def on_highlight(self):
        pass
