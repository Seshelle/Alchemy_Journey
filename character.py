import pygame
import entity
import tilemap
import user_interface
import math
from random import randint
from math import ceil
import skill_handler
from skill_handler import SkillKeys
from dialogue import draw_shadowed_text
from dialogue import draw_text
import json


class CharacterKeys:
    name = "name"
    upgrades = "upgrades"
    team = "team"
    max_health = "health"
    armor = "armor"
    current_health = "current health"
    movement = "movement"
    skills = "skills"
    max_mana = "mana"
    current_mana = "current mana"
    action_points = "action points"


class CharacterModifiers:
    damage = "damage"
    accuracy = "accuracy"
    dodge = "dodge"
    evasion = "evasion"
    armor = "armor"
    movement = "movement"
    health = "health"


class Character(entity.Entity):
    def __init__(self, position, current_map, entity_data):
        super().__init__(position, current_map, entity_data)
        self.current_map = current_map

        # visual position is where it is rendered, separate from actual tile position
        self.visual_position = [position[0], position[1]]

        # path the entity is moving along, empty when not moving
        self.path = []
        self.prev_direction = []

        # determines whether player can command this entity
        self.ally = True
        self.accepting_input = True
        self.selected = False

        # current state of character
        self.action_points = 2
        self.has_bonus_action = True
        self.used_skill = False
        self.knocked_out = False
        self.stabilized = False
        self.knockout_timer = 3
        self.status_effects = []
        self.modifiers = {}
        self.show_ui = True

        # attributes of this character
        self.name = self.data[CharacterKeys.name]
        if CharacterKeys.max_health not in self.data:
            self.data[CharacterKeys.max_health] = 12

        max_health = self.get_data(CharacterKeys.max_health)
        if CharacterKeys.current_health not in self.data:
            self.data[CharacterKeys.current_health] = max_health
        else:
            current_health = self.data[CharacterKeys.current_health]
            if current_health > max_health:
                current_health = max_health
            elif current_health < 1:
                current_health = 1
            self.data[CharacterKeys.current_health] = current_health

        if CharacterKeys.movement not in self.data:
            self.data[CharacterKeys.movement] = 4

        if CharacterKeys.max_mana not in self.data:
            self.data[CharacterKeys.max_mana] = 12

        max_mana = self.get_data(CharacterKeys.max_mana)
        if CharacterKeys.current_mana not in self.data:
            self.data[CharacterKeys.current_mana] = max_mana
        else:
            mana = self.data[CharacterKeys.current_mana]
            if mana > max_mana:
                mana = max_mana
            elif mana < 0:
                mana = 0
            self.data[CharacterKeys.current_mana] = mana

        if CharacterKeys.action_points not in self.data:
            self.data[CharacterKeys.action_points] = 2

        # create health bar image
        self.stat_text = pygame.font.SysFont(None, 24)
        self.bar_alpha = 125
        self.bar_height = 20
        self.bar_width = tilemap.tile_extent[0] * 2
        self.health_bar = pygame.Surface((self.bar_width, self.bar_height)).convert()
        self.health_color = pygame.Color("green")
        self.missing_health_color = pygame.Color("gray")
        self.health_bar.set_alpha(self.bar_alpha)

        # create mana bar image
        self.mana_bar = pygame.Surface((self.bar_width, self.bar_height)).convert()
        self.mana_color = pygame.Color("blue")
        self.mana_bar.set_alpha(self.bar_alpha)
        self.update_health_and_mana()

        # create hit chance indicator
        self.chance_image = pygame.Surface((tilemap.tile_extent[0], tilemap.tile_extent[1]))
        self.chance_image.set_colorkey(pygame.Color("black"))
        self.font = pygame.font.SysFont(None, 30)
        self.chance_image_active = False

        # create damage indicator
        self.damage_indicator = pygame.Surface((self.bar_width, self.bar_height)).convert()
        self.damage_indicator.fill(pygame.Color("purple"))
        self.damage_indicator.set_colorkey(pygame.Color("purple"))
        self.damage_indicator_fade = 0
        self.damage_indicator_height = self.bar_height * 3

        # load skill data and display it on character interface
        self.skills = []
        self.skill_interface = user_interface.UserInterface()
        self.skill_interface.add_image_button(
            (0, 0.9, 0.2, 0.1),
            self.data[CharacterKeys.name],
            "avatar", is_button=False
        )
        self.skill_interface.set_active(False)
        self.selected_skill_id = None
        skill_file = open("data/stats/skill_list.json")
        skill_list = json.load(skill_file)
        skill_file.close()
        for skill_name in self.data[CharacterKeys.skills]:
            skill_data = None
            if CharacterKeys.upgrades not in self.data:
                # if no skill levels are defined, default them to level 1
                skill_data = skill_list[skill_name]
            elif skill_name in self.data[CharacterKeys.upgrades]:
                # if skill is above level one, upgrade it according to its level data
                skill_data = skill_list[skill_name]
                skill_level = self.data[CharacterKeys.upgrades][skill_name]
                if skill_level > 1:
                    level_data = skill_data[SkillKeys.levels][skill_level - 2]
                    for upgrade in level_data:
                        skill_data[upgrade] = level_data[upgrade]

            if skill_data is not None:
                if SkillKeys.code in skill_data:
                    skill_code = skill_data[SkillKeys.code]
                else:
                    skill_code = "Default"
                self.add_skill(skill_handler.skill_list[skill_code](skill_data, self))

        # skill animation state
        self.active_skill = None

    def get_data(self, key):
        data = 0
        if key in self.data.keys():
            data = self.data[key]
        if key in self.modifiers.keys():
            data += self.modifiers[key]
        return data

    def get_movement(self):
        movement = self.get_data(CharacterKeys.movement)
        if self.action_points == 1:
            movement = movement / 2 + 0.5
        return movement

    def get_total_movement(self):
        if self.has_actions():
            movement = self.get_data(CharacterKeys.movement)
            return movement * (self.action_points - 1) + movement / 2 + 0.5
        return 0

    def has_actions(self):
        return self.action_points > 0

    def can_use_skill(self, bonus_action=False):
        if bonus_action is False:
            return self.action_points > 0 and self.used_skill is False
        return self.has_bonus_action

    def get_z(self):
        return self.visual_position[0] + self.visual_position[1] + 0.001

    def get_render_pos(self):
        return self.visual_position

    def update(self, deltatime):
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
                    self.finish_move()
                else:
                    # get next path node and move towards that now
                    destination = self.path[0]
                    move = [destination[0] - self.visual_position[0], destination[1] - self.visual_position[1]]
                    # remember which direction the path node is in
                    self.prev_direction = [move[0] > 0, move[1] > 0]
            else:
                distance = math.sqrt(distance)
                self.prev_direction = [move[0] > 0, move[1] > 0]
                # move at constant speed to next path node
                self.visual_position = [self.visual_position[0] + (move[0] / distance) * deltatime / 300,
                                        self.visual_position[1] + (move[1] / distance) * deltatime / 300]

        if self.active_skill is not None and not self.active_skill.update(deltatime):
            self.active_skill = None

        # move damage indicator up and fade it out if it is active
        if self.damage_indicator_fade > 0:
            self.damage_indicator_fade -= 0.25 * deltatime
            self.damage_indicator_height += 0.05 * deltatime

    def finish_move(self):
        self.path.clear()
        self.accepting_input = not self.knocked_out
        if self.accepting_input and self.selected:
            self.set_selected(True)

    def render(self, screen, masks=None):
        screen_pos = tilemap.path_to_screen(self.visual_position)
        if masks is not None and len(masks) > 0:
            masked_image = self.appearance.copy()
            for m in masks:
                # cut out portions of the character that are overlapped by terrain tiles
                offset = (m.position[0] - self.visual_position[0], m.position[1] - self.visual_position[1])
                offset = tilemap.path_to_screen(offset, False)
                masked_image.blit(m.image, (offset[0], offset[1] + self.get_height(False) - m.height))
            self.render_with_zoom(masked_image, screen, (screen_pos[0], screen_pos[1] - self.get_height()))
        else:
            self.render_with_zoom(self.appearance, screen, (screen_pos[0], screen_pos[1] - self.get_height()))

    def second_render(self, screen):
        # render health and mana bars
        if self.show_ui:
            screen_pos = tilemap.path_to_screen(self.visual_position)
            height = self.get_height()
            screen.blit(self.health_bar, (screen_pos[0], screen_pos[1] - height - self.bar_height))
            screen.blit(self.mana_bar, (screen_pos[0], screen_pos[1] - height))
            if self.chance_image_active:
                screen.blit(self.chance_image, (screen_pos[0] + tilemap.tile_extent[0], screen_pos[1] - height))
            self.skill_interface.render(screen)

            # render any active damage indicators
            if self.damage_indicator_fade > 0:
                self.damage_indicator.set_alpha(self.damage_indicator_fade)
                screen.blit(self.damage_indicator, (screen_pos[0], screen_pos[1] - height - self.damage_indicator_height))

        if self.active_skill is not None:
            self.active_skill.render(screen)

    def update_health_and_mana(self):
        self.health_bar.fill(self.missing_health_color)
        max_health = self.get_data(CharacterKeys.max_health)
        health = self.get_data(CharacterKeys.current_health)
        bar_portion = self.bar_width * (health / max_health)
        pygame.draw.rect(self.health_bar, self.health_color, (0, 0, bar_portion, self.bar_height))
        draw_text(self.health_bar,
                  str(health) + "/" + str(max_health),
                  pygame.Color("black"),
                  (0, 2, self.bar_width, self.bar_height),
                  self.stat_text)

        self.mana_bar.fill(self.missing_health_color)
        mana = self.get_data(CharacterKeys.current_mana)
        max_mana = self.get_data(CharacterKeys.max_mana)
        bar_portion = self.bar_width * (mana / max_mana)
        pygame.draw.rect(self.mana_bar, self.mana_color, (0, 0, bar_portion, self.bar_height))
        draw_text(self.mana_bar,
                  str(mana) + "/" + str(max_mana),
                  pygame.Color("white"),
                  (0, 2, self.bar_width, self.bar_height),
                  self.stat_text)

    def notify(self, event):
        if self.active_skill is None:
            skill_id = self.skill_interface.notify(event)
            if skill_id is not None and self.skills[skill_id].can_use_skill():
                self.selected_skill_id = skill_id
                self.current_map.display_skill_info(self.get_selected_skill(), True)
                return True
        return False

    def set_ally(self, is_ally):
        self.ally = is_ally
        self.accepting_input = is_ally
        self.skill_interface.set_active(False)

    def set_selected(self, selected):
        self.selected = selected
        self.skill_interface.set_active(selected)
        self.selected_skill_id = None
        if selected:
            if self.action_points > 0:
                self.current_map.display_movement(self.position, self.get_movement(), self.get_total_movement())
            return self
        return None

    def add_skill(self, skill):
        self.skills.append(skill)
        self.skill_interface.add_image_button(
            (0.05 * (len(self.skills) + 5), 0.87),
            None,
            len(self.skills) - 1,
            skill.get_data(SkillKeys.description),
            "images/icons/skill_icon.png"
        )

    def add_to_modifier(self, mod_name, amount):
        if mod_name in self.modifiers.keys():
            self.modifiers[mod_name] += amount
        else:
            self.set_modifier(mod_name, amount)

    def set_modifier(self, mod_name, amount):
        self.modifiers[mod_name] = amount

    def get_selected_skill(self):
        if self.selected_skill_id is None:
            return None
        return self.skills[self.selected_skill_id]

    def has_ai(self):
        return False

    def start_of_round_update(self):
        if not self.knocked_out:
            self.action_points = self.get_data(CharacterKeys.action_points)
            self.accepting_input = True
            self.used_skill = False
            for effect in self.status_effects:
                effect.on_start_turn()
            self.effect_cleanup()

    def end_of_round_update(self):
        self.accepting_input = False
        self.chance_image_active = False
        self.selected_skill_id = None
        if not self.knocked_out:
            for effect in self.status_effects:
                effect.on_end_turn()
        elif not self.stabilized:
            self.knockout_timer -= 1
            if self.knockout_timer <= 0:
                self.current_map.fail_scene()
        self.effect_cleanup()

    def move_order(self, path):
        if not self.accepting_input:
            return False
        # calculate the number of actions it will take
        actions = ceil(self.path_distance(path) / self.get_movement())
        return self.commit_move(path, actions)

    def path_distance(self, path):
        prev_space = self.position
        length = 0
        for space in path:
            if prev_space[0] != space[0] and prev_space[1] != space[1]:
                length += 1.414
            elif prev_space[0] != space[0] or prev_space[1] != space[1]:
                length += 1
        return length

    def commit_move(self, path, actions=-1):
        if self.action_points > 0 and len(path) > 1:
            self.path = path
            self.position = [path[-1][0], path[-1][1]]
            self.current_map.z_order_sort_entities()
            self.visual_position = path[0]
            self.accepting_input = False
            self.action_points -= actions
            return True
        self.finish_move()
        return False

    def use_action(self):
        self.current_map.clear_tinted_tiles()
        self.action_points -= 1
        self.used_skill = True
        if self.accepting_input and self.selected:
            self.set_selected(True)

    def use_bonus_action(self):
        if self.has_bonus_action:
            self.has_bonus_action = False
        else:
            self.use_action()

    def show_hit_chance(self, skill):
        # TODO: make a more accurate system for predicting hit chance
        hit_chance = skill.get_data("accuracy")
        if hit_chance is not None:
            if hit_chance > 100:
                hit_chance = 100
            elif hit_chance < 0:
                hit_chance = 0
            self.chance_image.fill((0, 0, 0))
            self.chance_image_active = True
            draw_shadowed_text(self.chance_image, str(hit_chance) + "%", pygame.Color("white"),
                               (0, 0, tilemap.tile_extent[0], tilemap.tile_extent[1]), self.font)

    def display_hit(self, to_display, color):
        self.damage_indicator_fade = 225
        self.damage_indicator_height = self.bar_height * 2
        self.damage_indicator.fill(pygame.Color("purple"))
        draw_shadowed_text(self.damage_indicator, to_display, color,
                           (0, 0, self.bar_width, self.bar_height), self.font)

    def reset_display(self):
        self.update_health_and_mana()
        self.chance_image_active = False

    def clear_hit(self):
        self.chance_image_active = False

    def use_skill(self, tile_pos):
        if self.active_skill is None and self.selected_skill_id is not None \
                and self.get_selected_skill().exec_skill(tile_pos):
            self.update_health_and_mana()
            self.active_skill = self.get_selected_skill()
            self.selected_skill_id = None
            return True
        return False

    def roll_to_hit(self, accuracy):
        evasion = randint(0, 99) + self.get_data(CharacterModifiers.evasion)
        if evasion < accuracy:
            for effect in self.status_effects:
                effect.on_self_hit()
            return True
        self.display_hit("MISS", pygame.Color("white"))
        return False

    def roll_to_crit(self, crit_chance):
        if randint(0, 99) < crit_chance:
            for effect in self.status_effects:
                effect.on_self_crit()
            return True
        return False

    def damage(self, amount, tags=None):
        if tags is None or "true" not in tags:
            amount -= self.get_data(CharacterKeys.armor)
        if amount > 0:
            health = self.get_data(CharacterKeys.current_health)
            health -= amount
            if health <= 0:
                self.knockout()
            self.data[CharacterKeys.current_health] = health
            self.update_health_and_mana()
        self.display_hit("-" + str(amount), pygame.Color("red"))

    def heal(self, amount):
        if amount > 0:
            health = self.get_data(CharacterKeys.current_health)
            health += amount
            max_health = self.get_data(CharacterKeys.max_health)
            if health > max_health:
                health = max_health
            self.data[CharacterKeys.current_health] = health
            self.update_health_and_mana()
        self.display_hit("+" + str(amount), pygame.Color("green"))

    def knockout(self):
        self.data[CharacterKeys.current_health] = 0
        self.knocked_out = True
        self.accepting_input = False
        self.selected_skill_id = None
        self.status_effects.clear()
        if not self.ally:
            self.delete = True
            self.current_map.remove_entities()

    def stabilize(self):
        self.stabilized = True

    def add_mana(self, amount):
        mana = self.get_data(CharacterKeys.current_mana)
        mana += amount
        max_mana = self.get_data(CharacterKeys.max_mana)
        if mana > max_mana:
            mana = max_mana
        if mana < 0:
            mana = 0
        self.data[CharacterKeys.current_mana] = mana

    def add_status_effect(self, effect):
        for current_effect in self.status_effects:
            if not current_effect.on_add_status_effect(effect):
                return False
        effect.on_add()
        self.status_effects.append(effect)
        if effect.visible:
            effect_rect = (0.002 + 0.01 * len(self.status_effects), 0.86, 0.02, 0.04)
            self.skill_interface.add_dynamic_description(effect_rect, effect)
        return True

    def effect_cleanup(self):
        found = True
        while found:
            found = False
            for index, effect in enumerate(self.status_effects):
                if effect.delete:
                    self.skill_interface.delete_button(self.status_effects[index].name)
                    del self.status_effects[index]
                    found = True
                    break

    def is_moving(self):
        return len(self.path) > 0


