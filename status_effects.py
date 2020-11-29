import random


class EffectKeys:
    code = "code"
    name = "name"
    tags = "tags"
    description = "description"
    icon = "icon"
    duration = "duration"
    visible = "visible"
    stacks = "stacks"
    amount = "amount"

    affected_stat = "stat"
    stat_change = "change"


class StatusEffect:
    def __init__(self, host, effect_data):
        self.host = host
        self.data = effect_data
        self.delete = False

        self.visible = True
        if EffectKeys.visible in effect_data.keys():
            self.visible = effect_data[EffectKeys.visible]

        self.name = "NO NAME"
        if EffectKeys.name in effect_data.keys():
            self.name = effect_data[EffectKeys.name]

        self.tags = []
        if EffectKeys.tags in effect_data.keys():
            self.tags = effect_data[EffectKeys.tags]

        self.can_stack = False
        if EffectKeys.stacks in effect_data.keys():
            self.can_stack = effect_data[EffectKeys.stacks]

        self.stacks = 1
        if EffectKeys.amount in effect_data.keys():
            self.stacks = effect_data[EffectKeys.amount]

        self.description = "NO DESCRIPTION"
        if EffectKeys.description in effect_data.keys():
            self.description = effect_data[EffectKeys.description]

        if EffectKeys.icon in effect_data.keys():
            self.icon = effect_data[EffectKeys.icon]
        else:
            self.icon = "images/icons/status_effect.png"

        self.duration = -1
        if EffectKeys.duration in effect_data.keys():
            self.duration = self.data[EffectKeys.duration]
        self.age = 0

    def info_string(self):
        return "Stacks: " + self.stacks + "\nDuration: " + (self.duration - self.age)

    def mark_for_deletion(self):
        if not self.delete:
            self.on_remove()
            self.delete = True
            self.visible = False

    def on_add(self):
        pass

    def on_remove(self):
        pass

    def add_stacks(self, amount):
        self.stacks += amount
        self.age = 0
        if self.stacks < 1:
            self.mark_for_deletion()

    def on_hit(self, user):
        pass

    def on_miss(self, user):
        pass

    def on_self_hit(self):
        pass

    def on_self_crit(self):
        pass

    def on_start_turn(self):
        # if an effect has zero duration, it will end before the host's turn begins
        if self.duration >= 0:
            if self.age >= self.duration:
                self.mark_for_deletion()

    def on_end_turn(self):
        # specifically when the character's team ends their round
        if self.duration >= 0:
            self.age += 1
            if self.age >= self.duration:
                self.mark_for_deletion()

    def on_add_status_effect(self, status_effect):
        # returns true if this effect should be appended to the character's
        # status effect list. Returns false for alternate handling
        if not self.delete and status_effect.name == self.name:
            # do not add non-unique status effect to effect list
            if self.can_stack:
                # add more stacks
                self.add_stacks(status_effect.stacks)
            # refresh the effect's duration
            self.age = 0
            if 0 <= self.duration < status_effect.duration:
                # if the new duration is longer, replace it with the longer duration
                self.duration = status_effect.duration
            return False
        return True


class AddModifier(StatusEffect):
    def __init__(self, host, effect_data):
        super().__init__(host, effect_data)
        self.stat_change = effect_data[EffectKeys.stat_change]
        self.affected_stat = effect_data[EffectKeys.affected_stat]

    def on_add(self):
        self.host.add_to_modifier(self.affected_stat, self.stat_change * self.stacks)

    def on_remove(self):
        self.host.add_to_modifier(self.affected_stat, -self.stat_change * self.stacks)

    def add_stacks(self, amount):
        self.host.add_to_modifier(self.affected_stat, self.stat_change * amount)


effect_list = {}


def effect(f):
    effect_list[f.__name__] = f


@effect
class Stun(StatusEffect):
    def on_start_turn(self):
        super().on_start_turn()
        self.host.has_action = False
        self.host.has_move = False


@effect
class Immobilize(AddModifier):
    def __init__(self, host, effect_data):
        super().__init__(host, effect_data)
        self.name = "Immobilize"
        self.description = "Immobilized: Cannot move"

    def on_start_turn(self):
        super().on_start_turn()
        self.host.has_move = False


@effect
class Modify(AddModifier):
    pass


@effect
class StackingPoison(StatusEffect):
    def on_end_turn(self):
        self.host.damage(self.stacks, ["effect", "poison"])
        self.add_stacks(-1)


@effect
class RandomMinorDebuff(StatusEffect):
    def __init__(self, host, effect_data):
        super().__init__(host, effect_data)
        random_effects = [
            ("Slow", "Slowed: Movement is reduced by 1 per stack.", "movement", -1, 1),
            ("Dazzled", "Dazzled: Accuracy is reduced by 5 per stack.", "accuracy", -5, 3),
            ("Weak", "Weakened: Damage is reduced by 1 per stack.", "damage", -1, 1),
            ("Exposed", "Exposed: Armor is reduced by 1 per stack", "armor", -1, 1)
        ]
        choice = random_effects[random.randint(0, len(random_effects) - 1)]
        self.name = choice[0]
        self.description = choice[1]
        self.affected_stat = choice[2]
        self.stat_change = choice[3]
        self.stacks = choice[4]

    def on_add(self):
        self.host.add_to_modifier(self.affected_stat, self.stat_change * self.stacks)

    def on_remove(self):
        self.host.add_to_modifier(self.affected_stat, -self.stat_change * self.stacks)

    def add_stacks(self, amount):
        self.host.add_to_modifier(self.affected_stat, self.stat_change * amount)
