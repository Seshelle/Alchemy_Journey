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
        # if y + font_height > rect[1] + rect[3]:
        #    break

        # determine maximum width of line
        while font.size(text[:i])[0] < rect[2] and i < len(text):
            i += 1
            if i < len(text) and text[i] == "\n":
                i += 1
                break

        # if we've wrapped the text, then adjust the wrap to the last word
        if i < len(text):
            i = max(text.rfind(" ", 0, i) + 1, text.rfind("\n", 0, i) + 1)

        # render the line and blit it to the surface
        clean_text = text[:i].replace("\n", "")
        if bkg:
            image = font.render(clean_text, 1, color, bkg)
            image.set_colorkey(bkg)
        else:
            image = font.render(clean_text, aa, color)

        surface.blit(image, (rect[0], y))
        y += font_height + line_spacing

        # remove the text we just blit
        text = text[i:]

    return text


def draw_shadowed_text(surface, text, color, rect, font, aa=False, bkg=None):
    rect2 = (rect[0] + 2, rect[1] + 2, rect[2], rect[3])
    draw_text(surface, text, (0, 0, 1), rect2, font, aa, bkg)
    draw_text(surface, text, color, rect, font, aa, bkg)


class Dialogue:

    def __init__(self, dialogue_file, start_active=True):
        with open(dialogue_file) as f:
            self.dialogue = json.load(f)

        self.current_line = 0
        self.break_message = None
        self.font = pygame.font.SysFont(None, 48)
        self.text = " "
        self.text_color = pygame.Color("white")
        self.speaker = " "
        self.speaker_color = pygame.Color("white")
        self.speech = pygame.Surface((a_settings.display_width * 2 / 3, a_settings.display_height / 2)).convert()

        self.camera_set = None

        self.active = start_active
        if start_active:
            self.next_line()

    def update(self, deltatime):
        pass

    def render(self, screen):
        if self.active:
            screen.blit(self.speech, (a_settings.display_width / 6, a_settings.display_height / 2))

    def notify(self, event):
        if self.active and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.next_line()
            return self.active

    def set_active(self, active):
        self.active = active
        if active:
            self.break_message = None
            self.next_line()
        else:
            self.break_message = "stopped"

    def next_line(self):
        # grab next line from file and render it to a surface once
        if self.current_line < len(self.dialogue["lines"]):

            # get next line of speech from file
            line = self.dialogue["lines"][self.current_line]

            if "camera x" in line.keys():
                self.camera_set = (line["camera x"], line["camera y"])

            if "break" in line.keys():
                self.break_message = line["break"]
                self.active = False

            if "text" in line.keys():
                self.text = line["text"]
                self.speech.fill(pygame.Color("brown"))

                # if a new speaker is defined for the line, draw it to title line
                if "speaker" in line.keys():
                    self.speaker = line["speaker"]

                title_height = 60
                title_pad_top = 10
                title_pad_left = 10
                speech_pad_left = 20
                draw_text(self.speech, self.speaker, pygame.Color("white"),
                          (title_pad_left, title_pad_top,
                           self.speech.get_width(), title_height),
                          self.font, True)
                draw_text(self.speech, self.text, pygame.Color("white"),
                          (speech_pad_left, title_height,
                           self.speech.get_width() - speech_pad_left * 2, self.speech.get_height() - title_height),
                          self.font, True)
        else:
            self.break_message = "EOF"
            self.active = False
        self.current_line += 1
