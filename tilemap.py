import pygame
from scenes import scenes
import game_modes
import game_state
import entity
import character
from character import CharacterKeys
import alchemy_settings as a_settings
import ai_manager
import user_interface
import math
import json
import random

tile_extent = (64, 32)


class Camera:
    speed = 0.5
    pos = [0, 0]
    zoom = 1


class TileKeys:
    tiles = "tiles"
    walkable = "walk"
    id = "id"
    height = "height"
    line_of_sight = "los"


def path_to_map(coords):
    # rotates path coordinates to map coordinates
    # map coordinates are the actual stored coordinates of tiles
    coords_map = [math.floor((coords[0] - coords[1]) / 2), coords[1] + coords[0]]
    return coords_map


def map_to_path(coords):
    # rotates map coordinates to path coordinates
    # path coordinates are what entities use for pathing and storing their position
    new_path = map_to_screen(coords)
    new_path = screen_to_path(new_path)
    new_path[0] += 1
    return new_path


def path_to_screen(path_xy, camera=True):
    # returns the screen position of a path coordinate
    screen_xy = [0, 0]
    screen_xy[0] = (path_xy[0] - path_xy[1]) * tile_extent[0]
    screen_xy[1] = (path_xy[1] + path_xy[0]) * tile_extent[1]
    if camera:
        screen_xy[0] = screen_xy[0] * Camera.zoom + Camera.pos[0]
        screen_xy[1] = screen_xy[1] * Camera.zoom + Camera.pos[1]
    return screen_xy


def map_to_screen(map_xy):
    # returns the screen position of a tile
    screen_xy = [0, 0]
    screen_xy[0] = map_xy[0] * tile_extent[0] * 2 + tile_extent[0] * (map_xy[1] % 2)
    screen_xy[1] = map_xy[1] * tile_extent[1]
    screen_xy[0] = screen_xy[0] * Camera.zoom + Camera.pos[0]
    screen_xy[1] = screen_xy[1] * Camera.zoom + Camera.pos[1]
    return screen_xy


def screen_to_path(screen_xy):
    # turns a screen position into a path coordinate
    adjust_screen = [0, 0]
    adjust_screen[0] = screen_xy[0] - Camera.pos[0]
    adjust_screen[1] = screen_xy[1] - Camera.pos[1]
    adjust_screen[0] /= Camera.zoom
    adjust_screen[1] /= Camera.zoom
    coords_xy = [0, 0]
    coords_xy[0] = math.floor((adjust_screen[0] / tile_extent[0] + adjust_screen[1] / tile_extent[1]) * 0.5 - 0.5)
    coords_xy[1] = math.floor((adjust_screen[1] / tile_extent[1] - adjust_screen[0] / tile_extent[0]) * 0.5 + 0.5)
    return coords_xy


def path_to_world(path_xy):
    return path_to_screen(path_xy, False)


def map_to_world(map_xy):
    x = (map_xy[0] * tile_extent[0] + tile_extent[1] * (map_xy[1] % 2)) * 2
    y = map_xy[1] * tile_extent[1]
    return [x, y]


def onscreen_path(path_xy):
    location = path_to_screen(path_xy)
    return onscreen(location)


def onscreen(location):
    if location[0] < 0 - tile_extent[0] * 2 or location[1] < 0 - tile_extent[1] * 2 \
            or location[0] > a_settings.display_width + tile_extent[0] * 2 \
            or location[1] > a_settings.display_height + tile_extent[1] * 2:
        return False
    return True


def distance_between(p0, p1):
    dx = abs(p0[0] - p1[0])
    dy = abs(p0[1] - p1[1])
    return (dx + dy) - 0.586 * min(dx, dy)


def supercover_line(p0, p1):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    nx = abs(dx)
    ny = abs(dy)

    if dx == 0:
        points = []
        for pos in range(ny):
            points.append([p0[0], min(p0[1], p1[1]) + pos])
        return points
    elif dx > 0:
        sign_x = 1
    else:
        sign_x = -1

    if dy == 0:
        points = []
        for pos in range(nx):
            points.append([min(p0[0], p1[0]) + pos, p0[1]])
        return points
    elif dy > 0:
        sign_y = 1
    else:
        sign_y = -1

    p = [p0[0], p0[1]]
    points = [[p[0], p[1]]]
    ix = 0
    iy = 0
    while ix < nx or iy < ny:
        if (0.5 + ix) / nx == (0.5 + iy) / ny:
            # next step is diagonal
            p[0] += sign_x
            p[1] += sign_y
            ix += 1
            iy += 1
        elif (0.5 + ix) / nx < (0.5 + iy) / ny:
            # next step is horizontal
            p[0] += sign_x
            ix += 1
        else:
            # next step is vertical
            p[1] += sign_y
            iy += 1
        points.append((p[0], p[1]))
    return points


class Node:

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position


class Mask:
    def __init__(self, position, height, image):
        self.position = position
        self.height = height
        self.image = image


class TintColors:
    green = 2
    yellow = 1
    red = 0


class MapKeys:
    tile_sheet = "tile sheet"
    sheet_rows = "sheet row"
    sheet_columns = "sheet col"
    tile_width = "tile width"
    tile_height = "tile height"
    spawn_points = "spawn points"
    map_file = "map file"
    characters = "characters"
    map_width = "map width"
    map_height = "map height"
    border_width = "border width"
    border_height = "border height"
    camera_x = "camera x"
    camera_y = "camera y"
    spawn_x = "spawn x"
    spawn_y = "spawn y"
    scene = "scene"


