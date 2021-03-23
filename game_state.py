import random
import pygame
import json


class GameState:
    # data that is remembered between game mode changes
    expedition_seed = random.random()
    expedition_location = [-1, -1]
    player_characters = {}
    expedition_inventory = {}
    expedition_modifiers = {}


def start_expedition(player_data, inventory, modifiers):
    GameState.expedition_seed = random.random()
    GameState.expedition_location = [-1, -1]
    GameState.player_characters = player_data
    GameState.expedition_inventory = inventory
    GameState.expedition_modifiers = modifiers


def update_player(player):
    player_data = GameState.player_characters[player.name]
    saved_health = player.health
    if saved_health <= 0:
        saved_health = 1
    player_data["current health"] = saved_health
    player_data["current mana"] = player.mana


def add_to_inventory(item, amount):
    inv = GameState.expedition_inventory
    if item in inv:
        inv[item] += amount
    else:
        inv[item] = amount


def dump_inventory():
    # saves loot gained from an expedition to save_data
    inv = GameState.expedition_inventory
    with open("data/save_data.json", "w") as save_file:
        save_data = json.load(save_file)
        for item in inv.keys():
            if item in save_data["currency"]:
                save_data["currency"][item] += inv[item]
            elif item in save_data["addons"]:
                save_data["addons"][item] += inv[item]
            else:
                save_data["addons"][item] = inv[item]
        json.dump(save_data, save_file)


def add_to_attribute(data, key, value):
    if key in data.keys():
        data[key] += value
    else:
        data[key] = value


class StoryState:
    progress = 0


class Timer:
    last_update = 0


def get_deltatime():
    runtime = pygame.time.get_ticks()
    time = runtime - Timer.last_update
    if time > 50:
        time = 50
    Timer.last_update = runtime
    return time
