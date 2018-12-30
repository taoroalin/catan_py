"""

Python Settlers of Catan

by Tao Lin

Notable features:

Saves all board and deck state in one Board object
with Player objects to keep track of resources, Dev cards, VPs, ports, road length, Knight count, etc..

Stores settlement/road/city information in an array with [0, 1, 2, 3, 4] at each position
Checks settlement and road legality with an road adjacency matrix created in Excel
Uses a recursive crawler to check road length after each road is placed
Uses an adjacency matrix to produce resources from tiles

"""

import random
import numpy as np
import pandas as pd
import functools
import itertools
bank_statement = {"Wood": 0, "Brick": 0, "Wheat": 0, "Rock": 0, "Sheep": 0}


class Player:
    """
    Player object handles all aspects of a player except game board pieces
    Player gives and receives resources, checks for devcard legality, 
    randomly pops resources, and discards half
    """

    def __init__(self, board, winvp=10):
        self.resources = bank_statement.copy()
        self.victory_points = 0
        self.facedown_devcards = []
        self.faceup_devcards = []
        self.ports = set()
        self.winvp = winvp
        self.board = board
        
        # Longest Road tracking
        self.longest_road = False
        self.road_length = 0

        # Largest Army Tracking
        self.knight_count = 0
        self.largest_army = False

        # Number of game pieces left
        self.settlements = 5
        self.cities = 4
        self.roads = 15

    def addvp(self):
        self.victory_points += 1
        if self.victory_points >= self.winvp:
            self.board.won(self)

    def addport(self, port):
        if not self.ports.issuperset({port}):
            self.ports = self.ports.union({port})

    def has(self, resources):
        for resource in self.resources:
            if self.resources[resource] < resources[resource]:
                return False
        return True

    def get(self, resources):
        for resource in self.resources:
            self.resources[resource] += resources[resource]

    def spend(self, resources):
        if self.has(resources):
            for resource in self.resources:
                self.resources[resource] -= resources[resource]
            return True
        return False

    def take_random(self):
        total = sum(self.resources.values())
        chosen = random.randint(1, total)
        for r in self.resources:
            if chosen > self.resources[r]:
                chosen -= self.resources[r]
            else:
                receipt = bank_statement.copy()
                receipt[r] += 1
                self.spend(receipt)
                return receipt
        print("take_random error")
        return False

    def get_devcard(self, card, turn_number):
        self.facedown_devcards.append((card, turn_number))

    def discard_half(self, resources):
        hand_size = sum(self.resources.values())
        if hand_size > 7:
            number_to_discard = hand_size//2
            if sum(resources.values()) == number_to_discard:
                if self.spend(resources):
                    return True
                print("You don't have those resources!")
                return False
            print("That's the wrong number of cards!")
            return False
        print("You don't need to discard; you have 7 or fewer cards!")
        return False

    def can_flip_devcard(self, card, turn_number, v=False):
        # Check if you have the given card and that you got it before this turn
        for i, mine in enumerate(self.facedown_devcards):
            if mine[0] == card and mine[1] < turn_number:
                # Check whether you've already used a devcard this turn
                for used in self.faceup_devcards:
                    if used[1] >= turn_number:
                        break
                else:
                    if v:
                        return i
                    else:
                        return True
        return False

    def flip_devcard(self, card, turn_number):
        c = self.can_flip_devcard(card, turn_number, v=True)
        if c is not False:
            del self.facedown_devcards[c]
            self.faceup_devcards.append((card, turn_number))
            return True
        return False


class Tile:
    """
    Tile can check if it produces, and give a receipt for what it produces
    """

    def __init__(self, resource, number):
        self.resource = resource
        self.number = number
        self.robber = False
        if self.resource == "Desert":
            self.robber = True

    def produce(self, roll):
        if self.number == roll and self.robber == False and self.resource != "Desert":
            return True
        return False

    def clearrobber(self):
        self.robber = False

    def rob(self):
        self.robber = True

    def give(self, count=1):
        r = bank_statement.copy()
        r[self.resource] = count
        return r

    def dots(self):
        if self.resource != "Desert":
            return [0, 0, 1, 2, 3, 4, 5, None, 5, 4, 3, 2, 1][self.number]
        return None

    def color(self):
        if self.resource == "Desert":
            return None
        elif self.number == 6 or self.number == 8:
            return "red"
        return "black"