class TileMap:
    def __init__(self, filename):
        f = open(filename)
        map_data = json.load(f)
        f.close()

        self.map_width = 0
        self.map_height = 0
        self.border_width = 0
        self.border_height = 0
        Camera.pos[0] = 0
        Camera.pos[1] = 0
        self.background_offset = (0, 0)
        self.background = pygame.Surface((1, 1))
        self.setup_background(map_data)

        self.zoomed_bg = None
        self.interface_layer = pygame.Surface([a_settings.display_width, a_settings.display_height]).convert()
        sheet = pygame.image.load(map_data[MapKeys.tile_sheet]).convert()
        self.ground_tiles = dict()
        self.tile_masks = dict()

        # create separate images from sprite sheet
        sheet_rows = map_data[MapKeys.sheet_rows]
        sheet_columns = map_data[MapKeys.sheet_columns]
        tile_width = map_data[MapKeys.tile_width]
        tile_height = map_data[MapKeys.tile_height]
        count = 0
        for i in range(sheet_columns):
            for j in range(sheet_rows):
                image = pygame.Surface([tile_width, tile_height]).convert()
                image.set_colorkey(pygame.Color("black"))
                image.blit(sheet, (0, 0), (i * tile_width, j * tile_height, tile_width, tile_height))
                self.ground_tiles[count] = image

                # create transparency masks from tiles
                mask_image = image.copy().convert_alpha()
                mask_image.fill((0, 0, 0), special_flags=pygame.BLEND_MULT)
                mask_image.set_colorkey((0, 0, 0, 0))
                self.tile_masks[count] = mask_image

                count += 1

        # read map data from file
        if MapKeys.spawn_points in map_data:
            self.spawn_points = map_data[MapKeys.spawn_points]
        self.spawns_used = 0
        with open(map_data[MapKeys.map_file], 'r') as map_file:
            self.tile_list = json.load(map_file)

        self.create_background()
        self.clean_bg = self.background.copy()

        self.entity_list = []

        self.change_scene = False
        self.next_scene = None

    def update(self, deltatime):
        for e in self.entity_list:
            e.update(deltatime)

    def render(self, screen):
        real_offset = [0, 0]
        real_offset[0] = self.background_offset[0] * Camera.zoom + Camera.pos[0]
        real_offset[1] = self.background_offset[1] * Camera.zoom + Camera.pos[1]
        screen.blit(self.zoomed_bg, real_offset)
        self.draw_all_entities(screen)

    def draw_all_entities(self, screen):
        for e in self.entity_list:
            # draw the entity if it is onscreen
            render_pos = e.get_render_pos()
            if onscreen_path(render_pos):
                # mask over the entity's image where an object is overlapping it
                tile_pos = (round(render_pos[0]), round(render_pos[1]))
                masks = []
                for offset in [(0, 1), (1, 0), (1, 1), (1, -1), (-1, 1)]:
                    new_tile = (tile_pos[0] + offset[0], tile_pos[1] + offset[1])
                    if self.in_bounds(new_tile, False):
                        map_tile = path_to_map(new_tile)
                        tiles = self.get_tile_attributes(map_tile)[TileKeys.tiles]
                        for tile in tiles:
                            if tile[TileKeys.height] > 0:
                                masks.append(Mask(new_tile, tile[TileKeys.height], self.tile_masks[tile[TileKeys.id]]))
                e.render(screen, masks)

    def notify(self, event):
        pass

    def add_entities(self, filename):
        with open(filename) as f:
            entity_data = json.load(f)
            for c in entity_data[MapKeys.characters]:
                new_character = entity.Entity([c[MapKeys.spawn_x], c[MapKeys.spawn_y]], self, c)
                self.entity_list.append(new_character)
        self.z_order_sort_entities()

    def setup_background(self, map_data):
        self.map_width = map_data[MapKeys.map_width]
        self.map_height = map_data[MapKeys.map_height]
        self.border_width = map_data[MapKeys.border_width]
        self.border_height = map_data[MapKeys.border_height]
        Camera.pos[0] = map_data[MapKeys.camera_x]
        Camera.pos[1] = map_data[MapKeys.camera_y]
        self.background_offset = (-self.border_width * tile_extent[0] * 2, -self.border_height * tile_extent[1])
        self.background = pygame.Surface([(self.map_width + self.border_width * 2 + 1) * tile_extent[0] * 2,
                                          (self.map_height + self.border_height * 2 + 1) * tile_extent[1]]).convert()

    def create_background(self):
        # create a grayed out border image
        border_image = self.ground_tiles[14].copy()
        border_image.fill((120, 120, 120), special_flags=pygame.BLEND_MULT)

        # blit each tile to the map, put grayed out borders outside map edge
        self.background.fill((0, 0, 0))
        for row in range(-self.border_height, self.map_height + self.border_height):
            for col in range(-self.border_width, self.map_width + self.border_width):
                x = (col * tile_extent[0] + tile_extent[1] * (row % 2)) * 2 - self.background_offset[0]
                y = row * tile_extent[1] - self.background_offset[1]
                if col < 0 or row < 0 or row >= self.map_height or col >= self.map_width:
                    self.background.blit(border_image, (x, y))
                else:
                    tiles = self.get_tile_attributes((col, row))[TileKeys.tiles]
                    for tile in tiles:
                        if tile[TileKeys.id] >= 0:
                            self.background.blit(self.ground_tiles[tile[TileKeys.id]], (x, y - tile[TileKeys.height]))
        self.zoom_background()

    def zoom_background(self):
        self.zoomed_bg = pygame.transform.scale(
            self.background,
            (round(self.background.get_width() * Camera.zoom), round(self.background.get_height() * Camera.zoom))
        )
        self.zoomed_bg.convert()
        self.clean_bg = self.zoomed_bg.copy()

    def zoom_image(self, image):
        if Camera.zoom != 1:
            zoomed = pygame.transform.scale(
                image,
                (round(image.get_width() * Camera.zoom), round(image.get_height() * Camera.zoom))
            )
            zoomed.convert()
            return zoomed
        return image

    def get_tile_path(self, coords):
        map_coords = path_to_map(coords)
        return self.get_tile_attributes(map_coords)

    def get_tile_attributes(self, tile_pos):
        return self.tile_list[str(tile_pos[0]) + ',' + str(tile_pos[1])]

    def set_tile_attributes(self, tile_pos, tile_data):
        self.tile_list[str(tile_pos[0]) + ',' + str(tile_pos[1])] = tile_data

    def move_camera_to_path(self, tile):
        destination = path_to_world((tile[0] - 3, tile[1] + 1))
        destination[0] += self.background_offset[0]
        destination[0] *= -1
        destination[1] += self.background_offset[1]
        destination[1] *= -1
        move = [destination[0] - Camera.pos[0], destination[1] - Camera.pos[1]]
        difference = move.copy()
        distance = difference[0] ** 2 + difference[1] ** 2
        full_square = distance * 2 / 3
        square = distance
        distance = math.sqrt(distance)
        if distance < 0.1:
            return
        direction = [move[0] > 0, move[1] > 0]
        wait_ms = 3
        speed = 400
        max_speed = 0.7
        min_speed = 3

        screen = pygame.display.get_surface()
        while [difference[0] > 0, difference[1] > 0] == direction:
            pygame.time.wait(wait_ms)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN:
                    key = event.key
                    if key == pygame.K_w or key == pygame.K_a or key == pygame.K_s or \
                            key == pygame.K_d or key == pygame.K_ESCAPE:
                        return

            deltatime = game_state.get_deltatime()
            speed_mult = abs(full_square - square) / full_square
            if speed_mult < max_speed:
                speed_mult = max_speed
            if speed_mult > min_speed:
                speed_mult = min_speed
            Camera.pos[0] += move[0] * deltatime / (speed * speed_mult)
            Camera.pos[1] += move[1] * deltatime / (speed * speed_mult)
            self.update(deltatime)
            self.render(screen)
            pygame.display.flip()
            difference = [destination[0] - Camera.pos[0], destination[1] - Camera.pos[1]]
            square = difference[0] ** 2 + difference[1] ** 2
            if square < 0.1:
                break
        Camera.pos = destination

    def move_camera_in_bounds(self):
        y_max = -(self.background_offset[1] + tile_extent[1]) * Camera.zoom
        if Camera.pos[1] > y_max:
            Camera.pos[1] = y_max

        y_min = (-self.map_height * tile_extent[1] + self.background_offset[
            1]) * Camera.zoom + a_settings.display_height
        if Camera.pos[1] < y_min:
            Camera.pos[1] = y_min

        x_max = -(self.background_offset[0] + tile_extent[0]) * Camera.zoom
        if Camera.pos[0] > x_max:
            Camera.pos[0] = x_max

        x_min = (-self.map_width * tile_extent[0] * 2 + self.background_offset[
            0]) * Camera.zoom + a_settings.display_width
        if Camera.pos[0] < x_min:
            Camera.pos[0] = x_min

    def in_bounds(self, coords, walkable_only, need_los=False):
        coords = (round(coords[0]), round(coords[1]))
        # valid if: x >= y, x + y > 0, x + y < map_height, x - y < map_width * 2
        if coords[0] < abs(coords[1]) or coords[0] + coords[1] >= self.map_height \
                or coords[0] - coords[1] >= self.map_width * 2:
            return False
        valid = True
        if walkable_only:
            valid = self.get_tile_path(coords)[TileKeys.walkable]
        if need_los:
            valid = valid and self.get_tile_path(coords)[TileKeys.line_of_sight]
        return valid

    def z_order_sort_entities(self):
        self.entity_list.sort()

    def add_entity(self, new_entity):
        self.entity_list.append(new_entity)
        self.z_order_sort_entities()

    def change_mode(self, next_mode):
        self.change_scene = True
        self.next_scene = next_mode


