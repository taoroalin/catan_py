import random
from board import Board


class Manager:
    def __init__(self, n_players, border_setup, tile_setup, player_names=None):
        self.board = Board(self, n_players, border_setup, tile_setup)
    def first_settlements(self):
        pass