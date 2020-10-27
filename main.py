import pygame
import tilemap
import game_modes
import alchemy_settings as a_settings
import os
from code import interact

os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()

screen = pygame.display.set_mode((a_settings.display_width, a_settings.display_height))
pygame.display.set_caption('Alchemy Journey')
clock = pygame.time.Clock()
runtime = 0
crashed = False
debug = False
super_debug = False
debug_string = ""

# set up fonts
basicFont = pygame.font.SysFont(None, 36)
tile_extent = tilemap.tile_extent

game_mode = game_modes.MainMenu(screen)
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
                crashed = True
        if not super_debug:
            game_mode.notify(event)

    # run upkeep and render for each object
    deltatime = pygame.time.get_ticks() - runtime
    runtime = pygame.time.get_ticks()

    # cProfile.runctx('game_mode.update(deltatime)', globals(), locals())
    game_mode.update(deltatime)
    if game_mode.new_mode is not None:
        game_mode = game_mode.new_mode

    if debug:
        text = basicFont.render(str(int(clock.get_fps())), True, pygame.Color("white"), pygame.Color("blue"))
        screen.blit(text, (0, 0))

    pygame.display.update()
    clock.tick(144)

pygame.quit()
quit()
