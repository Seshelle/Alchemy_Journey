import random


class GameState:
    # data that is remembered between game mode changes
    expedition_seed = 0
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


def add_to_attribute(data, key, value):
    if key in data.keys():
        data[key] += value
    else:
        data[key] = value


class StoryState:
    progress = 0
