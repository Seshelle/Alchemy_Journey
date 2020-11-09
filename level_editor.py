import pygame
import tilemap
from tilemap import TileKeys
import json


class LevelEditor(tilemap.TileMap):
    def __init__(self, filename):
        super().__init__(filename)
        self.scene = None
        self.interface.set_button_active("end turn", False)
        self.interface.add_button((0.9, 0.95, 0.15, 0.05), "Save", "save")
        self.chosen_tile = 0
        self.layer = 0
        self.chosen_height = 0
        self.walkable = True
        self.los = True

        self.painting = False

    def update(self, deltatime, screen):
        prev_coords = [0, 0]
        if self.mouse_coords is not None:
            prev_coords = [self.mouse_coords[0], self.mouse_coords[1]]
        super().update(deltatime, screen)
        mouse_change = prev_coords != self.mouse_coords
        mouse_pos = tilemap.path_to_screen(self.mouse_coords)
        if self.chosen_tile != -1:
            screen.blit(self.ground_tiles[self.chosen_tile], (mouse_pos[0], mouse_pos[1] - self.chosen_height))

        if mouse_change and self.painting:
            self.edit_tile()
        if not self.walkable or not self.los:
            if not self.los:
                tint = self.green_tile_tint
                attribute = TileKeys.line_of_sight
            else:
                tint = self.red_tile_tint
                attribute = TileKeys.walkable
            tint_pos = tilemap.path_to_screen(self.mouse_coords)
            screen.blit(tint, tint_pos, special_flags=pygame.BLEND_ADD)
            for x in range(self.map_width):
                for y in range(self.map_height):
                    if not self.get_tile_attributes((x, y))[attribute]:
                        screen.blit(tint, tilemap.map_to_screen((x, y)), special_flags=pygame.BLEND_ADD)

    def notify(self, event):

        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "save":
                with open("data/tutorial_map.json", 'w') as map_file:
                    json.dump(self.tile_list, map_file, separators=(',', ':'))
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.painting = True
                self.edit_tile()
            elif event.button == 2:
                # copy the tile id at current mouse position and layer
                mouse_pos = tilemap.screen_to_path(pygame.mouse.get_pos())
                mouse_pos = tilemap.path_to_map(mouse_pos)
                self.chosen_tile = self.get_tile_attributes(mouse_pos)[TileKeys.tiles][self.layer][TileKeys.id]

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.painting:
                self.painting = False
                self.create_background()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.chosen_tile += 1
                if self.chosen_tile >= len(self.ground_tiles):
                    self.chosen_tile = -1
            elif event.key == pygame.K_LEFT:
                self.chosen_tile -= 1
                if self.chosen_tile < -1:
                    self.chosen_tile = len(self.ground_tiles) - 1
            elif event.key == pygame.K_UP:
                self.chosen_height += tilemap.tile_extent[1] / 4
            elif event.key == pygame.K_DOWN:
                self.chosen_height -= tilemap.tile_extent[1] / 4
            elif event.key == pygame.K_SPACE:
                if self.walkable and self.los:
                    self.walkable = False
                elif not self.walkable and self.los:
                    self.los = False
                else:
                    self.walkable = True
                    self.los = True
            elif event.key == pygame.K_1:
                self.layer = 0
            elif event.key == pygame.K_2:
                self.layer = 1

    def edit_tile(self):
        mouse_pos = tilemap.screen_to_path(pygame.mouse.get_pos())
        if self.in_bounds(mouse_pos, False):
            mouse_tile = tuple(tilemap.path_to_map(mouse_pos))

            tile_list = self.get_tile_attributes(mouse_tile)[TileKeys.tiles]
            if self.layer >= len(tile_list):
                if self.chosen_tile >= 0:
                    tile_list.append({
                        TileKeys.id: self.chosen_tile,
                        TileKeys.height: self.chosen_height
                    })
            else:
                tile_list[self.layer] = {
                    TileKeys.id: self.chosen_tile,
                    TileKeys.height: self.chosen_height}

            tile_data = {
                TileKeys.tiles: tile_list,
                TileKeys.walkable: self.walkable,
                TileKeys.line_of_sight: self.los
            }
            self.set_tile_attributes(mouse_tile, tile_data)

    def add_entities(self, filename):
        pass

    def move_camera_in_bounds(self):
        pass
