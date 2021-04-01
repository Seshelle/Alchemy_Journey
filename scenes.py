import dialogue
import game_modes


class Scene:
    def __init__(self, current_map, map_data):
        self.current_map = current_map
        self.block_input = False

    def get_allow_input(self):
        return not self.block_input

    def detect_victory(self):
        # changes what the map considers victory
        # return None to keep default map behavior
        return None

    def handle_victory(self):
        # called when current_map has detected a victory
        # return None to keep default map behavior
        return None

    def detect_failure(self):
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


# this class handles scenes that start with dialogue and need it displayed
class DialogueScene(Scene):
    def __init__(self, current_map, map_data):
        super().__init__(current_map, map_data)
        self.dialogue = dialogue.Dialogue(map_data["dialogue"])
        self.set_dialogue_active(True)

    def update(self, deltatime):
        self.dialogue.update(deltatime)
        if self.block_input and not self.dialogue.active:
            self.set_dialogue_active(False)

        if self.dialogue.change_scene is not None:
            self.current_map.change_mode(game_modes.MapScene(self.dialogue.change_scene))

        if self.dialogue.camera_set is not None:
            camera_pos = self.dialogue.camera_set
            self.dialogue.camera_set = None
            self.current_map.move_camera_to_path(camera_pos)

        if self.dialogue.character_move is not None:
            move = self.dialogue.character_move
            self.dialogue.character_move = None
            for c in self.current_map.character_list:
                if move["character"] == c.name:
                    c.path = move["path"]
                    c.position = move["path"][-1]

        if self.dialogue.repeat:
            self.dialogue.repeat = False
            self.dialogue.next_line()

    def set_dialogue_active(self, active):
        self.block_input = active
        self.current_map.interface.set_button_active("end turn", not active)
        for c in self.current_map.character_list:
            c.show_ui = not active

    def notify(self, event):
        if self.dialogue.active:
            self.dialogue.notify(event)
        return self.block_input

    def render(self, screen):
        self.dialogue.render(screen)


@scene
class Empty(Scene):
    pass


@scene
class Cutscene(DialogueScene):
    pass


@scene
class Tutorial(DialogueScene):
    def handle_victory(self):
        # go to next dialogue scene
        self.current_map.change_mode(game_modes.MapScene("data/scenes/after_tutorial_scene.json"))
        return True

    def handle_failure(self):
        # return to main menu
        self.current_map.change_mode(game_modes.MainMenu())
        return True
