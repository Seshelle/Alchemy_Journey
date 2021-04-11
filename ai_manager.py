class AIManager:
    def __init__(self, current_map):
        self.current_map = current_map
        self.actors = []
        self.current_actor = 0

    def add_actor(self, new_actor):
        new_actor.set_manager(self)
        self.actors.append(new_actor)

    def next_priority(self):
        if self.current_actor >= 0:
            self.current_actor += 1
            if self.current_actor >= len(self.actors):
                self.end_ai_turn()
            else:
                self.actors[self.current_actor].give_priority()

    def end_ai_turn(self):
        self.current_actor = -1
        self.current_map.start_turn()

    def start_ai_turn(self):
        self.current_actor = 0
        for actor in self.actors:
            actor.ai_move()
        self.actors[0].give_priority()
