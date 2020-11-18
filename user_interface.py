import pygame
import math
import alchemy_settings as a_settings
from dialogue import draw_shadowed_text


def get_text_input(screen):
    user_input = ""
    input_rect = (a_settings.display_width / 3, a_settings.display_height / 3,
                  a_settings.display_width / 3, a_settings.display_height / 3)
    input_border = (a_settings.display_width / 4, a_settings.display_height / 4,
                    a_settings.display_width / 2, a_settings.display_height / 2)
    font = pygame.font.SysFont(None, 48)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                elif event.key == pygame.K_RETURN:
                    return user_input
                elif event.key == pygame.K_ESCAPE:
                    return None
                elif isinstance(event.unicode, str):
                    user_input += event.unicode
        pygame.draw.rect(screen, pygame.Color("blue"), input_border)
        pygame.draw.rect(screen, pygame.Color("black"), input_rect)
        draw_shadowed_text(
            screen,
            user_input,
            pygame.Color("white"),
            (a_settings.display_width / 3, a_settings.display_height / 3,
             a_settings.display_width / 3, a_settings.display_height / 3),
            font,
            True
        )
        pygame.display.update()


class InterfaceImage:
    def __init__(self, rect, text):
        self.rect = rect
        self.color = pygame.Color("purple")
        self.image = pygame.Surface((rect[2], rect[3])).convert()
        self.image.fill(self.color)
        self.text = text
        self.font = pygame.font.SysFont(None, 48)
        text_image = self.font.render(text, True, pygame.Color("white"))
        self.image.blit(text_image, (0, 0))

        self.active = True

    def set_active(self, active):
        self.active = active

    def render(self, screen):
        if self.active:
            screen.blit(self.image, self.rect)

    def mouse_overlap(self, mouse_pos):
        if not self.active:
            return False
        if self.rect[0] <= mouse_pos[0] <= self.rect[0] + self.rect[2] and \
                self.rect[1] <= mouse_pos[1] <= self.rect[1] + self.rect[3]:
            return True
        return False


class UIButton(InterfaceImage):
    def __init__(self, rect, text, button_id, is_button=True, hover_text=None):
        super().__init__(rect, text)

        self.button_id = button_id
        self.is_button = is_button

        self.has_hover_text = False
        if hover_text is not None:
            self.has_hover_text = True
            # TODO: replace these magic numbers
            self.hover_size = (256, 128)
            hover_font = pygame.font.SysFont(None, 26)
            self.hover_text_image = pygame.Surface(self.hover_size).convert()
            self.hover_text_image.fill(pygame.Color("orange"))
            draw_shadowed_text(self.hover_text_image, hover_text, pygame.Color("white"),
                               (0, 0, self.hover_size[0], self.hover_size[1]), hover_font, True)

    def second_render(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        if self.has_hover_text and self.mouse_overlap(mouse_pos):
            screen.blit(self.hover_text_image, (mouse_pos[0], mouse_pos[1] - self.hover_size[1]))


class UserInterface:
    def __init__(self):
        self.width = a_settings.display_width
        self.height = a_settings.display_height
        self.buttons = []
        self.top_layer_images = []
        self.bottom_layer_images = []
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

    def add_image(self, rect, text, bottom_layer=True):
        image_rect = self.ratio_rect_to_screen_rect(rect)
        if bottom_layer:
            self.bottom_layer_images.append(InterfaceImage(image_rect, text))
        else:
            self.top_layer_images.append(InterfaceImage(image_rect, text))

    def add_button(self, rect, text, button_id, is_button=True, hover_text=None):
        button_rect = self.ratio_rect_to_screen_rect(rect)
        self.buttons.append(UIButton(button_rect, text, button_id, is_button, hover_text))

    def ratio_rect_to_screen_rect(self, rect):
        wh = (self.width * rect[2], self.height * rect[3])
        screen_rect = (math.ceil(-wh[0] / 2) + self.width * rect[0],
                       math.ceil(-wh[1] / 2) + self.height * rect[1]) + wh
        return screen_rect

    def render(self, screen):
        if self.active:
            for image in self.bottom_layer_images:
                image.render(screen)
            for button in self.buttons:
                button.render(screen)
            for button in self.buttons:
                button.second_render(screen)
            for image in self.top_layer_images:
                image.render(screen)

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
