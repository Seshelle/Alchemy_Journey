import character


class EffectKeys:
    code = "code"
    duration = "duration"


class StatusEffect:
    def __init__(self, host, effect_data):
        self.host = host
        self.data = effect_data
        self.delete = False
        self.visible = True
        self.stacks = 1
        self.age = 0
        self.on_create(self.host)

    def mark_for_deletion(self):
        self.delete = True
        self.visible = False

    def on_create(self, host):
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
        if self.age >= self.data["duration"]:
            self.mark_for_deletion()

    def on_end_turn(self):
        # specifically when the character's team ends their round
        self.age += 1
        if self.age >= self.data["duration"]:
            self.mark_for_deletion()

    def on_check_statistic(self, stat):
        return 0

    def on_add_status_effect(self):
        return True


effect_list = {}


def effect(f):
    effect_list[f.__name__] = f


@effect
class Immobilize(StatusEffect):
    def on_check_statistic(self, stat):
        if not self.delete and stat == character.CharacterKeys.movement:
            return -9999
        else:
            return 0
