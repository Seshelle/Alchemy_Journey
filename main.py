import pygame
import game_modes
from game_state import get_deltatime
import alchemy_settings as a_settings
from os import environ
from code import interact
import gc

environ['SDL_VIDEO_CENTERED'] = '1'
pygame.mixer.pre_init()
pygame.init()

screen = pygame.display.set_mode((a_settings.display_width, a_settings.display_height))
pygame.display.set_caption('Alchemy Journey')
clock = pygame.time.Clock()
runtime = 0
crashed = False
debug = False

# set up fonts
basicFont = pygame.font.SysFont(None, 36)

game_mode = game_modes.MainMenu()
while not crashed:

    keypress = None
    # handle pygame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            crashed = True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKQUOTE:
                debug = not debug
                if event.mod & pygame.KMOD_LSHIFT:
                    interact(local=locals())
            if event.key == pygame.K_ESCAPE:
                game_mode.toggle_pause()
        game_mode.notify(event)

    # cProfile.runctx('game_mode.update(deltatime)', globals(), locals())
    game_mode.update(get_deltatime())
    if game_mode.new_mode is not None:
        game_mode = game_mode.new_mode
        gc.collect()

    if debug:
        text = basicFont.render(str(int(clock.get_fps())), True, pygame.Color("white"), pygame.Color("blue"))
        screen.blit(text, (0, 0))

    pygame.display.update()
    clock.tick(144)

pygame.quit()
quit()
