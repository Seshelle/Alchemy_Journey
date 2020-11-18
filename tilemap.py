import pygame
from scenes import scenes
import entity
import character
from character import CharacterKeys
import alchemy_settings as a_settings
import ai_manager
import user_interface
import math
import json

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
        sheet = pygame.image.load(map_data["tile sheet"]).convert()
        self.ground_tiles = dict()
        self.tile_masks = dict()

        # create separate images from sprite sheet
        sheet_rows = map_data["sheet row"]
        sheet_columns = map_data["sheet col"]
        tile_width = map_data["tile width"]
        tile_height = map_data["tile height"]
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
        self.spawn_points = [(3, 0), (5, 0)]
        self.spawns_used = 0
        with open(map_data["map file"], 'r') as map_file:
            self.tile_list = json.load(map_file)

        self.create_background()
        self.clean_bg = self.background.copy()

        self.entity_list = []

    def update(self, deltatime, screen):
        real_offset = [0, 0]
        real_offset[0] = self.background_offset[0] * Camera.zoom + Camera.pos[0]
        real_offset[1] = self.background_offset[1] * Camera.zoom + Camera.pos[1]
        screen.blit(self.zoomed_bg, real_offset)
        self.draw_all_entities(deltatime, screen)

    def draw_all_entities(self, deltatime, screen):
        for e in self.entity_list:
            e.update(deltatime)
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
            for c in entity_data["characters"]:
                new_character = entity.Entity([c["spawn x"], c["spawn y"]], self, c)
                self.entity_list.append(new_character)
        self.z_order_sort_entities()

    def setup_background(self, map_data):
        self.map_width = map_data["map width"]
        self.map_height = map_data["map height"]
        self.border_width = map_data["border width"]
        self.border_height = map_data["border height"]
        Camera.pos[0] = map_data["camera x"]
        Camera.pos[1] = map_data["camera y"]
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
        # TODO: make camera lerp instead of teleporting
        target_pos = path_to_world((tile[0] + 2, tile[1]))
        Camera.pos[0] = -target_pos[0] + a_settings.display_width / 2
        Camera.pos[1] = -target_pos[1] + a_settings.display_height / 2
        self.move_camera_in_bounds()

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


