from random import randint
import entity
from status_effects import EffectKeys
from status_effects import effect_list
import pygame
import tilemap


class SkillKeys:
    description = "desc"
    name = "name"
    code = "code"
    range = "range"
    accuracy = "accuracy"
    area = "area"
    damage = "damage"
    hits = "hits"
    min_heal = "min heal"
    max_heal = "max heal"
    crit_chance = "crit chance"
    mana_cost = "mana cost"
    tags = "tags"

    on_hit = "on hit effect"
    on_crit = "on crit effect"
    on_miss = "on miss effect"
    give_self = "give self effect"


class SkillTags:
    aimed = "aimed"
    indirect = "indirect"
    buff = "buff"
    friendly_fire = "friendly fire"
    bonus_action = "bonus action"
    free_action = "free action"
    no_target = "no target"


skill_list = {}


def skill(f):
    skill_list[f.__name__] = f


class Skill:
    def __init__(self, skill_data, user):
        self.data = skill_data
        self.user = user
        self.current_map = self.user.current_map

        self.mana_cost = 0
        if self.has_attribute(SkillKeys.mana_cost):
            self.mana_cost = skill_data[SkillKeys.mana_cost]
        self.range = 1.5
        if self.has_attribute(SkillKeys.range):
            self.range = skill_data[SkillKeys.range]
        self.area = 0
        if self.has_attribute(SkillKeys.area):
            self.area = skill_data[SkillKeys.area]
        self.crit_chance = 5
        if self.has_attribute(SkillKeys.crit_chance):
            self.crit_chance = skill_data[SkillKeys.crit_chance]
        self.accuracy = None
        if self.has_attribute(SkillKeys.accuracy):
            self.accuracy = skill_data[SkillKeys.accuracy]

        self.tags = skill_data[SkillKeys.tags]
        self.is_buff = self.has_tag(SkillTags.buff)
        self.friendly_fire = self.has_tag(SkillTags.friendly_fire)

        self.cached_valid_tiles = set()
        self.cached_position = [-1, -1]

    def get_data(self, key):
        if key in self.data.keys():
            return self.data[key]
        return None

    def has_tag(self, tag):
        return tag in self.tags

    def has_attribute(self, key):
        return key in self.data.keys()

    def exec_skill(self, tile_pos):
        if self.can_use_skill() and self.is_valid_tile(tile_pos):
            self.attack_targets(tile_pos)
            if self.has_tag(SkillTags.bonus_action):
                self.user.use_bonus_action()
            elif not self.has_tag(SkillTags.free_action):
                self.user.use_action()
            self.user.add_mana(-self.mana_cost)
            self.apply_effect(SkillKeys.give_self, self)
            return True
        return False

    def can_use_skill(self):
        if self.user.mana >= self.mana_cost:
            if self.has_tag(SkillTags.free_action):
                return True
            if self.has_tag(SkillTags.bonus_action):
                return self.user.has_bonus_action or self.user.has_action
            return self.user.has_action
        return False

    def display_targets(self, tile_pos):
        if self.can_use_skill():
            if self.has_tag(SkillTags.aimed):
                if self.is_valid_tile(tile_pos):
                    return self.get_area(tile_pos)
            else:
                potential_targets = set()
                for e in self.current_map.character_list:
                    if e.ally == self.is_buff and tuple(e.position) in self.targetable_tiles():
                        potential_targets.add((e.position[0], e.position[1]))
                        e.display_hit(self)
                return potential_targets
        return set()

    def get_area(self, tile_pos):
        return self.current_map.find_all_paths(tile_pos, self.area, True)

    def targetable_tiles(self, display=False):
        if display or self.user.position != self.cached_position:
            valid_tiles = self.current_map.find_all_paths(
                    self.user.position,
                    self.range,
                    True,
                    display,
                    self.has_tag(SkillTags.indirect)
                )
            if display:
                return valid_tiles
            else:
                self.cached_position = self.user.position
                self.cached_valid_tiles = valid_tiles
        return self.cached_valid_tiles

    def is_valid_tile(self, tile_pos):
        if self.has_tag(SkillTags.no_target):
            return True
        return tuple(tile_pos) in self.targetable_tiles()

    def attack_targets(self, tile_pos):
        targets = self.target(tile_pos)
        hits = self.get_data(SkillKeys.hits)
        if hits is None:
            hits = 1
        for target in targets:
            if not self.user.ally or self.is_buff == target.ally or self.friendly_fire:
                for hit in range(hits):
                    self.attack_character(target)

    def target(self, tile_pos):
        if not self.current_map.in_bounds(tile_pos, True):
            return []
        targets = self.current_map.get_characters_in_set(self.get_area(tile_pos))
        return targets

    def attack_character(self, target):
        if target.roll_to_hit(self.accuracy):
            self.apply_effect(SkillKeys.on_hit, target)
            damage_range = self.get_data(SkillKeys.damage)
            damage = randint(damage_range[0], damage_range[1])
            if randint(0, 99) < self.crit_chance:
                damage = round(damage * 1.5)
                self.apply_effect(SkillKeys.on_crit, target)
            target.damage(damage, self.tags)
        else:
            self.apply_effect(SkillKeys.on_miss, target)

    def apply_effect(self, apply_type, target):
        effect_data = self.get_data(apply_type)
        if effect_data is not None:
            effect = effect_list[effect_data[EffectKeys.code]](target, effect_data)
            target.add_status_effect(effect)


