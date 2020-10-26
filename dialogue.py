import pygame
import json
import alchemy_settings as a_settings


def draw_text(surface, text, color, rect, font, aa=False, bkg=None):
    y = rect[1]
    line_spacing = -2

    # get the height of the font
    font_height = font.size("Tg")[1]

    while text:
        i = 1

        # determine if the row of text will be outside our area
        if y + font_height > rect[3]:
            break

        # determine maximum width of line
        while font.size(text[:i])[0] < rect[2] and i < len(text):
            i += 1

        # if we've wrapped the text, then adjust the wrap to the last word
        if i < len(text):
            i = text.rfind(" ", 0, i) + 1

        # render the line and blit it to the surface
        if bkg:
            image = font.render(text[:i], 1, color, bkg)
            image.set_colorkey(bkg)
        else:
            image = font.render(text[:i], aa, color)

        surface.blit(image, (rect[0], y))
        y += font_height + line_spacing

        # remove the text we just blit
        text = text[i:]

    return text


class Dialogue:

    def __init__(self, dialogue_file):
        with open(dialogue_file) as f:
            self.dialogue = json.load(f)

        self.current_line = 0
        self.font = pygame.font.SysFont(None, 48)
        self.text = " "
        self.speaker = " "

        self.surface = pygame.Surface((a_settings.display_width * 2 / 3, a_settings.display_height / 2)).convert()
        self.needs_update = False

        self.next_line()

    def update(self, deltatime):
        pass

    def render(self, screen):
        if self.needs_update:
            screen.fill(pygame.Color("blue"))
            screen.blit(self.surface, (a_settings.display_width / 6, a_settings.display_height / 2))
            self.needs_update = False

    def notify(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.next_line()

    def next_line(self):
        # grab next line from file and render it to a surface once
        if self.current_line < len(self.dialogue["lines"]):
            self.text = self.dialogue["lines"][self.current_line]["text"]
            self.surface.fill(pygame.Color("black"))
            draw_text(self.surface, self.text, (255, 255, 255),
                      (0, 0, self.surface.get_width(), self.surface.get_height()),
                      self.font, True)
            self.needs_update = True
        self.current_line += 1
