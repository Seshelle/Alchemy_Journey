import pygame
import random
from tilemap import Camera
import alchemy_settings as a_settings
import math


class Icon:
    size = 64
    combat = 0
    elite_combat = 1
    replenish = 2
    key = 3
    lock = 4
    mystery = 5
    important = 6
    number = 6


class PathNode:
    def __init__(self, grid_pos=(-1, -1), symbol=-1):
        self.grid_pos = grid_pos
        self.symbol = symbol
        self.next_nodes = []
        self.has_entrance = False
        self.has_exit = False

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


class StrategyMap:
    def __init__(self):
        self.map_icons = {
            Icon.combat: pygame.image.load("images/icons/combat_icon.png").convert(),
            Icon.elite_combat: pygame.image.load("images/icons/elite_combat_icon.png").convert(),
            Icon.important: pygame.image.load("images/icons/important_icon.png").convert(),
            Icon.key: pygame.image.load("images/icons/key_icon.png").convert(),
            Icon.lock: pygame.image.load("images/icons/lock_icon.png").convert(),
            Icon.mystery: pygame.image.load("images/icons/mystery_icon.png").convert(),
            Icon.replenish: pygame.image.load("images/icons/replenish_icon.png").convert()
        }

        for icon in self.map_icons.values():
            icon.set_colorkey(pygame.Color("black"))

        # create map symbol grid
        self.grid_width = 7
        self.grid_height = 12
        self.grid_size = Icon.size * 3
        self.grid_variation = Icon.size
        self.path_grid = []
        self.offset_grid = []
        blank_column = []
        for i in range(self.grid_height):
            blank_column.append(PathNode())
        for i in range(self.grid_width):
            # create an empty grid
            self.path_grid.append(blank_column.copy())
            offset_column = []
            # randomly offset the symbols so they look less grid-like
            for j in range(self.grid_height):
                if j > 1:
                    offset_column.append(
                        (random.randint(0, self.grid_variation),
                         random.randint(0, self.grid_variation))
                    )
                else:
                    offset_column.append((0, 0))
            self.offset_grid.append(offset_column)
        self.grid_seed = random.random()

        # create dots for dotted line
        self.path_dot = pygame.Surface((16, 16)).convert()
        self.path_dot.fill(pygame.Color("black"))

        # center camera at bottom of map
        Camera.pos[0] = (a_settings.display_width - self.grid_width * self.grid_size) / 2
        Camera.pos[1] = -self.grid_height * self.grid_size + a_settings.display_height

        # generate potential paths from seed
        # random.seed(9)

        # put one event node at the end
        end_pos = round(self.grid_width / 2)
        self.path_grid[end_pos][0] = PathNode((end_pos, 0), Icon.important)
        # put 3-5 nodes in each row and connect them to next row
        for y in range(1, self.grid_height):

            # create 3 - 5 nodes in each row
            free_nodes = list(range(self.grid_width))
            for i in range(random.randint(3, 5)):
                column = random.choice(free_nodes)
                free_nodes.remove(column)
                self.path_grid[column][y] = PathNode((column, y), random.randint(0, Icon.number - 1))

            current_nodes = []
            next_nodes = []
            for x in range(self.grid_width):
                if self.path_grid[x][y].symbol != -1:
                    current_nodes.append(self.path_grid[x][y])
                if self.path_grid[x][y - 1].symbol != -1:
                    next_nodes.append(self.path_grid[x][y - 1])

            if len(next_nodes) == 1:
                for node in current_nodes:
                    node.add_next_node(next_nodes[0])
                continue

            branch_chance = 0.1
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
                    # next node in between the planned connection points
                    for blocking_node in current_nodes:
                        if node.grid_pos[0] * step < blocking_node.grid_pos[0] * step <= chosen_node.grid_pos[0] * step:
                            for path in blocking_node.next_nodes:
                                if path.grid_pos[0] * step < chosen_node.grid_pos[0] * step:
                                    blocked = True
                                    break
                    if not blocked:
                        node.add_next_node(chosen_node)

        # draw paths between connected nodes
        self.map_image = pygame.Surface(
            (self.grid_width * self.grid_size + self.grid_variation,
             self.grid_height * self.grid_size + self.grid_variation)
        ).convert()
        self.map_image.fill((190, 140, 90))
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                path_node = self.path_grid[x][y]
                path_pos = [
                    x * self.grid_size + Icon.size / 2 + self.offset_grid[x][y][0],
                    y * self.grid_size + Icon.size / 3 + self.offset_grid[x][y][1]
                ]
                for next_node in path_node.next_nodes:
                    n_pos = next_node.grid_pos
                    next_pos = [
                        n_pos[0] * self.grid_size + Icon.size / 2 + self.offset_grid[n_pos[0]][n_pos[1]][0],
                        n_pos[1] * self.grid_size + Icon.size * 2 / 3 + self.offset_grid[n_pos[0]][n_pos[1]][1]
                    ]
                    pygame.draw.line(self.map_image, pygame.Color("black"), path_pos, next_pos, 3)

        # draw all symbols to the map
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                symbol = self.path_grid[x][y].symbol
                if symbol >= 0:
                    self.map_image.blit(
                        self.map_icons[symbol],
                        (x * self.grid_size + self.offset_grid[x][y][0],
                         y * self.grid_size + self.offset_grid[x][y][1])
                    )

    def update(self, deltatime, screen):

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            Camera.pos[1] += deltatime * Camera.speed
        if keys[pygame.K_s]:
            Camera.pos[1] -= deltatime * Camera.speed
        if keys[pygame.K_a]:
            Camera.pos[0] += deltatime * Camera.speed
        if keys[pygame.K_d]:
            Camera.pos[0] -= deltatime * Camera.speed

        screen.fill((190, 140, 90))
        screen.blit(self.map_image, Camera.pos)

    def notify(self, event):
        # TODO: click node to go to combat
        pass
