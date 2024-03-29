import user_interface
import tilemap
import level_editor
import dialogue
import strategy_map
import pygame


class GameMode:
    def __init__(self):
        self.new_mode = None
        self.screen = pygame.display.get_surface()
        self.paused = False
        self.pause_menu = user_interface.UserInterface(False)
        self.pause_menu.add_image_button((0.45, 0.5, 0.1, 0.05), "Menu", "quit")

    def update(self, deltatime):
        self.pause_menu.render(self.screen)

    def notify(self, event):
        button_pressed = self.pause_menu.notify(event)
        if button_pressed is not None:
            if button_pressed == "quit":
                self.new_mode = MainMenu()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_menu.set_active(self.paused)


class MainMenu(GameMode):
    def __init__(self):
        super().__init__()
        self.interface = user_interface.UserInterface()
        self.interface.add_image_button((0.4, 0.2, 0.2, 0.1), "Hub", "hub")
        self.interface.add_image_button((0.4, 0.35, 0.2, 0.1), "Tutorial", "test")
        self.interface.add_image_button((0.4, 0.5, 0.2, 0.1), "Editor", "edit")
        self.interface.add_image_button((0.4, 0.65, 0.2, 0.1), "Quit", "quit")

    def update(self, deltatime):
        self.screen.fill((0, 0, 0))
        self.interface.render(self.screen)
        return None

    def notify(self, event):
        button_pressed = self.interface.notify(event)
        if button_pressed is not None:
            if button_pressed == "expedition":
                self.new_mode = ExpeditionScene()
            elif button_pressed == "test":
                self.new_mode = MapScene("data/scenes/test_map_scene.json")
            elif button_pressed == "edit":
                self.new_mode = Editor()
            elif button_pressed == "hub":
                self.new_mode = HubScene()
            elif button_pressed == "quit":
                pass

    def toggle_pause(self):
        pass


class BasicScene(GameMode):
    def __init__(self):
        super().__init__()
        self.current_map = None

    def update(self, deltatime):
        super().update(deltatime)
        if not self.paused:
            self.current_map.update(deltatime)
            self.current_map.render(self.screen)
            if self.current_map.change_scene:
                self.new_mode = self.current_map.next_scene

    def notify(self, event):
        super().notify(event)
        if not self.paused:
            self.current_map.notify(event)


class Editor(BasicScene):
    def __init__(self):
        super().__init__()
        self.current_map = level_editor.LevelEditor("data/scenes/blank_scene.json")


class MapScene(BasicScene):
    def __init__(self, filename):
        super().__init__()
        self.current_map = tilemap.CombatMap(filename)


class DialogueScene(GameMode):
    def __init__(self, dialogue_file, screen):
        super().__init__()
        self.dialogue = dialogue.Dialogue(dialogue_file)
        self.screen = screen

    def update(self, deltatime):
        super().update(deltatime)
        if not self.paused:
            self.dialogue.update(deltatime)
            self.dialogue.render(self.screen)

    def notify(self, event):
        super().notify(event)
        if not self.paused:
            self.dialogue.notify(event)


class HubScene(BasicScene):
    def __init__(self):
        super().__init__()
        self.current_map = tilemap.FreeMoveMap("data/scenes/hub_scene.json")


class ExpeditionScene(BasicScene):
    def __init__(self):
        super().__init__()
        self.current_map = strategy_map.StrategyMap()

    def notify(self, event):
        button_pressed = self.pause_menu.notify(event)
        if button_pressed is not None:
            if button_pressed == "quit":
                self.new_mode = MainMenu()
                return

        next_mode = self.current_map.notify(event)
        if next_mode is not None:
            self.new_mode = next_mode


class LootScene(GameMode):
    def __init__(self, level=-1):
        super().__init__()
        self.interface = strategy_map.LootInterface(level)

    def update(self, deltatime):
        self.interface.render(self.screen)
        super().update(deltatime)


class ShopScene(GameMode):
    def __init__(self, level=-1):
        super().__init__()
        self.interface = strategy_map.ShopInterface(level)

    def update(self, deltatime):
        self.interface.render(self.screen)
        super().update(deltatime)