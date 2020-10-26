import pygame
import math
import alchemy_settings as a_settings


class UIButton:
    def __init__(self, rect, text, button_id):
        self.button_id = button_id
        self.rect = rect
        self.text = text
        self.font = pygame.font.SysFont(None, 48)
        self.color = pygame.Color("purple")
        self.active = True

    def set_active(self, active):
        self.active = active

    def render(self, screen):
        if self.active:
            pygame.draw.rect(screen, self.color, self.rect)
            text = self.font.render(self.text, True, pygame.Color("white"))
            screen.blit(text, self.rect)

    def mouse_overlap(self, mouse_pos):
        if not self.active:
            return False
        if self.rect[0] <= mouse_pos[0] <= self.rect[0] + self.rect[2] and \
                self.rect[1] <= mouse_pos[1] <= self.rect[1] + self.rect[3]:
            return True
        return False


class UserInterface:
    def __init__(self):
        self.width = a_settings.display_width
        self.height = a_settings.display_height
        self.buttons = []
        self.active = True

    def set_active(self, active):
        self.active = active

    def set_button_active(self, button_id, active):
        for b in self.buttons:
            if b.button_id == button_id:
                b.set_active(active)

    def set_all_buttons_active(self, active=True):
        for b in self.buttons:
            b.set_active(active)

    def add_button(self, rect, text, button_id):
        # position determines center of button
        # create the button width/height using fractions of screen
        wh = (self.width * rect[2], self.height * rect[3])
        button_rect = (math.ceil(-wh[0] / 2) + self.width * rect[0], math.ceil(-wh[1] / 2) + self.height * rect[1]) + wh
        self.buttons.append(UIButton(button_rect, text, button_id))

    def render(self, screen):
        if self.active:
            for button in self.buttons:
                button.render(screen)

    def notify(self, event):
        if self.active and event.type == pygame.MOUSEBUTTONDOWN:
            for button in self.buttons:
                if button.mouse_overlap(pygame.mouse.get_pos()):
                    return button.button_id
        return None

    def reset(self, screen):
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.buttons = []
