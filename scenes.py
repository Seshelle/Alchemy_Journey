import pygame
import dialogue


class Scene:
    def __init__(self, current_map):
        self.current_map = current_map
        self.block_input = False

    def get_allow_input(self):
        return not self.block_input

    def detect_victory(self):
        return None

    def handle_failure(self):
        return None

    def update(self, deltatime):
        pass

    def notify(self, event):
        return False

    def render(self, screen):
        pass

    def second_render(self, screen):
        pass


scenes = {}


def scene(f):
    scenes[f.__name__] = f


@scene
class Empty(Scene):
    pass


@scene
class Tutorial(Scene):
    def __init__(self, current_map):
        super().__init__(current_map)
        self.block_input = True
        self.dialogue = dialogue.Dialogue("data/tutorial_dialogue.json")

    def update(self, deltatime):
        self.block_input = self.dialogue.active
        if self.dialogue.camera_set is not None:
            self.current_map.move_camera_to_path(self.dialogue.camera_set)
            self.dialogue.camera_set = None

    def notify(self, event):
        self.dialogue.notify(event)
        return self.block_input

    def render(self, screen):
        self.dialogue.render(screen)