class CombatMap(TileMap):
    mouse_coords = None

    def __init__(self, filename):
        super().__init__(filename)
        f = open(filename)
        map_data = json.load(f)
        f.close()

        if "scene" in map_data.keys():
            self.scene = scenes[map_data["scene"]](self)
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
        self.interface.add_button((0.9, 0.95, 0.15, 0.05), "End Turn", "end turn")
        self.controlled_characters = []
        self.ai_manager = ai_manager.AIManager(self)

        self.populate_map(filename)

    def populate_map(self, filename):
        self.add_entities(filename)
        self.add_entities('data/player_characters.json')

    def update(self, deltatime, screen):
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

        # update mouse coordinates when mouse moves to new tile
        mouse_change = False
        if screen_to_path(pygame.mouse.get_pos()) != self.mouse_coords:
            self.mouse_coords = screen_to_path(pygame.mouse.get_pos())
            mouse_change = True
            self.skill_display_update = True

        self.draw_movement_path(screen, mouse_change)
        if self.selected_character is not None:
            self.display_skill_info(self.selected_character.get_selected_skill())
        self.draw_all_entities(deltatime, screen)

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
                # the tiles in both sets are tiles that don't need updating
                tiles_to_cache = tiles_to_cache.union(self.tinted_tiles[color] & self.old_tinted_tiles[color])
            # update tiles that have any differences between old and new sets
            for color in self.tinted_tiles.keys():
                for tile in self.old_tinted_tiles[color] ^ self.tinted_tiles[color]:
                    tiles_to_cache.discard(tile)

            # zoom_mask = self.zoom_image(self.tile_mask_image)
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

    def draw_movement_path(self, screen, mouse_change):
        zoom_selection = self.zoom_image(self.selection_square)
        # draw path from selected ally entity to highlighted tile
        if self.selected_character is not None:
            screen.blit(zoom_selection, path_to_screen(self.selected_character.position))
            selected_skill = self.selected_character.get_selected_skill()

            if self.selected_character.accepting_input and selected_skill is None and self.selected_character.has_move:
                # calculate a new path whenever destination changes
                if mouse_change:
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
        if skill is not None:
            if force_update or skill.get_data("area") > 0 and self.skill_display_update:
                self.skill_display_update = False
                # render the area that will be hit by an area skill
                if skill != self.cached_skill or force_update:
                    range_display = skill.display_range()
                    self.cached_skill = skill
                else:
                    range_display = self.tinted_tiles[TintColors.yellow].copy()
                self.clear_tinted_tiles()
                self.tinted_tiles[TintColors.red] = skill.display_targets(self.mouse_coords)
                self.tinted_tiles[TintColors.yellow] = range_display

    def notify(self, event):
        # map scene gets first dibs on consuming input
        if self.scene.notify(event):
            return

        # check if map UI consumes the input
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "end turn":
                self.interface.set_button_active("end turn", False)
                self.end_turn()
            return

        # check if an entity's UI consumes the input
        for c in self.character_list:
            if c.notify(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_coords = screen_to_path(pygame.mouse.get_pos())

            if event.button == 1:
                # check if skill or movement is selected
                free_aim = False
                if self.selected_character is not None:
                    selected_skill = self.selected_character.get_selected_skill()
                    if selected_skill is not None and selected_skill.get_data("area") > 0:
                        free_aim = True

                if not free_aim:
                    # find if tile is occupied by a character
                    for c in self.character_list:
                        if mouse_coords == c.position:

                            # when an enemy is clicked on while a skill is selected, try to use the skill
                            if not c.ally and self.selected_character is not None and \
                                    self.selected_character.use_skill(mouse_coords):
                                return

                            # deselect previous character and select the new one
                            if self.selected_character is not None:
                                self.selected_character.set_selected(False)

                            self.clear_tinted_tiles()
                            self.selected_character = c.set_selected(True)
                            return

                    # move selected character to unoccupied position if able
                    if self.selected_character is not None and self.selected_character.accepting_input:
                        if self.selected_character.commit_move(self.path):
                            self.clear_tinted_tiles()
                else:
                    # center attack on clicked tile if free aiming
                    self.selected_character.use_skill(mouse_coords)

            elif event.button == 3:
                if self.selected_character is not None:
                    self.clear_tinted_tiles()
                    if self.selected_character.get_selected_skill() is None:
                        # right click to deselect unit
                        self.selected_character = self.selected_character.set_selected(False)
                    else:
                        # right click to cancel attack
                        self.selected_character.set_selected(True)

        elif event.type == pygame.KEYDOWN:
            # cycle through controllable characters and focus on them
            if event.key == pygame.K_TAB:
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

    def add_entities(self, filename):
        with open(filename) as f:
            entity_data = json.load(f)
            for c in entity_data["characters"]:
                # team 0 is the player controlled team
                if c["team"] == 0:
                    new_character = character.Character(self.get_spawn(), self, c)
                    self.controlled_characters.append(new_character)
                else:
                    new_character = character.AICharacter([c["spawn x"], c["spawn y"]], self, self.ai_manager, c)
                    self.ai_manager.add_actor(new_character)

                # add entity to character list if it makes decisions
                if new_character.intelligent:
                    self.character_list.append(new_character)
                self.entity_list.append(new_character)
        self.z_order_sort_entities()

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

    def find_all_paths(self, start, max_length, projectile=False, edges_only=False):
        # Create start node
        start_node = Node(None, tuple(start))

        # Initialize both open and closed list
        open_list = []
        closed_list = set()
        edge_list = set()

        # Add the start node
        open_list.append(start_node)
        open_list_pos = set(start_node.position)

        # Loop until you find the end
        while len(open_list) > 0:

            # Get the current node
            current_node = open_list[0]
            current_index = 0

            # Pop current off open list, add to closed list
            open_list.pop(current_index)
            open_list_pos.discard(current_node.position)
            closed_list.add(current_node.position)
            if edges_only:
                edge_list.add(current_node.position)

            if current_node.g + 1 > max_length:
                continue

            valid_adjacent = 0
            for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0),
                                 (-1, -1), (-1, 1), (1, -1), (1, 1)]:  # Adjacent squares

                g = current_node.g + 1

                # Get node position
                node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])

                # node is on the closed list
                if node_position in closed_list:
                    valid_adjacent += 1
                    continue

                # Make sure tile is not blocked
                if not projectile:
                    if not self.in_bounds(node_position, True):
                        continue
                else:
                    if not self.in_bounds(node_position, False, True):
                        continue

                # test line of sight if required
                if projectile and not self.line_of_sight(start, node_position):
                    continue

                # handle diagonal movement
                if new_position[0] != 0 and new_position[1] != 0:
                    g += 0.42
                    if g > max_length:
                        continue
                    # check if a tile is blocking diagonal movement
                    if not projectile:
                        if not self.in_bounds([node_position[0], current_node.position[1]], True) \
                                or not self.in_bounds([current_node.position[0], node_position[1]], True):
                            continue
                    else:
                        if not self.in_bounds([node_position[0], current_node.position[1]], False, True) \
                                or not self.in_bounds([current_node.position[0], node_position[1]], False, True):
                            continue

                # node is already in the open list
                if node_position in open_list_pos:
                    valid_adjacent += 1
                    continue

                # Create new node
                new_node = Node(current_node, node_position)
                new_node.g = g

                # Append
                open_list.append(new_node)
                open_list_pos.add(new_node.position)
                valid_adjacent += 1
            if edges_only and valid_adjacent == 8:
                edge_list.discard(current_node.position)
        if edges_only:
            return edge_list
        return closed_list

    def find_path(self, start, end, max_length):
        if not self.in_bounds(end, True):
            return []

        if start != self.last_path_test:
            self.possible_paths = self.find_all_paths(start, max_length)
            self.last_path_test = start

        if tuple(end) not in self.possible_paths:
            return []

        # Create start and end node
        start_node = Node(None, tuple(start))
        end_node = Node(None, tuple(end))

        # Initialize both open and closed list
        open_list = []
        closed_list = set()

        # Add the start node
        open_list.append(start_node)
        open_list_pos = set(start_node.position)

        # Loop until you find the end
        loops = 0
        while len(open_list) > 0 and loops < 1000:
            loops += 1

            # Get the current node
            current_node = open_list[0]
            current_index = 0
            for index, item in enumerate(open_list):
                if item.f < current_node.f:
                    current_node = item
                    current_index = index

            # Pop current off open list, add to closed list
            open_list.pop(current_index)
            open_list_pos.discard(current_node.position)
            closed_list.add(current_node.position)

            # Found the goal
            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]  # Return reversed path

            if current_node.g + 1 > max_length:
                continue

            for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0),
                                 (-1, -1), (-1, 1), (1, -1), (1, 1)]:  # Adjacent squares

                g = current_node.g + 1

                # Get node position
                node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])

                # node is on the closed list
                if node_position in closed_list:
                    continue

                # Make sure tile is valid
                if not self.in_bounds(node_position, True):
                    # add non-walkable tiles to closed list to improve performance
                    closed_list.add(node_position)
                    continue

                # handle diagonal movement
                if new_position[0] != 0 and new_position[1] != 0:
                    g += 0.42
                    if g > max_length:
                        continue
                    # check if a tile is blocking diagonal movement
                    if not self.in_bounds([node_position[0], current_node.position[1]], True) \
                            or not self.in_bounds([current_node.position[0], node_position[1]], True):
                        continue

                # multiply predicted distance to break ties and improve performance
                h = distance_between(node_position, end) * 1.02
                f = g + h

                # node is already in the open list
                if node_position in open_list_pos:
                    for open_node in open_list:
                        if node_position == open_node.position and g >= open_node.g:
                            continue

                # Create new node
                new_node = Node(current_node, node_position)
                new_node.g = g
                new_node.f = f

                # Append
                open_list.append(new_node)
                open_list_pos.add(new_node.position)
        return []

    def start_turn(self):
        self.clear_tinted_tiles()
        if self.selected_character is not None:
            self.selected_character = self.selected_character.set_selected(False)
        for c in self.entity_list:
            c.start_of_round_update()
        self.interface.set_button_active("end turn", True)
        self.remove_entities()

    def end_turn(self):
        self.clear_tinted_tiles()
        if self.selected_character is not None:
            self.selected_character = self.selected_character.set_selected(False)
        for c in self.entity_list:
            c.end_of_round_update()
        self.ai_manager.start_ai_turn()
        self.remove_entities()


class FreeMoveMap(TileMap):
    def __init__(self, filename):
        super().__init__(filename)
        self.interactive_entities = []
        self.player = entity.FreeMover([0, 0], self, {"appearance": "images/tile041.png", "height": 1.5})
        self.add_entity(self.player)
        self.add_entities(filename)
        self.control_entity = None

    def update(self, deltatime, screen):
        super().update(deltatime, screen)

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

        for e in self.interactive_entities:
            e.second_render(screen)

        self.z_order_sort_entities()

    def notify(self, event):
        super().notify(event)
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

    def add_entities(self, filename):
        with open(filename) as f:
            entity_data = json.load(f)
            for c in entity_data["characters"]:
                new_character = entity.InteractiveEntity([c["spawn x"], c["spawn y"]], self, c)
                self.entity_list.append(new_character)
                self.interactive_entities.append(new_character)
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
