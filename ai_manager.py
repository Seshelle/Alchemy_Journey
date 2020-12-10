class AIManager:
    def __init__(self, current_map):
        self.current_map = current_map
        self.actors = []
        self.current_actor = 0
        self.finished_actors = 0

    def add_actor(self, new_actor):
        new_actor.set_manager(self)
        self.actors.append(new_actor)

    def next_priority(self):
        self.current_actor += 1
        if self.current_actor >= len(self.actors):
            self.current_actor = 0
            self.end_ai_turn()
        else:
            self.actors[self.current_actor].give_priority()

    def actor_finished(self):
        self.finished_actors += 1
        if self.finished_actors >= len(self.actors):
            self.end_ai_turn()

    def end_ai_turn(self):
        self.current_actor = 0
        self.finished_actors = 0
        self.current_map.start_turn()

    def start_ai_turn(self):
        for actor in self.actors:
            actor.ai_move()
        self.actors[0].give_priority()


"""
AI Ideas:
create a set of tiles the AI character can move to
do some basic pruning of those tiles before examining them in depth
run a cost function on each of those tiles

calculate the benefit of taking actions at each tile:
    average damage dealt to enemy team
        - give a damage expectation to their skills to determine their effectiveness
        - if an attack is a high percentage of the opposing team, give large bonus
    resource cost
        - give penalties to costly skills when they are not being used effectively
    denying the enemy good positions, using basic heuristic to determine those
        - lay traps that cover good squares the enemy could occupy next turn
        - good squares threaten allies and are good defensively

calculate defensive advantages:
    full cover is best when no attack skills can be used
        - also try to get to a location where a skill can be used next turn (less priority)
    avoid squares with traps in them
        - compare percentage damage dealt to each team for ruthless AI's
    calculate expected damage allied team will take
        - avoid letting all opposing party members use their attacks
        - if an enemy attack cannot be prevented, ignore it
        - if close to death, avoid being in line of fire (or kamikaze)
    don't worry about bunching up, exploding enemies is fun!
"""
