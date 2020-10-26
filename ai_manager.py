import pygame
import character


class AIManager:
    def __init__(self, current_map):
        self.current_map = current_map
        self.actors = []
        self.current_actor = 0

    def add_actor(self, new_actor):
        new_actor.set_manager(self)
        self.actors.append(new_actor)

    def next_actor(self, actor):
        self.current_actor += 1
        self.start_ai_turn()

    def end_ai_turn(self):
        self.current_actor = 0
        self.current_map.start_turn()

    def start_ai_turn(self):
        if self.current_actor < len(self.actors):
            self.actors[self.current_actor].ai_move()
        else:
            self.end_ai_turn()
