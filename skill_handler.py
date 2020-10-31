from random import randint
import entity


class Skill:
    def __init__(self, skill_data, user):
        self.data = skill_data
        self.user = user

    def get_data(self, key):
        if key in self.data.keys():
            return self.data[key]
        else:
            return None

    def display(self, tile_pos):
        # returns a set of tiles to display when skill is selected
        return exec_skill_func("display_" + self.data["display"], self, tile_pos)

    def exec_skill(self, tile_pos):
        return exec_skill_func("skill_" + self.data["effect"], self, tile_pos)

    def exec_secondary_skill(self, tile_pos, name):
        return exec_skill_func("skill_" + self.data[name], self, tile_pos)


class StatusEffect:
    def __init__(self):
        pass

    def apply_effect(self, attack_hit):
        pass

    def start_turn_effect(self):
        pass

    def end_turn_effect(self):
        pass


skill_functions = {}


def skill_func(f):
    skill_functions[f.__name__] = f


def exec_skill_func(key, skill_used, target):
    if key in skill_functions.keys():
        return skill_functions[key](skill_used, target)
    else:
        print("Key not found: " + key)
        return False


""" ---------- DISPLAY FUNCTIONS ---------- """
# display functions return a set of tiles to display when choosing the target of a skill


@skill_func
def display_default(skill_used, tile_pos):
    tile_map = skill_used.user.current_map

    if skill_used.get_data("area") > 0:
        if not tile_map.in_bounds(tile_pos, True) or \
                not tile_map.line_of_sight(skill_used.user.position, tile_pos, skill_used.get_data("range")):
            return set()
        attacked_tiles = tile_map.make_radius(tile_pos, skill_used.get_data("area"), True)
        return attacked_tiles
    else:
        potential_targets = set()
        for e in tile_map.character_list:
            if not e.ally and tile_map.line_of_sight(skill_used.user.position, e.position,
                                                        skill_used.get_data("range")):
                potential_targets.add((e.position[0], e.position[1]))
                e.display_hit(skill_used)
        return potential_targets


""" ---------- TARGETING FUNCTIONS ---------- """
# targeting functions return a list of characters hit by the skill


@skill_func
def target_default(skill_used, tile_pos):
    tile_map = skill_used.user.current_map
    if not tile_map.in_bounds(tile_pos, True) or \
            not tile_map.line_of_sight(skill_used.user.position, tile_pos, skill_used.get_data("range")):
        return []
    attacked_tiles = tile_map.make_radius(tile_pos, skill_used.get_data("area"), True)
    targets = tile_map.get_characters_in_set(attacked_tiles)
    return targets


""" ---------- SKILL FUNCTIONS ---------- """
# skill functions handle the execution of a skill


@skill_func
def skill_default(skill_used, tile_pos):
    user = skill_used.user
    # check if user has action to use
    if user.has_action:
        # get targets that can be attacked
        targets = exec_skill_func("target_" + skill_used.get_data("targeting"), skill_used, tile_pos)
        for target in targets:
            if target.team != user.team:
                # roll to hit
                if randint(0, 99) < skill_used.get_data("accuracy"):
                    damage = randint(skill_used.get_data("min damage"), skill_used.get_data("max damage"))
                    if randint(0, 99) < skill_used.get_data("crit chance"):
                        damage *= 2
                    target.damage(damage)
        # end the character's turn
        user.use_action()
        return True
    return False


@skill_func
def skill_place_delayed_explosion(skill_used, tile_pos):
    # place a delayed explosion entity at tile position
    current_map = skill_used.user.current_map
    if current_map.in_bounds(tile_pos, True):
        entity_data = {"appearance": "images/tile040.png", "height": 0}
        current_map.add_entity(entity.DelayedSkill(tile_pos, entity_data, skill_used))
        skill_used.user.use_action()
        return True
    return False


@skill_func
def skill_delayed_explosion(skill_used, tile_pos):
    # get targets that can be attacked
    targets = exec_skill_func("target_" + skill_used.get_data("targeting"), skill_used, tile_pos)
    for target in targets:
        # roll to hit
        if randint(0, 99) < skill_used.get_data("accuracy"):
            damage = randint(skill_used.get_data("min damage"), skill_used.get_data("max damage"))
            if randint(0, 99) < skill_used.get_data("crit chance"):
                damage *= 2
            target.damage(damage)
    return True
