import pygame
import character
import alchemy_settings as a_settings
import ai_manager
import user_interface
import math
import random
import json

tile_extent = (64, 32)
camera_speed = 0.5
camera_pos = [0, 0]


def path_to_map(coords):
    # rotates path coordinates to map coordinates
    # map coordinates are the actual stored coordinates of tiles
    coords_map = [math.floor((coords[0] - coords[1]) / 2), coords[1] + coords[0]]
    return coords_map


def map_to_path(coords):
    # rotates path coordinates to map coordinates
    # map coordinates are the actual stored coordinates of tiles
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
        screen_xy[0] += camera_pos[0]
        screen_xy[1] += camera_pos[1]
    return screen_xy


def map_to_screen(map_xy):
    # returns the screen position of a tile
    screen_xy = [0, 0]
    screen_xy[0] = map_xy[0] * 128 + 64 * (map_xy[1] % 2) + camera_pos[0]
    screen_xy[1] = map_xy[1] * 32 + camera_pos[1]
    return screen_xy


def screen_to_path(screen_xy):
    # turns a screen position into a path coordinate
    # it is easier to calculate with path coordinates
    adjust_screen = [0, 0]
    adjust_screen[0] = screen_xy[0] - camera_pos[0]
    adjust_screen[1] = screen_xy[1] - camera_pos[1]
    coords_xy = [0, 0]
    # tilePos.x = (scenePos.x/tileExtents.x + scenePos.y/tileExtents.y) * 0.5f;
    coords_xy[0] = math.floor((adjust_screen[0] / tile_extent[0] + adjust_screen[1] / tile_extent[1]) * 0.5 - 0.5)
    # tilePos.y = (scenePos.y/tileExtents.y - scenePos.x/tileExtents.x) * 0.5f
    coords_xy[1] = math.floor((adjust_screen[1] / tile_extent[1] - adjust_screen[0] / tile_extent[0]) * 0.5 + 0.5)
    return coords_xy


def path_to_world(path_xy):
    return map_to_world(path_to_map(path_xy))


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
    return (dx + dy) + (-0.58) * min(dx, dy)


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


class Tile:
    def __init__(self, tile_id, height=0, walkable=True):
        self.tile_id = tile_id
        self.walkable = walkable
        self.height = height


class Mask:
    def __init__(self, position, height, image):
        self.position = position
        self.height = height
        self.image = image


