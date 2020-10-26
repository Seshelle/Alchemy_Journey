import entity
import tilemap
import user_interface
import math


class Skill:
    def __init__(self, skill_data, user):
        self.data = skill_data
        self.user = user

    def get_data(self, key):
        if key in self.data.keys():
            return self.data[key]
        else:
            return None


class StatusEffect:
    def __init__(self):
        pass

    def apply_effect(self, attack_hit):
        pass

    def start_turn_effect(self):
        pass

    def end_turn_effect(self):
        pass


class Character(entity.Entity):

    def __init__(self, position, current_map, entity_data):
        super().__init__(position, entity_data)
        self.current_map = current_map
        # visual position is where it is rendered, like when moving
        self.visual_position = [position[0], position[1]]

        # path the entity is moving along, empty when not moving
        self.path = []
        self.prev_direction = []

        # determines whether you can command this entity
        self.intelligent = True
        self.ally = True
        self.accepting_input = True
        self.selected = False

        # current state of character
        self.has_move = False
        self.has_action = False
        self.status_effects = []

        # attributes of this character
        self.team = entity_data["team"]
        self.max_health = entity_data["health"]
        self.health = self.max_health
        self.movement = entity_data["movement"]

        # skill attributes: range, area, min damage, max damage, accuracy, critical chance, mana cost
        self.skills = []
        self.skill_interface = user_interface.UserInterface()
        self.skill_interface.set_active(False)
        self.selected_skill = None

        self.skill_interface.add_button((0.05, 0.8, 0.1, 0.05), entity_data["name"], None)

        for skill_data in entity_data["skills"]:
            self.add_skill(Skill(skill_data, self))

    def get_z(self):
        return self.visual_position[0] + self.visual_position[1] + 0.001

    def get_render_pos(self):
        return self.visual_position

    def upkeep(self, deltatime):
        # animate along path if path is not empty
        if len(self.path) > 0:
            # set destination as next path node
            destination = self.path[0]
            move = [destination[0] - self.visual_position[0], destination[1] - self.visual_position[1]]
            distance = move[0] ** 2 + move[1] ** 2
            # if direction to next path node changes suddenly, move to next node
            if distance == 0 or [move[0] > 0, move[1] > 0] != self.prev_direction:
                self.path.remove(self.path[0])
                self.current_map.z_order_sort_entities()
                if len(self.path) == 0:
                    # no more path nodes, snap into final position
                    self.visual_position = destination
                    if self.ally:
                        self.accepting_input = True
                    self.finish_move()
                else:
                    # get next path node and move towards that now
                    destination = self.path[0]
                    move = [destination[0] - self.visual_position[0], destination[1] - self.visual_position[1]]
                    # remember which direction the path node is in
                    self.prev_direction = [move[0] > 0, move[1] > 0]
            else:
                self.prev_direction = [move[0] > 0, move[1] > 0]
                # move at constant speed to next path node
                self.visual_position = [self.visual_position[0] + (move[0] / math.sqrt(distance)) * deltatime / 300,
                                        self.visual_position[1] + (move[1] / math.sqrt(distance)) * deltatime / 300]

    def finish_move(self):
        pass

    def render(self, screen, masks=None):
        screen_pos = tilemap.path_to_screen(self.visual_position)
        if masks is not None and len(masks) > 0:
            masked_image = self.appearance.copy()
            for m in masks:
                offset = (m.position[0] - self.visual_position[0], m.position[1] - self.visual_position[1])
                offset = tilemap.path_to_screen(offset, False)
                masked_image.blit(m.image, (offset[0], offset[1] + self.height - m.height))
            screen.blit(masked_image, (screen_pos[0], screen_pos[1] - self.height))
        else:
            screen.blit(self.appearance, (screen_pos[0], screen_pos[1] - self.height))

    def second_render(self, screen):
        self.skill_interface.render(screen)

    def notify(self, event):
        if not self.has_action:
            skill_id = self.skill_interface.notify(event)
            if skill_id is not None:
                self.selected_skill = self.skills[skill_id]
                self.current_map.display_skill(self.selected_skill)
                return True
        return False

    def set_ally(self, is_ally):
        self.ally = is_ally
        self.accepting_input = is_ally
        self.skill_interface.set_active(False)

    def set_selected(self, selected):
        self.selected = selected
        self.skill_interface.set_active(selected)
        self.selected_skill = None
        if selected and not self.has_move:
            self.current_map.display_movement(self)

    def add_skill(self, skill):
        self.skills.append(skill)
        self.skill_interface.add_button((0.15 * len(self.skills), 0.9, 0.1, 0.05),
                                        skill.data["name"], len(self.skills) - 1)

    def get_selected_skill(self):
        if self.ally:
            return self.selected_skill
        else:
            return None

    def has_ai(self):
        return False

    def start_of_turn_update(self):
        self.has_move = False
        self.has_action = False
        self.accepting_input = self.ally

    def end_of_turn_update(self):
        self.accepting_input = False

    def commit_move(self, path):
        if not self.has_move and len(path) > 1:
            self.path = path
            self.position = [path[-1][0], path[-1][1]]
            self.current_map.z_order_sort_entities()
            self.visual_position = path[0]
            self.accepting_input = False
            self.has_move = True
            return True
        self.finish_move()
        return False

    def use_action(self):
        self.has_action = True
        self.has_move = True
        self.accepting_input = False

    def use_skill(self):
        # executes selected skill
        # if skill is successfully used, returns True
        if self.has_action and self.selected_skill is not None:
            self.use_action()
            return True
        return False

    def attack_with(self, skill):
        self.health -= skill.get_data("minimum damage")
        print(self.health)

    def is_moving(self):
        return len(self.path) > 0


class AICharacter(Character):
    def __init__(self, position, current_map, ai_manager, entity_data):
        super().__init__(position, current_map, entity_data)
        self.ally = False
        self.accepting_input = False
        self.AI_active = False
        self.manager = ai_manager

    def notify(self, event):
        return False

    def has_ai(self):
        return True

    def set_manager(self, manager):
        self.manager = manager

    def ai_move(self):
        # get all possible move locations

        all_moves = self.current_map.find_all_paths(self.position, self.movement)
        closest_target_distance = 99999
        closest_target = None
        for c in self.current_map.character_list:
            # don't move into occupied tiles
            all_moves.discard(tuple(c.position))
            # find closest enemy
            if c.ally:
                distance = tilemap.distance_between(self.position, c.position)
                if distance < closest_target_distance:
                    closest_target_distance = distance
                    closest_target = c

        all_moves.add(tuple(self.position))
        best_score = -999999
        best_move = None
        for move in all_moves:
            # try to get as close as possible to the closest enemy
            move_score = -tilemap.distance_between(move, closest_target.position)
            if move_score > best_score:
                best_score = move_score
                best_move = move

        self.commit_move(self.current_map.find_path(self.position, best_move, self.movement))

    def finish_move(self):
        # use action
        attack_tiles = self.current_map.find_all_paths(self.position, self.skills[0].get_data("range"), True)
        attack_targets = []
        for c in self.current_map.character_list:
            if c.ally and tuple(c.position) in attack_tiles:
                attack_targets.append(c)

        if len(attack_targets) > 0:
            attack_targets[0].attack_with(self.skills[0])

        self.manager.next_actor(self)

    def end_of_turn_update(self):
        self.has_action = False
        self.AI_active = True

    def start_of_turn_update(self):
        self.AI_active = False
        self.has_move = False