class ChainedSkill(Skill):
    def __init__(self, skill_data, user):
        super().__init__(skill_data, user)
        self.second_target = None

    def exec_skill(self, tile_pos):
        if self.can_use_skill() and self.is_valid_tile(tile_pos):
            screen = pygame.display.get_surface()
            get_target = True
            while get_target:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return False
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.second_target = tilemap.screen_to_path(pygame.mouse.get_pos())
                        get_target = False
                        break
                self.current_map.update(1)
                self.current_map.render(screen)
                pygame.display.flip()

            return super().exec_skill(tile_pos)
        return False


@skill
class Default(Skill):
    pass


@skill
class DelayedTrigger(Skill):
    def exec_skill(self, tile_pos):
        # place a delayed explosion entity at tile position
        if self.user.has_action and self.is_valid_tile(tile_pos):
            current_map = self.user.current_map
            if current_map.in_bounds(tile_pos, True):
                current_map.add_entity(entity.DelayedSkill(
                    tile_pos,
                    self.data,
                    skill_list[self.data["triggered"]](self.data, self.user)))
                self.user.use_action()
                return True
        return False


@skill
class DefaultTrigger(Skill):
    def __init__(self, skill_data, user):
        super().__init__(skill_data, user)
        self.data = skill_data["trigger attributes"]
        self.area = 0
        if SkillKeys.area in self.data.keys():
            self.area = self.data[SkillKeys.area]
        self.crit_chance = 0
        if SkillKeys.crit_chance in self.data.keys():
            self.crit_chance = self.data[SkillKeys.crit_chance]
        self.accuracy = None
        if SkillKeys.accuracy in self.data.keys():
            self.accuracy = self.data[SkillKeys.accuracy]

        self.tags = self.data[SkillKeys.tags]

    def exec_skill(self, tile_pos):
        targets = self.target(tile_pos)
        for target in targets:
            self.attack_character(target)


@skill
class Healing(Skill):
    def attack_character(self, target):
        heal = randint(self.get_data(SkillKeys.min_heal), self.get_data(SkillKeys.max_heal))
        target.heal(heal)


@skill
class MoveSkill(Skill):
    def attack_targets(self, tile_pos):
        self.user.position = tile_pos
        self.user.path = [self.user.position, tile_pos]

    def targetable_tiles(self, display=False):
        tiles_in_range = self.current_map.find_all_paths(self.user.position, self.range, False, display)
        return tiles_in_range


@skill
class Sweep(Skill):
    def get_area(self, tile_pos):
        area = set()
        area.add(tuple(tile_pos))
        # return the clicked position and the two closest adjacent tiles
        difference = (self.user.position[0] - tile_pos[0], self.user.position[1] - tile_pos[1])
        if difference[0] != 0 and difference[1] != 0:
            area.add((tile_pos[0] + difference[0], tile_pos[1]))
            area.add((tile_pos[0], tile_pos[1] + difference[1]))
        elif difference[0] != 0:
            area.add((tile_pos[0], tile_pos[1] + 1))
            area.add((tile_pos[0], tile_pos[1] - 1))
        else:
            area.add((tile_pos[0] + 1, tile_pos[1]))
            area.add((tile_pos[0] - 1, tile_pos[1]))
        return area

    def is_valid_tile(self, tile_pos):
        return self.user.position != tile_pos and tuple(tile_pos) in self.targetable_tiles()


@skill
class Respite(Skill):
    def display_targets(self, tile_pos):
        targets = set()
        for c in self.current_map.character_list:
            if c.ally == self.user.ally:
                targets.add(tuple(c.position))
        return targets

    def target(self, tile_pos):
        targets = []
        for c in self.current_map.character_list:
            if c.ally == self.user.ally:
                targets.append(c)
        return targets

    def attack_character(self, target):
        target.heal(1)


@skill
class Throw(ChainedSkill):
    def attack_targets(self, tile_pos):
        throw_target = self.current_map.get_characters_in_set(self.get_area(tile_pos))[0]
        if self.user.ally == throw_target.ally or throw_target.roll_to_hit(self.accuracy):
            throw_target.position = self.second_target
            throw_target.visual_position = self.second_target

            damage_range = self.get_data(SkillKeys.damage)

            damage = randint(damage_range[0], damage_range[1])
            if randint(0, 99) < self.crit_chance:
                damage = round(damage * 1.5)
            throw_target.damage(damage, self.tags)

            throw_target = self.current_map.get_characters_in_set(self.get_area(self.second_target))
            if len(throw_target) > 0:
                throw_target = throw_target[0]
                damage = randint(damage_range[0], damage_range[1])
                if randint(0, 99) < self.crit_chance:
                    damage = round(damage * 1.5)
                throw_target.damage(damage, self.tags)

