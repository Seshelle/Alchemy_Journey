from random import randint


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


@skill_func
def display_default(skill_used, tile_pos):
    attacked_tiles = skill_used.user.current_map.make_radius(tile_pos, skill_used.get_data("area"), True)
    if skill_used.get_data("area") > 0:
        return attacked_tiles
    else:
        potential_targets = set()
        for c in skill_used.user.current_map.character_list:
            if (c.position[0], c.position[1]) in attacked_tiles:
                potential_targets.add((c.position[0], c.position[1]))
        return potential_targets


""" ---------- TARGETING FUNCTIONS ---------- """


@skill_func
def target_default(skill_used, tile_pos):
    tile_map = skill_used.user.current_map
    attacked_tiles = tile_map.make_radius(tile_pos, skill_used.get_data("area"), True)
    targets = tile_map.get_characters_in_set(attacked_tiles)
    return targets


""" ---------- SKILL FUNCTIONS ---------- """


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
                hit_chance = skill_used.get_data("accuracy")
                if randint(0, 99) < hit_chance:
                    damage = randint(skill_used.get_data("min damage"), skill_used.get_data("max damage"))
                    target.damage(damage)
        # end the character's turn
        user.use_action()
        return True
    return False