class TileMap:
    mouse_coords = None

    def __init__(self, file_name, sheet_rows, sheet_columns, sheet_width, sheet_height, map_width, map_height):
        self.map_width = map_width
        self.map_height = map_height
        self.background = pygame.Surface([(map_width + 1) * tile_extent[0] * 2,
                                          (map_height + 1) * tile_extent[1] * 2]).convert()
        self.tint_layer = pygame.Surface([(map_width + 1) * tile_extent[0] * 2,
                                          (map_height + 1) * tile_extent[1] * 2]).convert()
        self.tint_layer.fill((0, 0, 0))
        self.tint_layer.set_colorkey((0, 0, 0))
        self.tint_layer.set_alpha(75)
        self.tint_layer_rect = (0, 0, 0, 0)
        self.tint_layer_update = False
        self.interface_layer = pygame.Surface([a_settings.display_width, a_settings.display_height]).convert()
        sheet = pygame.image.load(file_name).convert()
        self.ground_tiles = dict()
        self.tile_masks = dict()

        # create separate images from sprite sheet
        count = 0
        for i in range(sheet_rows):
            for j in range(sheet_columns):
                image = pygame.Surface([sheet_width, sheet_height]).convert()
                image.set_colorkey(pygame.Color("black"))
                image.blit(sheet, (0, 0), (i * sheet_width, j * sheet_height, sheet_width, sheet_height))
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
        self.tile_list = dict()
        random.seed(3)
        for row in range(map_height):
            for col in range(map_width):
                if random.random() < 0.8:
                    self.tile_list[(col, row)] = Tile(0)
                else:
                    self.tile_list[(col, row)] = Tile(14, round(tile_extent[1] * 3 / 2), False)

        # create a grayed out border image
        border_image = self.ground_tiles[0].copy()
        border_image.fill((120, 120, 120), special_flags=pygame.BLEND_MULT)
        self.border_thickness = 1

        # blit each tile to the map, put grayed out borders outside map edge
        for row in range(-self.border_thickness, map_height + self.border_thickness):
            for col in range(-self.border_thickness, map_width + self.border_thickness):
                x = (col * tile_extent[0] + tile_extent[1] * (row % 2)) * 2
                y = row * tile_extent[1]
                if x < 0 or y < 0 or row >= map_height or col >= map_width:
                    self.background.blit(border_image, (x, y))
                else:
                    attributes = self.tile_list[(col, row)]
                    self.background.blit(self.ground_tiles[attributes.tile_id], (x, y - attributes.height))

        # initialize other images
        self.selection_square = pygame.image.load("images/selection_square.png").convert()
        self.selection_square.set_colorkey(pygame.Color("black"))
        self.path_arrow = pygame.image.load("images/path_arrow.png").convert()
        self.path_arrow.set_colorkey(pygame.Color("black"))
        self.path_arrow_horizontal = pygame.image.load("images/path_arrow_horizontal.png").convert()
        self.path_arrow_horizontal.set_colorkey(pygame.Color("black"))
        self.path_arrow_vertical = pygame.image.load("images/path_arrow_vertical.png").convert()
        self.path_arrow_vertical.set_colorkey(pygame.Color("black"))
        self.red_tile_tint = pygame.image.load("images/tintable_square.png").convert_alpha()
        self.red_tile_tint.set_colorkey(pygame.Color("black"))
        self.green_tile_tint = self.red_tile_tint.copy()
        self.red_tile_tint.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
        self.green_tile_tint.fill((0, 255, 0), special_flags=pygame.BLEND_RGB_MULT)

        # objects to display
        self.path = []
        self.possible_paths = set()
        self.last_path_test = (-99, -199)
        self.selected_character = None
        self.entity_list = []
        self.character_list = []
        self.red_tinted_tiles = set()
        self.green_tinted_tiles = set()

        # map scene user interface
        self.interface = user_interface.UserInterface()
        self.interface.add_button((0.9, 0.95, 0.15, 0.05), "End Turn", "end turn")

        # AI manager
        self.ai_manager = ai_manager.AIManager(self)

    def upkeep(self, deltatime, screen):
        # move camera in response to key presses
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] and camera_pos[1] < -deltatime * camera_speed:
            camera_pos[1] += deltatime * camera_speed

        if keys[pygame.K_s] and camera_pos[1] > -(self.map_height + 1) * tile_extent[1] \
                + a_settings.display_height + deltatime * camera_speed:
            camera_pos[1] -= deltatime * camera_speed

        if keys[pygame.K_a] and camera_pos[0] < -deltatime * camera_speed:
            camera_pos[0] += deltatime * camera_speed

        if keys[pygame.K_d] and camera_pos[0] > -(self.map_width + 0.5) * tile_extent[0] * 2 \
                + a_settings.display_width + deltatime * camera_speed:
            camera_pos[0] -= deltatime * camera_speed

        # create new tint layer if it has changed
        min_x = 999999
        min_y = 999999
        max_x = 0
        max_y = 0
        if self.tint_layer_update:
            self.tint_layer_update = False
            for tile in self.red_tinted_tiles:
                tint_pos = path_to_world(tile)
                if tint_pos[0] < min_x:
                    min_x = tint_pos[0]
                if tint_pos[0] > max_x:
                    max_x = tint_pos[0]
                if tint_pos[1] < min_y:
                    min_y = tint_pos[1]
                if tint_pos[1] > max_y:
                    max_y = tint_pos[1]
                self.tint_layer.blit(self.red_tile_tint, tint_pos)

            for tile in self.green_tinted_tiles:
                tint_pos = path_to_world(tile)
                if tint_pos[0] < min_x:
                    min_x = tint_pos[0]
                if tint_pos[0] > max_x:
                    max_x = tint_pos[0]
                if tint_pos[1] < min_y:
                    min_y = tint_pos[1]
                if tint_pos[1] > max_y:
                    max_y = tint_pos[1]
                self.tint_layer.blit(self.green_tile_tint, tint_pos)

            # find area of tint layer that needs to be rendered
            self.tint_layer_rect = (min_x, min_y,
                                    max_x - min_x + tile_extent[0] * 2,
                                    max_y - min_y + tile_extent[1] * 2)

        # draw background first
        screen_rect = (-camera_pos[0], -camera_pos[1], a_settings.display_width, a_settings.display_height)
        screen.blit(self.background, (0, 0), screen_rect)

        # render tint layer over background
        if len(self.red_tinted_tiles) + len(self.green_tinted_tiles) > 0:
            screen.blit(self.tint_layer,
                        (camera_pos[0] + self.tint_layer_rect[0], camera_pos[1] + self.tint_layer_rect[1]),
                        self.tint_layer_rect)

        # update mouse coordinates when mouse moves to new tile
        mouse_change = False
        if screen_to_path(pygame.mouse.get_pos()) != self.mouse_coords:
            self.mouse_coords = screen_to_path(pygame.mouse.get_pos())
            mouse_change = True

        # draw path from selected ally entity to highlighted tile
        if self.selected_character is not None:
            screen.blit(self.selection_square, path_to_screen(self.selected_character.position))
            selected_skill = self.selected_character.get_selected_skill()

            if self.selected_character.accepting_input and selected_skill is None \
                    and self.selected_character.has_move is False:
                # calculate a new path whenever destination changes
                if mouse_change:
                    self.path = self.find_path(self.selected_character.position,
                                               self.mouse_coords, self.selected_character.movement)

                # draw arrows along path in direction of path
                if len(self.path) > 1:
                    last_loc = self.path[0]
                    offset = -tile_extent[1]
                    for loc in self.path[1:]:
                        arrow = None
                        if last_loc[0] > loc[0]:
                            if last_loc[1] > loc[1]:
                                # up arrow
                                arrow = pygame.transform.flip(self.path_arrow_vertical, False, True)
                            elif last_loc[1] < loc[1]:
                                # left arrow
                                arrow = pygame.transform.flip(self.path_arrow_horizontal, True, False)
                            else:
                                # up-left arrow
                                arrow = pygame.transform.flip(self.path_arrow, True, True)
                        elif last_loc[0] < loc[0]:
                            if last_loc[1] > loc[1]:
                                # right arrow
                                arrow = self.path_arrow_horizontal
                            elif last_loc[1] < loc[1]:
                                # down arrow
                                arrow = self.path_arrow_vertical
                            else:
                                # down-right arrow
                                arrow = self.path_arrow
                        else:
                            if last_loc[1] > loc[1]:
                                # up-right arrow
                                arrow = pygame.transform.flip(self.path_arrow, False, True)
                            elif last_loc[1] < loc[1]:
                                # down-left arrow
                                arrow = pygame.transform.flip(self.path_arrow, True, False)
                            else:
                                print("ERROR: supplied path contains duplicate points")

                        render_loc = path_to_screen(loc)
                        screen.blit(arrow, (render_loc[0], render_loc[1] + offset))
                        last_loc = loc
            elif mouse_change and selected_skill is not None and selected_skill.get_data("area") > 0:
                # render the area that will be hit by an area skill
                self.clear_tinted_tiles()
                if not selected_skill.get_data("line of sight") or \
                        self.line_of_sight(self.selected_character.position,
                                           self.mouse_coords, selected_skill.get_data("range")):

                    self.red_tinted_tiles = self.make_radius(self.mouse_coords, selected_skill.get_data("area"), True)

        # draw highlighted square around mouse position
        screen.blit(self.selection_square, path_to_screen(self.mouse_coords))

        # draw all entities onscreen
        for e in self.entity_list:
            e.upkeep(deltatime)
            # draw the entity if it is onscreen
            render_pos = e.get_render_pos()
            if onscreen_path(render_pos):
                # mask the entity's image where a tile is overlapping it
                tile_pos = (round(render_pos[0]), round(render_pos[1]))
                masks = []
                for offset in [(0, 1), (1, 0), (1, 1)]:
                    new_tile = (tile_pos[0] + offset[0], tile_pos[1] + offset[1])
                    if self.in_bounds(new_tile, False):
                        map_tile = path_to_map(new_tile)
                        attributes = self.tile_list[tuple(map_tile)]
                        if attributes.height > 0:
                            masks.append(Mask(new_tile, attributes.height,
                                              self.tile_masks[attributes.tile_id]))
                e.render(screen, masks)

        # draw character UI elements last
        for c in self.character_list:
            c.second_render(screen)

        # finally draw tile map UI
        self.interface.render(screen)

    def notify(self, event):
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "end turn":
                self.interface.set_button_active("end turn", False)
                self.end_turn()
            return

        # check if an entity's UI eats the input
        for c in self.character_list:
            if c.notify(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_coords = screen_to_path(pygame.mouse.get_pos())

            if event.button == 1:
                # check if skill or movement is selected
                free_aim = False
                selected_skill = None
                if self.selected_character is not None:
                    selected_skill = self.selected_character.get_selected_skill()
                    if selected_skill is not None and selected_skill.get_data("area") > 0:
                        free_aim = True

                if not free_aim:
                    # if a character is clicked on, select them
                    for c in self.character_list:
                        if mouse_coords == c.position:

                            if not c.ally and self.selected_character is not None \
                                    and self.selected_character.use_skill():
                                self.attack_tiles(mouse_coords, selected_skill)
                                self.selected_character.set_selected(False)
                                self.selected_character = None
                                self.clear_tinted_tiles()
                                return

                            # deselect previous character and select the new one
                            if self.selected_character is not None:
                                self.selected_character.set_selected(False)
                            self.selected_character = c
                            self.clear_tinted_tiles()
                            c.set_selected(True)

                            return 0

                    # move selected character to unoccupied position if able
                    if self.selected_character is not None and self.selected_character.accepting_input:
                        if self.selected_character.commit_move(self.path):
                            self.clear_tinted_tiles()
                elif self.selected_character.use_skill():
                    # center attack on clicked tile if free aiming
                    self.attack_tiles(mouse_coords, selected_skill)
                    self.selected_character.set_selected(False)
                    self.selected_character = None
                    self.clear_tinted_tiles()

            elif event.button == 3:
                if self.selected_character is not None:
                    if self.selected_character.get_selected_skill() is None:
                        # right click to deselect unit
                        self.selected_character.set_selected(False)
                        self.selected_character = None
                        self.clear_tinted_tiles()
                    else:
                        # right click to cancel attack
                        self.selected_character.set_selected(True)

    def add_entities(self, filename):
        with open(filename) as f:
            entity_data = json.load(f)
            for c in entity_data["characters"]:
                new_character = None
                if c["team"] == 0:
                    new_character = character.Character(self.get_spawn(), self, c)
                else:
                    new_character = character.AICharacter(self.get_spawn(), self, self.ai_manager, c)
                    self.ai_manager.add_actor(new_character)
                self.character_list.append(new_character)
                self.entity_list.append(new_character)
        self.z_order_sort_entities()

    def get_spawn(self):
        spawn_pos = self.spawn_points[self.spawns_used]
        self.spawns_used += 1
        return spawn_pos

    def get_tile_path(self, coords):
        map_coords = path_to_map(coords)
        return self.tile_list[(map_coords[0], map_coords[1])]

    def z_order_sort_entities(self):
        self.entity_list.sort()

    def in_bounds(self, coords, walkable_only):
        # valid if: x >= y, x + y > 0, x + y < map_height, x - y < map_width * 2
        if coords[0] < abs(coords[1]) or coords[0] + coords[1] >= self.map_height \
                or coords[0] - coords[1] >= self.map_width * 2:
            return False
        if walkable_only:
            return self.get_tile_path(coords).walkable
        return True

    def clear_tinted_tiles(self):
        for tile in self.red_tinted_tiles.union(self.green_tinted_tiles):
            tile_pos = path_to_world(tile)
            self.tint_layer.fill((0, 0, 0), (tile_pos[0], tile_pos[1], tile_extent[0] * 2, tile_extent[1] * 2))
        self.red_tinted_tiles.clear()
        self.green_tinted_tiles.clear()
        self.tint_layer_update = True

    def display_skill(self, skill):
        if skill.get_data("area") == 0:
            self.clear_tinted_tiles()
            for e in self.character_list:
                if not e.ally \
                        and self.line_of_sight(self.selected_character.position, e.position, skill.get_data("range")):
                    self.red_tinted_tiles.add((e.position[0], e.position[1]))

    def display_movement(self, this_character):
        self.possible_paths = self.find_all_paths(this_character.position, this_character.movement)
        # self.last_path_test = character.position
        # show possible movement tiles for selected character
        self.clear_tinted_tiles()
        self.green_tinted_tiles = self.possible_paths
        # dirty the mouse coordinates so there will be an immediate path update
        self.mouse_coords = (-1, -1)

    def attack_tiles(self, center, skill):
        for tile in self.make_radius(center, skill.get_data("area"), skill.get_data("line of sight")):
            for c in self.character_list:
                if not c.ally and c.position[0] == tile[0] and c.position[1] == tile[1]:
                    c.attack_with(skill)

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
                    if neighbor not in closed_list:
                        if self.in_bounds(neighbor, walkable_only):
                            open_list.add(neighbor)
        return closed_list

    def line_of_sight(self, p0, p1, length=9999):
        line = supercover_line(p0, p1)
        if len(line) > length:
            return False
        for tile in line:
            if not self.in_bounds(tile, True):
                return False
        return True

    def find_all_paths(self, start, max_length, need_los=False):
        # Create start node
        start_node = Node(None, tuple(start))

        # Initialize both open and closed list
        open_list = []
        closed_list = set()

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
                    continue

                # test line of sight if required (projectile attacks for example)
                if need_los and not self.line_of_sight(start, node_position):
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

                # node is already in the open list
                if node_position in open_list_pos:
                    continue

                # Create new node
                new_node = Node(current_node, node_position)
                new_node.g = g

                # Append
                open_list.append(new_node)
                open_list_pos.add(new_node.position)
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

                # Create the f, g, and h values
                dx = abs(node_position[0] - end[0])
                dy = abs(node_position[1] - end[1])
                h = ((dx + dy) + (-0.58) * min(dx, dy)) * 1.02
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
            self.selected_character.set_selected(False)
            self.selected_character = None
        for c in self.character_list:
            c.start_of_turn_update()
        self.interface.set_button_active("end turn", True)

    def end_turn(self):
        self.clear_tinted_tiles()
        if self.selected_character is not None:
            self.selected_character.set_selected(False)
            self.selected_character = None
        for c in self.character_list:
            c.end_of_turn_update()
        self.ai_manager.start_ai_turn()