class Border:
    """
    Border transforms an arrangement of border segments 
    into a mapping from settlement to port

    It also has the default border setup hardcoded
    """
    default_ports = [
        [None, None, "Wild", None, None],
        ["Wild", None, None, "Brick", None],
        [None, None, "Wood", None, None],
        ["Wild", None, None, "Wheat", None],
        [None, None, "Rock", None, None],
        ["Wild", None, None, "Sheep", None]
    ]
    all_ports = [*["Wild"]*4, "Brick", "Wood", "Wheat", "Rock", "Sheep"]

    def __init__(self, mode):
        if mode == "standard":
            self.ports = Border.default_ports.copy()
        elif mode == "random":
            self.ports = Border.default_ports.copy()
            random.shuffle(self.ports)
        elif mode == "scrambled":
            self.ports = Border.default_ports.copy()
            self.port_order = Border.all_ports.copy()
            random.shuffle(self.port_order)
            port_order = self.port_order.copy()
            for i, s in enumerate(self.ports):
                for j, p in enumerate(s):
                    if p is not None:
                        self.ports[i][j] = port_order.pop()
        else:
            raise ValueError("Bad border mode")
        self.map = [None]*54
        c = 0
        for s in self.ports:
            for p in s:
                c += 1
                if p is not None:
                    self.map[c] = p
                    if c == 29:
                        self.map[0] = p
                    else:
                        self.map[c+1] = p

    def port(self, location):
        return self.map[location]


