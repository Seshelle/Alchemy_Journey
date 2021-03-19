import pygame
import random
from tilemap import Camera
import alchemy_settings as a_settings
from game_state import GameState
import game_modes
from weighted_table import WeightedTable


class Icon:
    size = 64
    grid_size = size * 3
    grid_variation = size
    combat = "combat"
    elite_combat = "elite"
    heal = "heal"
    loot = "loot"
    shop = "shop"
    mystery = "mystery"
    important = "important"
    number = 6


class PathNode:
    def __init__(self, grid_pos=(-1, -1), symbol=None):
        self.grid_pos = grid_pos
        scatter = [random.randint(0, Icon.grid_variation), random.randint(0, round(Icon.grid_variation / 2))]
        self.world_pos = (
            grid_pos[0] * Icon.grid_size + scatter[0],
            grid_pos[1] * Icon.grid_size + scatter[1]
        )
        self.symbol = symbol
        self.next_nodes = []
        self.has_entrance = False
        self.has_exit = False

    def set_encounter(self, symbol):
        self.symbol = symbol

    def add_next_node(self, node):
        node.has_entrance = True
        self.next_nodes.append(node)
        self.has_exit = True

    def make_previous(self, node):
        node.add_next_node(self)

    def add_closest_node(self, node_list, as_exit=True):
        chosen_node = self.find_closest_node(node_list, as_exit)
        if chosen_node is not None:
            if as_exit:
                self.add_next_node(chosen_node)
            else:
                chosen_node.add_next_node(self)

    def find_closest_node(self, node_list, as_exit=True):
        closest = 999
        chosen_node = None
        for node in node_list:
            distance = abs(node.grid_pos[0] - self.grid_pos[0])
            tie_breaker = random.random() / 2
            if distance + tie_breaker < closest:
                if as_exit and node not in self.next_nodes:
                    closest = distance
                    chosen_node = node
                elif not as_exit and self not in node.next_nodes:
                    closest = distance
                    chosen_node = node
        return chosen_node

    def mouse_overlap(self, mouse_pos):
        if self.symbol is None:
            return False
        screen_pos = [self.world_pos[0] + Camera.pos[0], self.world_pos[1] + Camera.pos[1]]
        if screen_pos[0] < mouse_pos[0] < screen_pos[0] + Icon.size and \
                screen_pos[1] < mouse_pos[1] < screen_pos[1] + Icon.size:
            return True


