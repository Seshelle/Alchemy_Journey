import pygame
import math
import alchemy_settings as a_settings
from dialogue import draw_text


class UIButton:
    def __init__(self, rect, text, button_id, is_button=True, hover_text=None):
        self.button_id = button_id
        self.is_button = is_button

        self.rect = rect
        self.color = pygame.Color("purple")
        self.button_image = pygame.Surface((rect[2], rect[3])).convert()
        self.button_image.fill(self.color)
        self.text = text
        self.font = pygame.font.SysFont(None, 48)
        text_image = self.font.render(text, True, pygame.Color("white"))
        self.button_image.blit(text_image, (0, 0))

        self.active = True

        self.has_hover_text = False
        if hover_text is not None:
            self.has_hover_text = True
            self.hover_size = (256, 128)
            self.hover_font = pygame.font.SysFont(None, 26)
            self.hover_text_image = pygame.Surface(self.hover_size).convert()
            self.hover_text_image.fill(pygame.Color("orange"))
            draw_text(self.hover_text_image, hover_text, pygame.Color("black"),
                      (2, 2, self.hover_size[0], self.hover_size[1]), self.hover_font, True)
            draw_text(self.hover_text_image, hover_text, pygame.Color("white"),
                      (0, 0, self.hover_size[0], self.hover_size[1]), self.hover_font, True)

    def set_active(self, active):
        self.active = active

    def render(self, screen):
        if self.active:
            screen.blit(self.button_image, self.rect)

    def second_render(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        if self.has_hover_text and self.mouse_overlap(mouse_pos):
            screen.blit(self.hover_text_image, (mouse_pos[0], mouse_pos[1] - self.hover_size[1]))

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
        self.texts = []
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

    def add_button(self, rect, text, button_id, is_button=True, hover_text=None):
        # position determines center of button
        # create the button width/height using fractions of screen
        wh = (self.width * rect[2], self.height * rect[3])
        button_rect = (math.ceil(-wh[0] / 2) + self.width * rect[0], math.ceil(-wh[1] / 2) + self.height * rect[1]) + wh
        self.buttons.append(UIButton(button_rect, text, button_id, is_button, hover_text))

    def render(self, screen):
        if self.active:
            for button in self.buttons:
                button.render(screen)
            for button in self.buttons:
                button.second_render(screen)

    def notify(self, event):
        if self.active and event.type == pygame.MOUSEBUTTONDOWN:
            for button in self.buttons:
                if button.is_button and button.mouse_overlap(pygame.mouse.get_pos()):
                    return button.button_id
        return None

    def reset(self, screen):
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.buttons = []