class Board:
    """
    Board manages the game state
    It handles all transformations from one valid game state to another
    """
    costs = {"Road": {"Wood": 1, "Brick": 1, "Wheat": 0, "Rock": 0, "Sheep": 0},
             "Settlement": {"Wood": 1, "Brick": 1, "Wheat": 1, "Rock": 0, "Sheep": 1},
             "City": {"Wood": 0, "Brick": 0, "Wheat": 2, "Rock": 3, "Sheep": 0},
             "Development Card": {"Wood": 0, "Brick": 0, "Wheat": 1, "Rock": 1, "Sheep": 1}}
    # cols are junctions, rows are roads
    road_adjacency = pd.read_csv("road.csv", header=0, index_col=0)
    road_adjacency = road_adjacency.apply(lambda x: np.bool_(x))
    # cols are junctions, rows are tiles
    tile_adjacency = pd.read_csv("tile.csv", header=0, index_col=0)
    tile_adjacency = tile_adjacency.apply(lambda x: np.bool_(x))

    @staticmethod
    def s2r(location):
        x = Board.road_adjacency.iloc[:, location]
        return x

    @staticmethod
    def r2s(location):
        x = Board.road_adjacency.iloc[location, :]
        return x

    @staticmethod
    def r2r(location):
        s = Board.r2s(location)
        r = np.any(Board.road_adjacency.loc[:, s], 1)
        r[location] = False
        return r

    @staticmethod
    def s2s(location):
        r = Board.s2r(location)
        s = np.any(Board.road_adjacency.loc[r, :], 0)
        s[location] = False
        return s

    @staticmethod
    def s2t(location):
        return Board.tile_adjacency.iloc[:, location]

    @staticmethod
    def t2s(location):
        return Board.tile_adjacency.iloc[location, :]

    def __init__(self, manager, n_players, border_setup="standard", tile_setup="random"):
        """
        This sets up everything prior to initial settlement placement.
        Here's what it does:
            Assigns resources to each tile, including robbing the Desert
            Assigns numbers to the tiles based on the predefined order

            Generates the port arrangement

            Shuffles the Dev card deck

            Initializes all roads and cities to 0

            Sets the turn counter and player counters to 0

        """

        self.manager = manager

        resources = ["Brick", "Wheat", "Sheep", "Sheep", "Rock", "Brick", "Wood", "Sheep",
                     "Rock", "Wheat", "Wheat", "Wood", "Rock", "Wheat", "Wood", "Sheep", "Brick", "Wood", "Desert"]
        if tile_setup == "random":
            random.shuffle(resources)
        elif tile_setup == "basic":
            pass
        else:
            raise ValueError("Bad Tile Setup")
        number_order = [5, 6, 11, 5, 8, 10, 9,
                        2, 10, 12, 9, 8, 3, 4, 3, 4, 6, 11]
        self.tiles = []
        for resource in resources:
            if resource == "Desert":
                self.tiles.append(Tile("Desert", 0))
            else:
                self.tiles.append(Tile(resource, number_order.pop(0)))

        self.border = Border(border_setup)

        self.roads = np.zeros(72, dtype=np.int8)
        self.settlements = np.zeros(54, dtype=np.int8)
        self.cities = np.zeros(54, dtype=np.int8)

        self.devdeck = [
            *["Knight"]*14,
            *["Monopoly"]*2,
            *["Road Building"]*2,
            *["Victory"]*5,
            *["Year of Plenty"]*2
        ]
        random.shuffle(self.devdeck)

        # Using an extra player
        # to make players array practically start at 0
        self.players = [Player(self) for x in range(n_players + 1)]

        self.last_turn = 0
        self.turn_number = 0

    def check_road_length(self, player, location):
        """
        This is the most computer-science intensive part of the game
        It crawls through the road-adjacency graph recursively
        to find the longest road
        """
        def crawler(used, location, mode="distance"):
            joints = Board.road_adjacency.iloc[:, location]
            if sum(joints) != 2:
                print("Bad adjacency graph: road doesn't have 2 endpoints")
            options = np.zeros(72, dtype=np.int8)
            for i, joint in enumerate(joints):
                options += self.roads * \
                    Board.road_adjacency.iloc[joint, :] == player
            options = options*(1-used)
            here = np.zeros(72, dtype=np.int8)
            if sum(options) > 0:
                paths = []
                for i, option in enumerate(options):
                    if option == 1:
                        here = np.zeros(72, dtype=np.int8)
                        here[location] = 1
                        paths.append(crawler(used + here, i))
                if mode == "distance":
                    return max(paths) + 1
                elif mode == "ends":
                    return np.sum(paths, 0)
                return False
            else:
                if mode == "distance":
                    return 1
                elif mode == "ends":
                    return here
                return False
        right_points = Board.road_adjacency.iloc[:, location]
        for i, h in enumerate(right_points):
            if h == 1:
                right_points[h] = 0
        left_endpoints = crawler([right_points], location, mode="ends")
        longest_road = 0
        for i, endpoint in enumerate(left_endpoints):
            if endpoint == 1:
                longest_road = max(
                    longest_road, crawler([], i, mode="distance"))
        print("Found a long road:", longest_road)
        if longest_road >= 5:
            if self.players[player].road_length < longest_road:
                self.players[player].road_length = longest_road
                for other_player in self.players:
                    if other_player.road_length >= longest_road:
                        break
                else:
                    for other_player in self.players:
                        player.longest_road = False
                    self.players[player].longest_road = True

    def build_road(self, player, location, free=False):
        if self.roads[location] == 0 and self.players[player].roads > 0:
            next_settlements = Board.r2s(location)
            next_roads = Board.r2r(location)
            has_settlement = sum(self.settlements[next_settlements] == player)
            has_city = sum(self.cities[next_settlements] == player)
            has_road = sum(self.roads[next_roads] == player)
            if has_settlement + has_road + has_city > 0:
                if free or self.players[player].spend(Board.costs["Road"]):
                    self.roads[location] = player
                    self.players[player].roads -= 1
                    self.check_road_length(player, location)
                    return True
                print("No Resources!")
                return False
            print("No connection!")
            return False
        print("You're Blocked!")
        return False

    def build_settlement(self, player, location, initial=False, getnear=False):
        blocking_locations = Board.s2s(location)
        if sum((self.settlements+self.cities)*blocking_locations) == 0:
            if sum(self.roads[Board.s2r(location)] == player) > 0:
                if self.players[player].spend(Board.costs["Settlement"]):
                    self.settlements[location] = player
                    self.players[player].addvp()
                    self.players[player].settlements -= 1
                    self.players[player].addport(self.border.port(location))
                    return True
                else:
                    print("No Resources!")
            elif initial == True:
                self.settlements[location] = player
                self.players[player].settlements -= 1
                self.players[player].addvp()
                self.players[player].addport(self.border.port(location))
                if getnear:
                    for i, t in enumerate(Board.s2t(location)):
                        if t:
                            self.players[player].get(self.tiles[i].give())
                return True
            else:
                print("No Road")
        else:
            print("You're Blocked")
        return False

    def build_city(self, player, location):
        if self.settlements[location] == player and self.players[player].cities > 0:
            if self.players[player].spend(Board.costs["City"]):
                self.settlements[location] = 0
                self.players[player].cities -= 1
                self.players[player].settlements += 1
                self.cities[location] = player
                return True
            print("No Resources!")
            return False
        print("You need a settlement there first!")
        return False

    def buy_devcard(self, player):
        if len(self.devdeck) > 0:
            if self.players[player].spend(Board.costs["Development Card"]):
                self.players[player].get_devcard(self.devdeck.pop())
                return True
            print("No Resources!")
            return False
        print("You losers used all the dev cards!")
        return False

    def roll(self, fix=None):
        if self.last_turn == len(self.players):
            self.last_turn = 1
            self.turn_number += 1
        else:
            self.last_turn += 1
        result = random.randint(1, 6) + random.randint(1, 6)
        if fix is not None:
            result = fix
        if result != 7:
            for i, tile in enumerate(self.tiles):
                if tile.produce(result):
                    spots = Board.t2s(i)
                    settlements = self.settlements[spots]
                    cities = self.cities[spots]
                    for settlement in settlements:
                        if settlement != 0:
                            self.players[settlement].get(tile.give(1))
                    for city in cities:
                        if city != 0:
                            self.players[city].get(tile.give(2))
            return result
        else:
            return 7

    def rob(self, player1, player2, location):
        if self.tiles[location].robber == False:
            spots = Board.t2s(location)
            if sum(self.settlements[spots] == player2) > 0 or sum(self.cities[spots] == player2) > 0:
                for tile in self.tiles:
                    tile.clearrobber()
                self.tiles[location].rob()
                self.players[player1].get(self.players[player2].take_random())
                return True
            print("That player isn't next to that tile!")
            return False
        print("The robber must move to a different tile!")
        return False

    def knight(self, player, special):
        if self.rob(player, special[0], special[1]):
            self.players[player].knight_count += 1

            # Check for largest army
            if self.players[player].knight_count > 2:
                for i, _ in enumerate(self.players):
                    if i != player:
                        if self.players[i].knight_count >= self.players[player].knight_count:
                            break
                else: # If the loop didn't break
                    for p in self.players:
                        if p.largest_army:
                            p.largest_army = False
                            p.victory_points -= 2
                    self.players[player].largest_army = True
                    self.players[player].addvp()
                    self.players[player].addvp()
            return True
        return False

    def monopoly(self, player, special):
        if type(special) == str and special in bank_statement.keys():
            for i, player in enumerate(self.players):
                receipt = bank_statement.copy()
                resource_number = player.resources[special]
                receipt[special] = resource_number
                self.players[player].get(self.players[i].spend(receipt))
            return True
        print("Monopoly takes a bank statement!")
        return False

    def year_of_plenty(self, player, special):
        if type(special) == dict and len(special) == 5:
            if sum(special.values()) == 2:
                self.players[player].get(special)
                return True
            print("That wasn't two resources!")
            return False
        print("That wasn't a receipt!")
        return False

    def road_building(self, player, special):
        if len(special) == 2 and type(special[0]) == int and type(special[1]) == int:
            if self.build_road(player, special[0], free=True) and self.build_road(player, special[1], free=True):
                return True
        print("That isn't 2 locations!")
        return False

    def activate_devcard(self, player, card, turn_number, special):
        if self.players[player].can_flip_devcard(card, self.turn_number):
            if card == "Knight":
                if self.knight(player, special):
                    self.players[player].flip_devcard(card, turn_number)
                    return True
            elif card == "Victory":
                self.players[player].addvp()
                self.players[player].flip_devcard(card, turn_number)
                return True
            elif card == "Monopoly":
                if self.monopoly(player, special):
                    self.players[player].flip_devcard(card, turn_number)
                    return True
            elif card == "Road Building":
                if self.road_building(player, special):
                    self.players[player].flip_devcard(card, turn_number)
                    return True
                return False
            elif card == "Year of Plenty":
                if self.year_of_plenty(player, special):
                    self.players[player].flip_devcard(card, turn_number)
                    return True
            else:
                print("Not a valid card")
                return False
        print("You can't use that dev card!")
        return False