class StrategyMap:
    def __init__(self):
        self.map_icons = {
            Icon.combat: pygame.image.load("images/icons/combat_icon.png").convert(),
            Icon.elite_combat: pygame.image.load("images/icons/elite_combat_icon.png").convert(),
            Icon.important: pygame.image.load("images/icons/important_icon.png").convert(),
            Icon.loot: pygame.image.load("images/icons/key_icon.png").convert(),
            Icon.shop: pygame.image.load("images/icons/lock_icon.png").convert(),
            Icon.mystery: pygame.image.load("images/icons/mystery_icon.png").convert(),
            Icon.heal: pygame.image.load("images/icons/replenish_icon.png").convert()
        }

        for icon in self.map_icons.values():
            icon.set_colorkey(pygame.Color("black"))

        # create map symbol grid
        self.grid_width = 7
        self.grid_height = 12
        self.path_grid = []
        blank_column = []
        for i in range(self.grid_height):
            blank_column.append(PathNode())
        for i in range(self.grid_width):
            # create an empty grid
            self.path_grid.append(blank_column.copy())
        self.grid_seed = random.random()

        # create dots for dotted line
        self.path_dot = pygame.Surface((16, 16)).convert()
        self.path_dot.fill(pygame.Color("black"))

        # center camera at bottom of map
        Camera.pos[0] = (a_settings.display_width - self.grid_width * Icon.grid_size) / 2
        Camera.pos[1] = -self.grid_height * Icon.grid_size + a_settings.display_height

        # generate potential paths from seed
        random.seed(GameState.expedition_seed)
        random.seed()

        # put one event node at the end
        end_pos = round(self.grid_width / 2)
        self.path_grid[end_pos][0] = PathNode((end_pos, 0), Icon.important)

        # create weighted tables to pull encounters from
        table_file = "data/encounter_tables.json"
        start_table = WeightedTable(table_file, "start")
        beginning_table = WeightedTable(table_file, "beginning")
        middle_table = WeightedTable(table_file, "middle")
        end_table = WeightedTable(table_file, "end")

        # put 3-5 nodes in each row and connect them to next row
        for y in range(1, self.grid_height):

            # generate encounter nodes in each row
            free_nodes = list(range(self.grid_width))
            for i in range(random.randint(4, 5)):
                column = random.choice(free_nodes)
                free_nodes.remove(column)
                # get encounter type from weighted table
                reduction = 4
                if y == 1:
                    if random.random() < 0.85:
                        encounter = "heal"
                    else:
                        encounter = "loot"
                elif y <= 3:
                    encounter = end_table.roll_reduction(reduction)
                elif y <= 7:
                    encounter = middle_table.roll_reduction(reduction)
                elif y <= 10:
                    encounter = beginning_table.roll_reduction(reduction)
                else:
                    encounter = start_table.roll_reduction(reduction)
                self.path_grid[column][y] = PathNode((column, y), encounter)

            current_nodes = []
            next_nodes = []
            for x in range(self.grid_width):
                if self.path_grid[x][y].symbol is not None:
                    current_nodes.append(self.path_grid[x][y])
                if self.path_grid[x][y - 1].symbol is not None:
                    next_nodes.append(self.path_grid[x][y - 1])

            if len(next_nodes) == 1:
                for node in current_nodes:
                    node.add_next_node(next_nodes[0])
                continue

            branch_chance = 0.6
            # connect outermost nodes
            current_nodes[0].add_next_node(next_nodes[0])
            current_nodes[-1].add_next_node(next_nodes[-1])
            # connect the remaining middle ones
            for node in next_nodes:
                if not node.has_entrance:
                    node.add_closest_node(current_nodes, False)
            for node in current_nodes:
                if not node.has_exit:
                    node.add_closest_node(next_nodes)
            # randomly add additional branching paths
            for node in current_nodes:
                if len(node.next_nodes) < 2 and random.random() < branch_chance:
                    chosen_node = node.find_closest_node(next_nodes)
                    # check if there are any paths that would overlap this new path
                    blocked = False
                    diff = chosen_node.grid_pos[0] - node.grid_pos[0]
                    if diff > 0:
                        step = 1
                    else:
                        step = -1
                    # check if there are any nodes along current row that connect to a
                    # next node between the planned connection points
                    for blocking_node in current_nodes:
                        if node.grid_pos[0] * step < blocking_node.grid_pos[0] * step:
                            for path in blocking_node.next_nodes:
                                if path.grid_pos[0] * step < chosen_node.grid_pos[0] * step:
                                    blocked = True
                                    break
                    if not blocked:
                        node.add_next_node(chosen_node)

        # draw paths between connected nodes
        self.map_image = pygame.Surface(
            (self.grid_width * Icon.grid_size + Icon.grid_variation,
             self.grid_height * Icon.grid_size + Icon.grid_variation)
        ).convert()
        self.map_image.fill((190, 140, 90))
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                path_node = self.path_grid[x][y]
                path_pos = [
                    path_node.world_pos[0] + Icon.size / 2,
                    path_node.world_pos[1] + Icon.size / 3
                ]
                for next_node in path_node.next_nodes:
                    # if two shops are in a row, change one of them to a normal combat encounter
                    if path_node.symbol == "shop" and next_node.symbol == "shop":
                        path_node.set_encounter("combat")
                    next_pos = [
                        next_node.world_pos[0] + Icon.size / 2,
                        next_node.world_pos[1] + Icon.size * 2 / 3
                    ]
                    pygame.draw.line(self.map_image, pygame.Color("black"), path_pos, next_pos, 3)

        # draw all symbols to the map
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                node = self.path_grid[x][y]
                if node.symbol is not None:
                    self.map_image.blit(self.map_icons[node.symbol], node.world_pos)

        self.change_scene = False
        self.next_scene = None
        self.expedition_location = GameState.expedition_location
        if self.expedition_location[1] >= 0:
            self.circle_node(self.expedition_location)
        random.seed()

    def update(self, deltatime):

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            Camera.pos[1] += deltatime * Camera.speed
        if keys[pygame.K_s]:
            Camera.pos[1] -= deltatime * Camera.speed
        if keys[pygame.K_a]:
            Camera.pos[0] += deltatime * Camera.speed
        if keys[pygame.K_d]:
            Camera.pos[0] -= deltatime * Camera.speed

    def render(self, screen):
        screen.fill((190, 140, 90))
        screen.blit(self.map_image, Camera.pos)

    def notify(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            location = GameState.expedition_location
            # check if mouse over a symbol on correct row
            if location[1] < 0:
                # row < 0 means choose between starting locations
                for i in range(self.grid_width):
                    node = self.path_grid[i][self.grid_height - 1]
                    if node.mouse_overlap(mouse_pos):
                        return self.go_to_scene(node.grid_pos)
            else:
                current_node = self.path_grid[location[0]][location[1]]
                for next_node in current_node.next_nodes:
                    if next_node.mouse_overlap(mouse_pos):
                        GameState.expedition_location = next_node.grid_pos
                        return self.go_to_scene(next_node.grid_pos)
        return None

    def circle_node(self, grid_pos):
        node = self.path_grid[grid_pos[0]][grid_pos[1]]
        center = (node.world_pos[0] + round(Icon.size / 2), node.world_pos[1] + round(Icon.size / 2))
        pygame.draw.circle(self.map_image, pygame.Color("black"), center, round(Icon.size / 2), 4)

    def go_to_scene(self, grid_pos):
        GameState.expedition_location = grid_pos
        area = self.path_grid[grid_pos[0]][grid_pos[1]]
        return game_modes.CombatScene("data/combat_test_scene.json")

