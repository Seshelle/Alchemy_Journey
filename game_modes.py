import user_interface
import tilemap
import level_editor
import dialogue


class GameMode:
    def __init__(self, screen):
        self.new_mode = None
        self.screen = screen

    def update(self, deltatime):
        pass

    def notify(self, event):
        pass


class MainMenu(GameMode):
    def __init__(self, screen):
        super().__init__(screen)
        self.interface = user_interface.UserInterface()
        self.interface.add_button((0.5, 0.35, 0.2, 0.1), "Map", "map")
        self.interface.add_button((0.5, 0.5, 0.2, 0.1), "Editor", "edit")
        self.interface.add_button((0.5, 0.65, 0.2, 0.1), "Quit", "quit")

    def update(self, deltatime):
        self.screen.fill((0, 0, 0))
        self.interface.render(self.screen)
        return None

    def notify(self, event):
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "map":
                self.new_mode = MapScene(self.screen, "data/test_map_scene.json")
            if button_pressed == "edit":
                self.new_mode = Editor(self.screen)
            if button_pressed == "quit":
                pass


class Editor(GameMode):
    def __init__(self, screen):
        super().__init__(screen)
        self.interface = user_interface.UserInterface()
        self.interface.add_button((0.9, 0.05, 0.1, 0.05), "Menu", "quit")
        self.current_map = level_editor.LevelEditor("data/test_map_scene.json")

    def update(self, deltatime):
        self.current_map.update(deltatime, self.screen)
        self.interface.render(self.screen)

    def notify(self, event):
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "quit":
                self.new_mode = MainMenu(self.screen)
        else:
            self.current_map.notify(event)


class MapScene(GameMode):
    def __init__(self, screen, filename):
        super().__init__(screen)

        self.interface = user_interface.UserInterface()
        self.interface.add_button((0.9, 0.05, 0.1, 0.05), "Menu", "quit")

        self.current_map = tilemap.TileMap(filename)

    def update(self, deltatime):
        self.current_map.update(deltatime, self.screen)
        self.interface.render(self.screen)

    def notify(self, event):
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "quit":
                self.new_mode = MainMenu(self.screen)
        else:
            self.current_map.notify(event)


class DialogueScene(GameMode):
    def __init__(self, dialogue_file, screen):
        super().__init__(screen)
        self.dialogue = dialogue.Dialogue(dialogue_file)
        self.screen = screen

    def update(self, deltatime):
        self.dialogue.update(deltatime)
        self.dialogue.render(self.screen)

    def notify(self, event):
        self.dialogue.notify(event)