class CombatMap(TileMap):
    mouse_coords = None

    def __init__(self, filename):
        super().__init__(filename)
        f = open(filename)
        map_data = json.load(f)
        f.close()

        if MapKeys.scene in map_data.keys():
            self.scene = scenes[map_data[MapKeys.scene]](self)
            self.has_scene = True
        else:
            self.scene = None
            self.has_scene = False

        # keep track of when to update display
        self.tint_layer_update = False
        self.skill_display_update = False

        # initialize other images
        self.selection_square = pygame.image.load("images/selection_square.png").convert()
        self.selection_square.set_colorkey(pygame.Color("black"))
        self.path_arrow = pygame.image.load("images/path_arrow.png").convert()
        self.path_arrow.set_colorkey(pygame.Color("black"))
        self.path_arrow_horizontal = pygame.image.load("images/path_arrow_horizontal.png").convert()
        self.path_arrow_horizontal.set_colorkey(pygame.Color("black"))
        self.path_arrow_vertical = pygame.image.load("images/path_arrow_vertical.png").convert()
        self.path_arrow_vertical.set_colorkey(pygame.Color("black"))

        # create tile tint images
        self.white_tile_tint = pygame.image.load("images/tintable_square.png").convert_alpha()
        red_tile_tint = self.white_tile_tint.copy()
        green_tile_tint = self.white_tile_tint.copy()
        yellow_tile_tint = self.white_tile_tint.copy()
        red_tile_tint.fill((255, 0, 0, 75), special_flags=pygame.BLEND_RGBA_MULT)
        green_tile_tint.fill((0, 255, 0, 75), special_flags=pygame.BLEND_RGBA_MULT)
        yellow_tile_tint.fill((255, 255, 0, 75), special_flags=pygame.BLEND_RGBA_MULT)
        self.tint_images = {
            TintColors.red: red_tile_tint,
            TintColors.yellow: yellow_tile_tint,
            TintColors.green: green_tile_tint
        }
        self.tinted_tiles = {
            TintColors.red: set(),
            TintColors.yellow: set(),
            TintColors.green: set()
        }
        self.old_tinted_tiles = {
            TintColors.red: set(),
            TintColors.yellow: set(),
            TintColors.green: set()
        }
        self.cached_skill = None

        # objects to display
        self.path = []
        self.possible_paths = set()
        self.last_path_test = (-99, -199)
        self.selected_character = None
        self.character_list = []
        self.interface = user_interface.UserInterface()
        self.interface.add_image_button((0.8, 0.9, 0.15, 0.05), "End Turn", "end turn")
        self.controlled_characters = []
        self.ai_manager = ai_manager.AIManager(self)

        if "enemy spawn area" in map_data.keys():
            self.enemy_spawn_area = map_data["enemy spawn area"]
            self.populate_map()
            self.add_players(game_state.GameState.player_characters)

    def populate_map(self):
        # make up an assortment of enemies to face
        with open("data/enemy_list.json") as enemy_file:
            enemy_list = json.load(enemy_file)

        # just grab 5 random enemies from enforcer group for now
        enemy_choices = enemy_list["normal enemies"]["enforcer"]
        enemy_data = []
        for i in range(5):
            enemy_name = random.choice(enemy_choices)
            enemy_data.append(enemy_list[enemy_name])

        self.add_entities(enemy_data)

    def update(self, deltatime):
        if self.has_scene:
            self.scene.update(deltatime)

        # move camera in response to key presses
        if not self.has_scene or self.scene.get_allow_input():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                Camera.pos[1] += deltatime * Camera.speed
            if keys[pygame.K_s]:
                Camera.pos[1] -= deltatime * Camera.speed
            if keys[pygame.K_a]:
                Camera.pos[0] += deltatime * Camera.speed
            if keys[pygame.K_d]:
                Camera.pos[0] -= deltatime * Camera.speed

            self.move_camera_in_bounds()

        for e in self.entity_list:
            e.update(deltatime)

        # update mouse coordinates when mouse moves to new tile
        if screen_to_path(pygame.mouse.get_pos()) != self.mouse_coords:
            self.mouse_coords = screen_to_path(pygame.mouse.get_pos())
            self.skill_display_update = True

    def render(self, screen):
        # create offset used by tint_layer
        real_offset = [0, 0]
        real_offset[0] = self.background_offset[0] * Camera.zoom
        real_offset[1] = self.background_offset[1] * Camera.zoom

        self.apply_tint_layer_to_bg(real_offset)

        # draw background first
        bg_offset = [0, 0]
        bg_offset[0] = real_offset[0] + Camera.pos[0]
        bg_offset[1] = real_offset[1] + Camera.pos[1]
        screen.blit(self.zoomed_bg, bg_offset)

        self.draw_movement_path(screen)

        if self.selected_character is not None:
            self.display_skill_info(self.selected_character.get_selected_skill())
        self.skill_display_update = False
        self.draw_all_entities(screen)

        if self.has_scene:
            self.scene.render(screen)

        for e in self.entity_list:
            if self.mouse_coords == e.position:
                e.on_highlight()

        # draw character UI elements
        for c in self.character_list:
            c.second_render(screen)

        # draw map UI and scene UI last
        self.interface.render(screen)
        if self.has_scene:
            self.scene.second_render(screen)

    def apply_tint_layer_to_bg(self, real_offset):
        if self.tint_layer_update:
            self.tint_layer_update = False

            # get a list of all tiles that don't need an update
            tiles_to_cache = set()
            for color in self.tinted_tiles.keys():
                tiles_to_cache = tiles_to_cache.union(self.tinted_tiles[color] & self.old_tinted_tiles[color])

            # update tiles that have any differences between old and new sets
            for color in self.tinted_tiles.keys():
                for tile in self.old_tinted_tiles[color] ^ self.tinted_tiles[color]:
                    tiles_to_cache.discard(tile)

            # create a surface to transfer from clean bg, then mask it in shape of the tile
            zoom_mask = self.zoom_image(self.white_tile_tint)
            clean_surface = pygame.Surface(
                (tile_extent[0] * 2 * Camera.zoom,
                 tile_extent[1] * 2 * Camera.zoom)
            ).convert()
            clean_surface.fill((0, 0, 0, 0))
            clean_surface.set_colorkey((0, 0, 0, 0))

            tiles_to_clean = set()
            for tile_set in self.old_tinted_tiles.values():
                tiles_to_clean = tiles_to_clean.union(tile_set)

            # remove tint from bg using original copy
            for tile in tiles_to_clean:
                if tile not in tiles_to_cache:
                    tile_pos = path_to_world(tile)
                    tile_offset = ((tile_pos[0] - self.background_offset[0]) * Camera.zoom,
                                   (tile_pos[1] - self.background_offset[1]) * Camera.zoom)
                    clean_surface.blit(zoom_mask, (0, 0))
                    clean_surface.blit(
                        self.clean_bg,
                        (0, 0),
                        (tile_offset[0], tile_offset[1],
                         tile_extent[0] * 2 * Camera.zoom, tile_extent[1] * 2 * Camera.zoom),
                        special_flags=pygame.BLEND_MULT
                    )
                    self.zoomed_bg.blit(clean_surface, tile_offset)

            for tile_set in self.old_tinted_tiles.values():
                tile_set.clear()

            # after clearing old tiles, tint the bg tiles the proper color
            for color in self.tinted_tiles.keys():
                zoom_tint = self.zoom_image(self.tint_images[color])
                for tile in self.tinted_tiles[color]:
                    if tile not in tiles_to_cache:
                        tint_pos = path_to_world(tile)
                        tint_pos[0] = tint_pos[0] * Camera.zoom - real_offset[0]
                        tint_pos[1] = tint_pos[1] * Camera.zoom - real_offset[1]
                        self.zoomed_bg.blit(zoom_tint, tint_pos)

    def draw_movement_path(self, screen):
        zoom_selection = self.zoom_image(self.selection_square)
        # draw path from selected ally entity to highlighted tile
        if self.selected_character is not None:
            screen.blit(zoom_selection, path_to_screen(self.selected_character.position))
            selected_skill = self.selected_character.get_selected_skill()

            if self.selected_character.accepting_input and selected_skill is None and self.selected_character.has_move:
                # calculate a new path whenever destination changes
                if self.skill_display_update:
                    self.path = self.find_path(
                        self.selected_character.position,
                        self.mouse_coords,
                        self.selected_character.get_data(CharacterKeys.movement))

                # draw arrows along path in direction of path
                if len(self.path) > 1:
                    last_loc = self.path[0]
                    offset = -tile_extent[1] * Camera.zoom
                    diagonal_arrow = self.zoom_image(self.path_arrow)
                    horizontal_arrow = self.zoom_image(self.path_arrow_horizontal)
                    vertical_arrow = self.zoom_image(self.path_arrow_vertical)
                    for loc in self.path[1:]:
                        arrow = None
                        if last_loc[0] > loc[0]:
                            if last_loc[1] > loc[1]:
                                # up arrow
                                arrow = pygame.transform.flip(vertical_arrow, False, True)
                            elif last_loc[1] < loc[1]:
                                # left arrow
                                arrow = pygame.transform.flip(horizontal_arrow, True, False)
                            else:
                                # up-left arrow
                                arrow = pygame.transform.flip(diagonal_arrow, True, True)
                        elif last_loc[0] < loc[0]:
                            if last_loc[1] > loc[1]:
                                # right arrow
                                arrow = horizontal_arrow
                            elif last_loc[1] < loc[1]:
                                # down arrow
                                arrow = vertical_arrow
                            else:
                                # down-right arrow
                                arrow = diagonal_arrow
                        else:
                            if last_loc[1] > loc[1]:
                                # up-right arrow
                                arrow = pygame.transform.flip(diagonal_arrow, False, True)
                            elif last_loc[1] < loc[1]:
                                # down-left arrow
                                arrow = pygame.transform.flip(diagonal_arrow, True, False)
                            else:
                                print("ERROR: supplied path contains duplicate points")

                        render_loc = path_to_screen(loc)
                        screen.blit(arrow, (render_loc[0], render_loc[1] + offset))
                        last_loc = loc

        # draw highlighted square around mouse position
        if not self.has_scene or self.scene.get_allow_input():
            screen.blit(zoom_selection, path_to_screen(self.mouse_coords))

    def display_skill_info(self, skill, force_update=False):
        # render the area that will be hit by a skill
        if skill is not None:
            tags = skill.get_data("tags")
            if force_update or "aimed" in tags and self.skill_display_update:
                if force_update or skill != self.cached_skill:
                    range_display = skill.targetable_tiles(True)
                    self.cached_skill = skill
                else:
                    range_display = self.tinted_tiles[TintColors.yellow].copy()
                self.clear_tinted_tiles()
                if "friendly" in tags:
                    self.tinted_tiles[TintColors.green] = skill.display_targets(self.mouse_coords)
                else:
                    self.tinted_tiles[TintColors.red] = skill.display_targets(self.mouse_coords)
                self.tinted_tiles[TintColors.yellow] = range_display

    def notify(self, event):
        # map scene gets first dibs on consuming input
        if self.has_scene and self.scene.notify(event):
            return

        # check if map UI consumes the input
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "end turn":
                self.end_turn()
            return

        # check if an entity's UI consumes the input
        for c in self.character_list:
            if c.notify(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_coords = screen_to_path(pygame.mouse.get_pos())
            selected = self.selected_character
            skill = None
            aimed = False
            if selected is not None and selected.ally:
                skill = selected.get_selected_skill()
                if skill is not None:
                    aimed = "aimed" in skill.get_data("tags") or "no target" in skill.get_data("tags")

            if event.button == 1:

                if not aimed:
                    # find if tile is occupied by a character
                    for c in self.character_list:
                        if mouse_coords == c.position:

                            # when a valid target is clicked on while a skill is selected, try to use the skill
                            if skill is not None and (
                                    c.ally == skill.has_tag("buff") or skill.has_tag("friendly fire")) and \
                                    self.selected_character.use_skill(mouse_coords):
                                return

                            # deselect previous character and select the new one
                            if selected is not None:
                                self.selected_character.set_selected(False)

                            self.clear_tinted_tiles()
                            self.selected_character = c.set_selected(True)
                            return

                    # move selected character to unoccupied position if able
                    if selected is not None and selected.move_order(self.path):
                        self.clear_tinted_tiles()
                else:
                    # center attack on clicked tile if free aiming
                    selected.use_skill(mouse_coords)

            elif event.button == 3:
                if selected is not None:
                    self.clear_tinted_tiles()
                    if skill is None:
                        # right click to deselect unit
                        self.selected_character = self.selected_character.set_selected(False)
                    else:
                        # right click to cancel attack
                        selected.set_selected(True)

        elif event.type == pygame.KEYDOWN:
            # cycle through controllable characters and focus on them
            if event.key == pygame.K_TAB and len(self.controlled_characters) > 0:
                self.clear_tinted_tiles()
                if self.selected_character is None:
                    self.selected_character = self.controlled_characters[0].set_selected(True)
                else:
                    for i, c in enumerate(self.controlled_characters):
                        if c.position == self.selected_character.position:
                            self.controlled_characters[i].set_selected(False)
                            if i + 1 < len(self.controlled_characters):
                                self.selected_character = self.controlled_characters[i + 1].set_selected(True)
                                break
                            else:
                                self.selected_character = self.controlled_characters[0].set_selected(True)
                                break
                self.move_camera_to_path(self.selected_character.position)
            # focus camera on current selection
            elif event.key == pygame.K_SPACE and self.selected_character is not None:
                self.move_camera_to_path(self.selected_character.position)
            # zoom camera in and out
            elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                zoom_step = 0.05
                zoom_min = 0.6
                zoom_max = 1
                if event.key == pygame.K_UP:
                    Camera.zoom -= zoom_step
                    if Camera.zoom < zoom_min:
                        Camera.zoom = zoom_min
                else:
                    Camera.zoom += zoom_step
                    if Camera.zoom > zoom_max:
                        Camera.zoom = zoom_max
                self.zoom_background()
                self.tint_layer_update = True
                self.move_camera_in_bounds()

    def add_players(self, entity_data):
        for c in entity_data.values():
            # team 0 is the player controlled team
            new_character = character.Character(self.get_spawn(), self, c)
            self.controlled_characters.append(new_character)
            self.character_list.append(new_character)
            self.entity_list.append(new_character)

    def add_entities(self, entity_data):
        for c in entity_data:
            spawn = self.get_enemy_spawn_location()
            new_character = character.AICharacter(spawn, self, self.ai_manager, c)
            self.character_list.append(new_character)
            self.entity_list.append(new_character)

        self.z_order_sort_entities()

    def get_enemy_spawn_location(self):
        min_x = self.enemy_spawn_area[0][0]
        max_x = self.enemy_spawn_area[1][0]
        x = random.randint(min_x, max_x)
        min_y = self.enemy_spawn_area[0][1]
        max_y = self.enemy_spawn_area[1][1]
        y = random.randint(min_y, max_y)
        return [x, y]

    def remove_entities(self):
        if self.selected_character is not None and self.selected_character.delete:
            self.selected_character = None

        found = True
        while found:
            found = False
            for i, o in enumerate(self.character_list):
                if o.delete:
                    del self.character_list[i]
                    found = True
                    break

            for i, o in enumerate(self.entity_list):
                if o.delete:
                    del self.entity_list[i]
                    found = True
                    break

            for i, o in enumerate(self.ai_manager.actors):
                if o.delete:
                    del self.ai_manager.actors[i]
                    found = True
                    break

    def get_spawn(self):
        spawn_pos = self.spawn_points[self.spawns_used]
        self.spawns_used += 1
        return spawn_pos

    def clear_tinted_tiles(self):
        has_tint = False
        for tile_set in self.tinted_tiles.values():
            if len(tile_set) > 0:
                has_tint = True
                break
        if has_tint:
            for color in self.tinted_tiles.keys():
                self.old_tinted_tiles[color] = self.tinted_tiles[color].copy()
        for tiles in self.tinted_tiles.values():
            tiles.clear()
        self.tint_layer_update = True

        for c in self.character_list:
            c.reset_display()

    def display_movement(self, this_character):
        self.possible_paths = self.find_all_paths(this_character.position,
                                                  this_character.get_data(CharacterKeys.movement))
        # show possible movement tiles for selected character
        self.clear_tinted_tiles()
        self.tinted_tiles[TintColors.green] = self.possible_paths
        # dirty the mouse coordinates so there will be an immediate path update
        self.mouse_coords = (-1, -1)

    def get_characters_in_set(self, tile_set):
        inside = []
        for c in self.character_list:
            if (c.position[0], c.position[1]) in tile_set:
                inside.append(c)
        return inside

    def make_radius(self, center, radius, walkable_only):
        open_list = set()
        closed_list = set()
        open_list.add((center[0], center[1]))
        steps = -1
        while steps < radius:
            steps += 1
            working_list = open_list.copy()
            open_list.clear()
            for current_center in working_list:
                closed_list.add(current_center)
                for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]:  # Adjacent squares
                    neighbor = (current_center[0] + new_position[0], current_center[1] + new_position[1])
                    if neighbor not in closed_list and self.in_bounds(neighbor, walkable_only):
                        open_list.add(neighbor)
        return closed_list

    def line_of_sight(self, p0, p1, length=9999):
        if distance_between(p0, p1) > length:
            return False
        line = supercover_line(p0, p1)
        for tile in line:
            if not self.in_bounds(tile, False, True):
                return False
        return True

    def find_all_paths(self, start, max_length, projectile=False, edges_only=False, indirect=False):
        # Initialize both open and closed list
        open_list = [(start[0], start[1], 0)]
        open_list_pos = {start[0], start[1]}
        closed_index = 0
        closed_list = set()
        edge_list = set()

        # Loop until you find the end
        while closed_index < len(open_list):

            # Pop current off open list, add to closed list
            current_node = open_list[closed_index]
            closed_index += 1
            current_position = (current_node[0], current_node[1])
            open_list_pos.discard(current_position)
            closed_list.add(current_position)
            if edges_only:
                edge_list.add(current_position)

            if current_node[2] + 1 > max_length:
                continue

            valid_adjacent = 0
            for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0),
                                 (-1, -1), (-1, 1), (1, -1), (1, 1)]:  # Adjacent squares

                g = current_node[2] + 1
                node_position = (current_node[0] + new_position[0], current_node[1] + new_position[1])

                if node_position in closed_list:
                    valid_adjacent += 1
                    continue

                # Make sure tile is not blocked
                if indirect:
                    if not self.in_bounds(node_position, False, False):
                        valid_adjacent += 1
                        continue
                elif projectile:
                    if not self.in_bounds(node_position, False, True) or not self.line_of_sight(start, node_position):
                        continue
                else:
                    if not self.in_bounds(node_position, True):
                        continue

                # handle diagonal movement
                if new_position[0] != 0 and new_position[1] != 0:
                    g += 0.414
                    if g > max_length:
                        continue
                    # check if a tile is blocking diagonal movement
                    if not indirect and (
                            not self.in_bounds([node_position[0], current_node[1]], not projectile, projectile) or
                            not self.in_bounds([current_node[0], node_position[1]], not projectile, projectile)):
                        continue

                if node_position in open_list_pos:
                    valid_adjacent += 1
                    continue

                # Create new node
                new_node = (node_position[0], node_position[1], g)
                open_list.append(new_node)
                open_list_pos.add(node_position)
                valid_adjacent += 1
            if edges_only and valid_adjacent >= 8:
                edge_list.discard(current_position)
        if edges_only:
            return edge_list
        return closed_list

    def find_path(self, start, end, max_length):
        end = tuple(end)
        if not self.in_bounds(end, True):
            return []

        if start != self.last_path_test:
            self.possible_paths = self.find_all_paths(start, max_length)
            self.last_path_test = start

        if end not in self.possible_paths:
            return []

        start_node = Node(None, tuple(start))
        open_list = {tuple(start): start_node}
        closed_list = set()

        # Loop until finding the end
        loops = 0
        while len(open_list) > 0 and loops < 1000:
            loops += 1

            # Get node closest to destination
            current_node = next(iter(open_list.values()))
            current_position = current_node.position
            for key in open_list.keys():
                if open_list[key].f < current_node.f:
                    current_node = open_list[key]
                    current_position = key

            # Found the goal
            if current_position == end:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]  # Return reversed path

            open_list.pop(current_position)
            closed_list.add(current_position)

            if current_node.g + 1 > max_length:
                continue

            for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0),
                                 (-1, -1), (-1, 1), (1, -1), (1, 1)]:  # Adjacent squares

                g = current_node.g + 1
                node_position = (current_position[0] + new_position[0], current_position[1] + new_position[1])

                if node_position in closed_list:
                    continue

                # Make sure tile is valid
                if not self.in_bounds(node_position, True):
                    # add non-walkable tiles to closed list to improve performance
                    closed_list.add(node_position)
                    continue

                # handle diagonal movement
                if new_position[0] != 0 and new_position[1] != 0:
                    g += 0.414
                    if g > max_length:
                        continue
                    # check if a tile is blocking diagonal movement
                    if not self.in_bounds([node_position[0], current_position[1]], True) \
                            or not self.in_bounds([current_position[0], node_position[1]], True):
                        continue

                # deterministically alter predicted distance to break ties and improve performance
                hashed = 1000 * node_position[0] + node_position[1]
                h = distance_between(node_position, end) * (1 + hashed / 100000)
                f = g + h

                # make sure a better path does not exist
                if node_position in open_list.keys() and g >= open_list[node_position].g:
                    continue

                new_node = Node(current_node, node_position)
                new_node.g = g
                new_node.f = f
                open_list[node_position] = new_node
        return []

    def start_turn(self):
        for c in self.entity_list:
            c.start_of_round_update()
        self.remove_entities()

        if not self.detect_victory() and not self.detect_failure():
            self.interface.set_button_active("end turn", True)

    def end_turn(self):
        self.interface.set_button_active("end turn", False)
        self.clear_tinted_tiles()
        if self.selected_character is not None:
            self.selected_character = self.selected_character.set_selected(False)
        self.remove_entities()

        # stabilize downed allies
        for c in self.controlled_characters:
            if c.knocked_out:
                position = c.position
                adj_set = set()
                for adj in [(0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1), (-1, 1)]:
                    adj_set.add((position[0] + adj[0], position[1] + adj[1]))
                adjacent_allies = self.get_characters_in_set(adj_set)
                for ally in adjacent_allies:
                    if ally.ally and ally.has_action:
                        c.stabilize()

        for c in self.entity_list:
            c.end_of_round_update()
        if not self.detect_victory() and not self.detect_failure():
            self.ai_manager.start_ai_turn()

    def detect_victory(self):
        # let scene object handle potential alternate victory conditions
        alternate_victory = None
        if self.has_scene:
            alternate_victory = self.scene.detect_victory()
            if alternate_victory is not None:
                return alternate_victory
        if alternate_victory is None:
            # otherwise check if there are any remaining enemies on the map
            victory = True
            for c in self.character_list:
                if not c.ally:
                    victory = False
                    break
            if victory:
                # update game state with current player state
                for c in self.controlled_characters:
                    game_state.update_player(c)
                self.change_mode(game_modes.ExpeditionScene())
                return True
        return False

    def detect_failure(self):
        # check if all controllable characters are knocked out
        for c in self.controlled_characters:
            if not c.knocked_out:
                return False
        return self.fail_scene()

    def fail_scene(self):
        failure = None
        if self.has_scene:
            failure = self.scene.handle_failure()
            if failure is not None:
                return failure
        if failure is None:
            self.change_mode(game_modes.HubScene())
            return True


