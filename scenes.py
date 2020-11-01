class Scene:
    def __init__(self, current_map):
        self.current_map = current_map

    def update(self, deltatime):
        pass

    def notify(self, event):
        pass

    def render(self, screen):
        pass

    def second_render(self, screen):
        pass


scenes = {}


def scene(f):
    scenes[f.__name__] = f


@scene
class Tutorial(Scene):
    def __init__(self, current_map):
        super().__init__(current_map)
