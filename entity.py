import pygame
import tilemap
import dialogue
import user_interface


class Entity:
    def __init__(self, position, current_map, entity_data):
        self.current_map = current_map
        self.data = entity_data.copy()

        # load appearance
        if "appearance" in entity_data.keys():
            # self.appearance = pygame.image.load(entity_data["appearance"]).convert()
            self.image_directory = "images/entity/" + entity_data["appearance"] + "/"
        else:
            self.image_directory = "images/entity/default/"
        self.appearance = pygame.image.load(self.image_directory + "default.png").convert()
        self.appearance.set_colorkey(pygame.Color("black"))

        # position is real gameplay position, in path coordinates
        self.position = [position[0], position[1]]
        if "height" in entity_data:
            self.height = entity_data["height"] * tilemap.tile_extent[1]
        else:
            self.height = 1.5 * tilemap.tile_extent[1]
        # determines whether you can currently command this entity
        self.ally = False
        self.accepting_input = False
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
        # tile_height = self.current_map.get_tile_path(tile_pos)[tilemap.TileKeys.tiles][0][tilemap.TileKeys.height]
        tile_height = 0
        height = self.height + tile_height
        if camera:
            height *= tilemap.Camera.zoom
        return height

    def update(self, deltatime):
        pass

    def render(self, screen, masks=None):
        if self.appearance is not None:
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

    def active_when_adjacent(self, player_pos):
        self.interaction_active = abs(player_pos[0] - self.position[0]) <= self.interaction_range and \
                                  abs(player_pos[1] - self.position[1]) <= self.interaction_range
        self.message_active = self.interaction_active

    def interact(self):
        return self.interaction_active

    def notify(self, event):
        pass

    def render(self, screen, masks=None):
        super().render(screen, masks)
        if self.message_active:
            location = tilemap.path_to_screen(self.get_render_pos())
            screen.blit(self.message_image, (location[0], location[1] - tilemap.tile_extent[1] * 2))

    def second_render(self, screen):
        pass


class NPC(InteractiveEntity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)

        self.dialogue = None
        if "dialogue" in entity_data.keys():
            self.dialogue = dialogue.Dialogue(entity_data["dialogue"], False)

    def notify(self, event):
        if dialogue is not None:
            self.dialogue.notify(event)
            if not self.dialogue.active:
                self.current_map.return_control()

    def interact(self):
        if self.interaction_active and self.dialogue is not None:
            self.dialogue.set_active(True)
            self.message_active = False
            return True
        return False

    def second_render(self, screen):
        self.dialogue.render(screen)


class MenuEntity(InteractiveEntity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)
        self.inventory_interface = None

    def notify(self, event):
        if self.inventory_interface.notify(event) is False:
            self.set_menu_active(False)

    def interact(self):
        if self.interaction_active and not self.inventory_interface.active:
            self.set_menu_active(True)
            return True
        return False

    def set_menu_active(self, active):
        self.message_active = not active
        self.inventory_interface.set_active(active)

    def second_render(self, screen):
        self.inventory_interface.render(screen)


class EmbarkLocation(MenuEntity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)
        self.inventory_interface = user_interface.EmbarkInterface()

    def notify(self, event):
        mode = self.inventory_interface.notify(event)
        if mode is False:
            self.set_menu_active(False)
        elif mode is not None:
            self.current_map.change_mode(mode)


class Armory(MenuEntity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)
        self.inventory_interface = user_interface.ArmoryInterface()


class DelayedSkill(Entity):
    def __init__(self, position, entity_data, skill):
        super().__init__(position, skill.current_map, entity_data)
        self.skill = skill
        self.repeated = self.skill.has_tag("repeated")
        self.duration = skill.data["duration"]
        self.age = 0

    def start_of_round_update(self):
        if not self.delete:
            self.age += 1
            if self.age > self.duration:
                self.skill.exec_skill(self.position)
                self.delete = True
            elif self.repeated:
                self.skill.exec_skill(self.position)

    def on_highlight(self):
        pass
