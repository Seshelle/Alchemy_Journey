import pygame
import alchemy_settings as a_settings
from dialogue import draw_shadowed_text
import json
import game_modes
from game_state import start_expedition


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


class ImageButton:
    def __init__(self, rect, text, button_id, hover_text=None, image_file=None, is_button=True):
        if image_file is not None:
            self.image = pygame.image.load(image_file).convert()
            # TODO: Make image size dynamic rather than fixed
            size = self.image.get_size()
            self.rect = (rect[0], rect[1], size[0], size[1])
        else:
            self.rect = rect
            self.image = pygame.Surface((rect[2], rect[3]))
            if isinstance(text, pygame.Color):
                self.image.fill(text)
            else:
                self.image.fill(pygame.Color("purple"))

        if text is not None and isinstance(text, str):
            font = pygame.font.SysFont(None, 48)
            text_image = font.render(text, True, pygame.Color("white"))
            self.image.blit(text_image, (0, 0))

        self.has_hover_text = hover_text is not None
        # TODO: replace these magic numbers
        self.hover_size = (256, 128)
        self.hover_text = None
        self.hover_text_image = None
        if self.has_hover_text:
            self.update_hover_text(hover_text)

        self.button_id = button_id
        self.is_button = is_button

        self.active = True

    def update_hover_text(self, description):
        if description != self.hover_text:
            self.hover_text = description
            hover_font = pygame.font.SysFont(None, 26)
            self.hover_text_image = pygame.Surface(self.hover_size).convert()
            self.hover_text_image.fill(pygame.Color("orange"))
            draw_shadowed_text(self.hover_text_image, description, pygame.Color("white"),
                               (0, 0, self.hover_size[0], self.hover_size[1]), hover_font, True)

    def set_active(self, active):
        self.active = active

    def render(self, screen):
        if self.active:
            screen.blit(self.image, self.rect)

    def second_render(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        if self.has_hover_text and self.mouse_overlap(mouse_pos):
            hover_size = self.hover_text_image.get_size()
            hover_placement = mouse_pos
            if mouse_pos[1] > hover_size[1]:
                hover_placement = (hover_placement[0], hover_placement[1] - hover_size[1])
            else:
                hover_placement = (hover_placement[0] + 10, hover_placement[1] + 10)
            if mouse_pos[0] + hover_size[0] > screen.get_width():
                hover_placement = (hover_placement[0] - hover_size[0], hover_placement[1])

            screen.blit(self.hover_text_image, hover_placement)

    def mouse_overlap(self, mouse_pos):
        if self.is_button and self.active:
            if self.rect[0] <= mouse_pos[0] <= self.rect[0] + self.rect[2] and \
                    self.rect[1] <= mouse_pos[1] <= self.rect[1] + self.rect[3]:
                return True
        return False


class DynamicDescription(ImageButton):
    def __init__(self, rect, described, button_id):
        super().__init__(rect, None, button_id, image_file=described.icon)
        self.described = described
        self.update_hover_text(self.described.get_description())

    def second_render(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        if self.mouse_overlap(mouse_pos):
            # update dynamic hover text
            self.update_hover_text(self.described.get_description())
            screen.blit(self.hover_text_image, (mouse_pos[0], mouse_pos[1] - self.hover_size[1]))


class UserInterface:
    def __init__(self, start_active=True):
        self.width = a_settings.display_width
        self.height = a_settings.display_height
        self.buttons = {}
        self.top_layer_images = []
        self.bottom_layer_images = []
        self.active = start_active

    def set_active(self, active):
        self.active = active

    def set_button_active(self, button_id, active):
        self.buttons[button_id].set_active(active)

    def set_all_buttons_active(self, active=True):
        for b in self.buttons.values():
            b.set_active(active)

    def delete_button(self, button_id):
        self.buttons.pop(button_id, None)

    def add_image_button(self, rect, text, button_id, hover_text=None, image_file=None, is_button=True):
        if rect[0] <= 1 and rect[1] <= 1 and (len(rect) < 3 or rect[3] <= 1):
            rect = self.ratio_rect_to_screen_rect(rect)
        self.buttons[button_id] = ImageButton(rect, text, button_id, hover_text, image_file, is_button)

    def add_dynamic_description(self, rect, described):
        if rect[0] <= 1 and rect[1] <= 1 and (len(rect) < 3 or rect[3] <= 1):
            rect = self.ratio_rect_to_screen_rect(rect)
        button_id = described.name
        self.buttons[button_id] = DynamicDescription(rect, described, button_id)

    def move_button(self, button_id, new_rect):
        if new_rect[0] <= 1 and new_rect[1] <= 1 and (len(new_rect) < 3 or new_rect[3] <= 1):
            new_rect = self.ratio_rect_to_screen_rect(new_rect)
        self.buttons[button_id].rect = new_rect

    def ratio_rect_to_screen_rect(self, rect):
        if len(rect) == 4:
            wh = (self.width * rect[2], self.height * rect[3])
        else:
            wh = (self.width, self.height)
        screen_rect = (self.width * rect[0],
                       self.height * rect[1]) + wh
        return screen_rect

    def render(self, screen):
        if self.active:
            for image in self.bottom_layer_images:
                image.render(screen)
            for button in self.buttons.values():
                button.render(screen)
            for button in self.buttons.values():
                button.second_render(screen)
            for image in self.top_layer_images:
                image.render(screen)

    def notify(self, event):
        if self.active and event.type == pygame.MOUSEBUTTONDOWN:
            for button in self.buttons.values():
                if button.is_button and button.mouse_overlap(pygame.mouse.get_pos()):
                    return button.button_id
        return None

    def reset(self, screen):
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.buttons = {}


class EmbarkInterface(UserInterface):
    def __init__(self):
        super().__init__(False)
        # define where the character's centers are for each box
        self.chosen_center = 0.66
        self.box_width = 0.33

        # add a left box and a right box to hold characters
        self.add_image_button((0, 0, self.box_width, 1), pygame.Color("black"), "box1", is_button=False)
        self.add_image_button((self.chosen_center, 0, self.box_width, 1), pygame.Color("black"), "box2", is_button=False)

        # add a button to embark and begin the expedition
        self.add_image_button((0.4, 0.9, 0.2, 0.1), "Embark", "exit")

        # fill left box with characters from character_list that are unlocked
        self.free_characters = {}
        self.chosen_characters = {}
        self.party_slots = [None, None, None, None]
        self.char_height = 0.15
        with open("data/character_list.json") as char_file:
            self.char_data = json.load(char_file)
            for i, c in enumerate(self.char_data.values()):
                char_name = c["name"]
                self.free_characters[char_name] = c
                self.add_image_button(
                    (0, self.char_height * i, self.box_width, self.char_height - 0.02),
                    char_name,
                    char_name
                )

    def notify(self, event):
        if self.active and event.type == pygame.MOUSEBUTTONDOWN:
            for button in self.buttons.values():
                if button.mouse_overlap(pygame.mouse.get_pos()):
                    b_id = button.button_id
                    # Clicking on a character button moves the character to your party from free and vice-versa
                    if len(self.chosen_characters) < 4 and b_id in self.free_characters.keys():
                        # find first free slot in party and move character button there
                        chosen_slot = 0
                        for i, slot in enumerate(self.party_slots):
                            if slot is None:
                                chosen_slot = i
                                self.party_slots[i] = b_id
                                break
                        new_rect = (self.chosen_center, self.char_height * chosen_slot,
                                    self.box_width, self.char_height - 0.02)

                        self.chosen_characters[b_id] = self.free_characters[b_id]
                        del self.free_characters[b_id]
                        self.move_button(b_id, new_rect)

                    elif b_id in self.chosen_characters.keys():
                        self.free_characters[b_id] = self.chosen_characters[b_id]
                        del self.chosen_characters[b_id]

                        # return the character back to its original slot
                        slot = self.char_data.index(self.free_characters[b_id])
                        new_rect = (0, self.char_height * slot,
                                    self.box_width, self.char_height - 0.02)
                        self.move_button(b_id, new_rect)

                        # open up the party slot
                        for i, slot in enumerate(self.party_slots):
                            if slot == b_id:
                                self.party_slots[i] = None

                    elif b_id == "exit":
                        if len(self.chosen_characters) > 0:
                            start_expedition(self.chosen_characters, {}, {})
                            return game_modes.ExpeditionScene()
                    break
        return None


class ArmoryInterface(UserInterface):
    def __init__(self):
        super().__init__(False)
        with open("data/save_data.json", "r") as save_file:
            self.save_data = json.load(save_file)

        # set up box on left to hold character list
        self.box_width = 0.25
        self.character_list = []
        self.char_height = 0.12
        self.add_image_button((0, 0, self.box_width, 1), pygame.Color("black"), "box1", is_button=False)

        # create character list on left
        with open("data/character_list.json") as char_file:
            self.char_data = json.load(char_file)
        count = 0
        for c in self.char_data.keys():
            if self.save_data["characters"][c]["unlocked"] is False:
                continue
            self.character_list.append(c)
            self.add_image_button(
                (0, (self.char_height + 0.02) * count, self.box_width, self.char_height),
                self.char_data[c]["name"], c
            )
            count += 1

        # create add-on display for each character adjacent to them on list
        self.addon_width = 0.15
        self.add_image_button((self.box_width, 0, self.addon_width, 1),
                              pygame.Color("black"), "addbox", is_button=False)
        count = 0
        spacing = 0.005
        self.addon_offset = 1000
        for c in self.character_list:
            self.add_image_button((self.box_width + spacing, count * (self.char_height + 0.02),
                                   self.addon_width / 2 - spacing * 2, self.char_height),
                                  pygame.Color("yellow"), (count + 1) * self.addon_offset)
            self.add_image_button((self.box_width + self.addon_width / 2 + spacing, count * (self.char_height + 0.02),
                                   self.addon_width / 2 - spacing * 2, self.char_height),
                                  pygame.Color("yellow"), (count + 1) * self.addon_offset + 1)
            count += 1

        # create skill display on top right
        self.menu_spacing = 0.02
        self.add_image_button((self.box_width + self.menu_spacing + self.addon_width, 0,
                               1 - self.menu_spacing - self.box_width - self.addon_width, 0.25),
                              pygame.Color("black"), "skillbox", is_button=False)

        # populate skill display with skills from first character
        self.skill_dimensions = 0.05
        with open("data/skill_list.json") as skill_file:
            self.skill_data = json.load(skill_file)
        self.selected_character = None
        self.skill_button_list = []
        self.reset_skill_list(list(self.char_data.keys())[0])

        # create addon inventory on right, starts hidden
        self.working_slot = 0
        self.add_image_button((self.box_width + self.menu_spacing + self.addon_width, 0,
                               1 - self.menu_spacing - self.box_width - self.addon_width, 1),
                              pygame.Color("black"), "invbox", is_button=False)
        self.set_button_active("invbox", False)

        # create a button for each addon in player's inventory
        with open("data/addons.json") as addon_file:
            self.addon_data = json.load(addon_file)
        self.inventory_buttons = []
        self.reset_inventory()

    def notify(self, event):
        button_id = None
        if self.active and event.type == pygame.MOUSEBUTTONDOWN:
            for button in self.buttons.values():
                if button.is_button and button.mouse_overlap(pygame.mouse.get_pos()):
                    button_id = button.button_id
                    break
        if button_id is None:
            return None

        # if the button_id is an integer, then it is an add-on slot
        if isinstance(button_id, int):
            if button_id >= 1000:
                # open up inventory so player can swap the add-on in that character's add-on slot
                slot = button_id % self.addon_offset
                character_pos = round(button_id / self.addon_offset) - 1
                slot += character_pos * 2
                # select the character whose slot it is
                self.reset_skill_list(self.character_list[character_pos])
                self.open_inventory(slot)
        elif button_id in self.char_data.keys():
            # select a character and show their skills
            self.reset_skill_list(button_id)
        elif button_id in self.addon_data.keys():
            self.swap_addon(button_id)

        return button_id

    def reset_skill_list(self, character_key):
        self.selected_character = character_key
        # delete all skills displayed for previously selected character
        for button in self.skill_button_list:
            self.delete_button(button)
        self.skill_button_list.clear()

        count = 0
        skill_list = self.char_data[self.selected_character]["skills"]
        # create a display of the newly selected character's skills
        for skill in skill_list:
            skill_image = "images/icons/skill_icon.png"
            self.add_image_button(
                (self.box_width + self.menu_spacing + self.addon_width + self.skill_dimensions * count, 0,
                 self.skill_dimensions, self.skill_dimensions),
                None, self.skill_data[skill]["name"], self.skill_data[skill]["desc"], skill_image)
            self.skill_button_list.append(self.skill_data[skill]["name"])
            count += 1

    def reset_inventory(self):
        for button in self.inventory_buttons:
            self.delete_button(button)
        self.inventory_buttons.clear()

        count = 0
        for a in self.save_data["addons"].keys():
            addon = self.save_data["addons"][a]
            if addon["count"] > 0:
                addon_image = "images/icons/skill_icon.png"
                addon_desc = create_addon_desc(addon)
                self.add_image_button(
                    (self.box_width + self.menu_spacing + self.addon_width + self.skill_dimensions * count, 0,
                     self.skill_dimensions, self.skill_dimensions),
                    None, a, addon_desc, addon_image)
                self.inventory_buttons.append(a)
                count += 1
        for button in self.inventory_buttons:
            self.set_button_active(button, False)

    def set_inventory_active(self, active):
        self.set_button_active("invbox", active)
        for button in self.inventory_buttons:
            self.set_button_active(button, active)
        for button in self.skill_button_list:
            self.set_button_active(button, not active)

    def open_inventory(self, slot):
        self.working_slot = slot
        self.reset_skill_list(self.character_list[round((slot - slot % 2) / 2)])
        self.set_inventory_active(True)

    def swap_addon(self, addon_id):
        # copy the selected addon to the working slot
        which_slot = "slot" + str(self.working_slot % 2)
        if self.save_data["characters"][self.selected_character][which_slot] != "none":
            prev_addon = self.save_data["characters"][self.selected_character][which_slot]
            self.save_data["addons"][prev_addon]["count"] += 1
        if addon_id is not None:
            self.save_data["characters"][self.selected_character][which_slot] = self.addon_data[addon_id]
            self.save_data["addons"][addon_id]["count"] -= 1
        else:
            self.save_data["characters"][self.selected_character][which_slot] = "none"
        self.save_changes()
        self.reset_inventory()
        self.set_inventory_active(False)

    def unequip_all(self):
        for character in self.save_data["characters"].keys():
            addon = self.save_data["characters"][character]["slot0"]
            if addon != "none":
                self.save_data["addons"][addon] += 1
                self.save_data["characters"][character]["slot0"] = "none"
            addon = self.save_data["characters"][character]["slot1"]
            if addon != "none":
                self.save_data["addons"][addon] += 1
                self.save_data["characters"][character]["slot1"] = "none"
        self.save_changes()
        self.reset_inventory()

    def save_changes(self):
        with open("data/save_data.json", "w") as save_file:
            json.dump(self.save_data, save_file)


def create_addon_desc(addon):
    addon_desc = addon["name"]
    if "desc" in addon:
        addon_desc += "\n" + addon["desc"]
    for mod in addon["effects"].keys():
        addon_desc += "\n" + mod + ": " + str(addon["effects"][mod])
    return addon_desc
