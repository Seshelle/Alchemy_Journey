from random import randint
import entity
from status_effects import EffectKeys
from status_effects import effect_list
import tilemap


class SkillKeys:
    description = "desc"
    name = "name"
    code = "code"
    range = "range"
    accuracy = "accuracy"
    area = "area"
    min_damage = "min damage"
    max_damage = "max damage"
    crit_chance = "crit chance"
    on_hit = "on hit effect"
    on_miss = "on miss effect"


skill_list = {}


def skill(f):
    skill_list[f.__name__] = f


class Skill:
    def __init__(self, skill_data, user):
        self.data = skill_data
        self.user = user
        self.current_map = self.user.current_map

    def get_data(self, key):
        if key in self.data.keys():
            return self.data[key]
        else:
            return None

    def exec_skill(self, tile_pos):
        if self.user.has_action:
            self.attack_targets(tile_pos)
            self.user.use_action()
            return True
        return False

    def display_targets(self, tile_pos):
        if self.get_data(SkillKeys.area) > 0:
            if not self.current_map.in_bounds(tile_pos, True) or \
                    not self.current_map.line_of_sight(self.user.position, tile_pos, self.get_data(SkillKeys.range)):
                return set()
            attacked_tiles = self.current_map.find_all_paths(tile_pos, self.get_data(SkillKeys.area), True)
            return attacked_tiles
        else:
            potential_targets = set()
            for e in self.current_map.character_list:
                if not e.ally and self.current_map.line_of_sight(self.user.position, e.position,
                                                         self.get_data(SkillKeys.range)):
                    potential_targets.add((e.position[0], e.position[1]))
                    e.display_hit(self)
            return potential_targets

    def display_range(self):
        tiles_in_range = self.current_map.find_all_paths(self.user.position, self.get_data(SkillKeys.range), True, True)
        return tiles_in_range

    def target(self, tile_pos):
        if not self.current_map.in_bounds(tile_pos, True) or \
                not self.current_map.line_of_sight(self.user.position, tile_pos, self.get_data(SkillKeys.range)):
            return []
        attacked_tiles = self.current_map.find_all_paths(tile_pos, self.get_data(SkillKeys.area), True)
        targets = self.current_map.get_characters_in_set(attacked_tiles)
        return targets

    def attack_targets(self, tile_pos):
        targets = self.target(tile_pos)
        for target in targets:
            if target.team != self.user.team:
                self.attack_character(target)

    def attack_character(self, target):
        if target.roll_to_hit(self.get_data(SkillKeys.accuracy)):
            effect = self.apply_effect(SkillKeys.on_hit, target)
            if effect is not None:
                effect.on_hit(self.user)
            damage = randint(self.get_data(SkillKeys.min_damage), self.get_data(SkillKeys.max_damage))
            if randint(0, 99) < self.get_data(SkillKeys.crit_chance):
                damage *= 2
            target.damage(damage)
        else:
            effect = self.apply_effect(SkillKeys.on_miss, target)
            if effect is not None:
                effect.on_miss(self.user)

    def apply_effect(self, apply_type, target):
        effect_data = self.get_data(apply_type)
        if effect_data is not None:
            effect = effect_list[effect_data[EffectKeys.code]](self.user, effect_data)
            if target.add_status_effect(effect):
                return effect
        return None


@skill
class Default(Skill):
    pass


@skill
class DelayedTrigger(Skill):
    def exec_skill(self, tile_pos):
        # place a delayed explosion entity at tile position
        if self.user.has_action:
            current_map = self.user.current_map
            if current_map.in_bounds(tile_pos, True):
                entity_data = {"appearance": "images/tile040.png", "height": 1.5}
                current_map.add_entity(entity.DelayedSkill(
                    tile_pos,
                    entity_data,
                    skill_list[self.data["triggered"]](self.data, self.user)))
                self.user.use_action()
                return True
        return False


@skill
class DefaultTrigger(Skill):
    def exec_skill(self, tile_pos):
        targets = self.target(tile_pos)
        for target in targets:
            self.attack_character(target)
        return True