class FreeMoveMap(TileMap):
    def __init__(self, filename):
        super().__init__(filename)
        self.interactive_entities = []
        self.player = entity.FreeMover([0, 0], self, {"appearance": "images/tile041.png", "height": 1.5})
        self.add_entity(self.player)
        self.add_entities(filename)
        self.control_entity = None

    def update(self, deltatime):
        super().update(deltatime)

        if self.control_entity is None:
            keys = pygame.key.get_pressed()
            up = keys[pygame.K_w]
            down = keys[pygame.K_s]
            left = keys[pygame.K_a]
            right = keys[pygame.K_d]

            move_keys = [up, down, left, right]
            speed = deltatime * self.player.move_speed
            # the following code allows the player to slide along walls instead of stopping
            # it does this by checking a 45 degree angle from your current movement
            if not self.try_move_player(move_keys, speed):
                # try the move with one key added in a perpendicular direction
                if not move_keys[0] and not move_keys[1]:
                    self.try_move_player([True, move_keys[1], move_keys[2], move_keys[3]], speed)
                    self.try_move_player([move_keys[0], True, move_keys[2], move_keys[3]], speed)
                else:
                    self.try_move_player([move_keys[0], move_keys[1], True, move_keys[3]], speed, True)
                    self.try_move_player([move_keys[0], move_keys[1], move_keys[2], True], speed, True)

            Camera.pos = path_to_world(self.player.position)
            Camera.pos[0] *= -1
            Camera.pos[1] *= -1
            Camera.pos[0] += a_settings.display_width / 2 - tile_extent[0] * 2
            Camera.pos[1] += a_settings.display_height / 2 - tile_extent[1]
            self.move_camera_in_bounds()

            for e in self.interactive_entities:
                e.active_when_adjacent(self.player.position)
        self.z_order_sort_entities()

    def render(self, screen):
        super().render(screen)
        for e in self.interactive_entities:
            e.second_render(screen)

    def notify(self, event):
        if self.control_entity is not None:
            self.control_entity.notify(event)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                # try to interact with all active interactive entities
                for e in self.interactive_entities:
                    if e.interact():
                        self.set_control_entity(e)
                        break

    def set_control_entity(self, controller):
        self.control_entity = controller

    def return_control(self):
        self.control_entity = None

    def add_entities(self, filename, team=0):
        with open(filename) as f:
            entity_data = json.load(f)
            for c in entity_data[MapKeys.characters]:
                new_character = entity.NPC([c[MapKeys.spawn_x], c[MapKeys.spawn_y]], self, c)
                self.entity_list.append(new_character)
                self.interactive_entities.append(new_character)
            for c in entity_data["exits"]:
                new_exit = entity.EmbarkLocation([c[MapKeys.spawn_x], c[MapKeys.spawn_y]], self, c)
                self.entity_list.append(new_exit)
                self.interactive_entities.append(new_exit)
        self.z_order_sort_entities()

    def try_move_player(self, move_keys, speed, no_mult=False):
        move = self.create_move(move_keys, speed, no_mult)
        if self.in_bounds(move, True):
            self.player.position = move
            return True
        return False

    def create_move(self, move_keys, speed, no_mult):
        # up = 0, down = 1, left = 2, right = 3
        move = [self.player.position[0], self.player.position[1]]
        vertical_speed_mult = 1.5
        if no_mult:
            vertical_speed_mult = 1
        if move_keys[0]:
            move[0] -= speed * vertical_speed_mult
            move[1] -= speed * vertical_speed_mult
        if move_keys[1]:
            move[0] += speed * vertical_speed_mult
            move[1] += speed * vertical_speed_mult
        if move_keys[2]:
            move[0] -= speed
            move[1] += speed
        if move_keys[3]:
            move[0] += speed
            move[1] -= speed
        return move