class AICharacter(Character):
    def __init__(self, position, current_map, ai_manager, entity_data):
        super().__init__(position, current_map, entity_data)
        self.ally = False
        self.accepting_input = False
        self.AI_active = False
        self.manager = ai_manager
        self.manager.add_actor(self)

        self.health_color = pygame.Color("red")
        self.update_health_and_mana()

        self.has_priority = False

    def has_ai(self):
        return True

    def set_manager(self, manager):
        self.manager = manager

    def ai_move(self):
        # AI for stupid melee enemies
        if self.action_points > 0:
            move = self.get_movement()
            all_moves = self.current_map.find_all_paths(self.position, move)
            closest_target_distance = 99999
            closest_target = None
            # find closest party member
            for c in self.current_map.character_list:
                all_moves.discard(tuple(c.position))
                if c.ally and not c.knocked_out:
                    distance = tilemap.distance_between(self.position, c.position)
                    if distance < closest_target_distance:
                        closest_target_distance = distance
                        closest_target = c

            # find the full path to the closest party member
            path = self.current_map.find_path(self.position, closest_target.position, 99)
            # trim the path down to only as far as this character can move
            prev_space = self.position
            trimmed_path = []
            length = 0
            for space in path:
                if prev_space[0] != space[0] and prev_space[1] != space[1]:
                    length += 1.414
                elif prev_space[0] != space[0] or prev_space[1] != space[1]:
                    length += 1
                if length <= move:
                    trimmed_path.append(space)

            # if the path destination is blocked, find the next closest unblocked destination
            path_destination = trimmed_path[-1]
            if path_destination not in all_moves:
                best_distance = 99999
                new_destination = None
                for pos in all_moves:
                    distance = tilemap.distance_between(path_destination, pos)
                    if distance < best_distance:
                        best_distance = distance
                        new_destination = pos
                trimmed_path = self.current_map.find_path(self.position, new_destination, 99)

            self.commit_move(trimmed_path)
        else:
            self.finish_move()

    def update(self, deltatime):
        super().update(deltatime)
        # if this AI has priority and is not currently using a skill or moving it will
        # try to use another skill. If it cannot, give priority to next AI character
        if self.AI_active and self.has_priority and self.active_skill is None and len(self.path) == 0:
            self.has_priority = self.use_skills()
            if not self.has_priority:
                self.manager.next_priority()

    def give_priority(self):
        self.has_priority = True

    def move_order(self, path):
        return False

    def use_skills(self):
        if self.action_points > 0:
            self.selected_skill_id = 0
            attack_tiles = self.skills[0].targetable_tiles()
            attack_targets = []
            for c in self.current_map.character_list:
                if c.ally and tuple(c.position) in attack_tiles:
                    attack_targets.append(c)

            if len(attack_targets) > 0 and self.get_selected_skill().exec_skill(attack_targets[0].position):
                self.active_skill = self.get_selected_skill()
                self.current_map.move_camera_to_path(self.visual_position)
                return True
        return False

    def finish_turn(self):
        self.manager.actor_finished()

    def finish_move(self):
        self.path.clear()

    def use_skill(self, tile_pos):
        return False

    def end_of_round_update(self):
        self.AI_active = True
        for effect in self.status_effects:
            effect.on_start_turn()
        self.effect_cleanup()

    def start_of_round_update(self):
        self.AI_active = False
        self.action_points = 2
        self.used_skill = False
        for effect in self.status_effects:
            effect.on_end_turn()
        self.effect_cleanup()
