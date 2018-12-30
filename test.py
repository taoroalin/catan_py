import unittest
import manager
import board
import numpy as np

class PlayerTest(unittest.TestCase):
    def setUp(self):
        self.player = board.Player(None)
        self.bank_statement = {"Wood": 1, "Brick": 1,
                               "Wheat": 1, "Rock": 1, "Sheep": 1}
        self.blank_bank_statement = {
            "Wood": 0, "Brick": 0, "Wheat": 0, "Rock": 0, "Sheep": 0}
        self.player.get(self.bank_statement)

    def testHas(self):
        self.assertTrue(self.player.has(self.bank_statement))
        extra = self.bank_statement.copy()
        extra["Wood"] += 1
        self.assertFalse(self.player.has(extra))

    def testGet(self):
        self.player.get(self.bank_statement)
        should_have = {a: 2*b for a, b in self.bank_statement.items()}
        self.assertEqual(self.player.resources, should_have)

    def testSpend(self):
        self.assertTrue(self.player.spend(self.bank_statement))
        self.assertEquals(self.player.resources, {
                          a: 0 for a in self.bank_statement})

    def testTakeRandom(self):
        stolen = self.blank_bank_statement
        for _ in range(5):
            find = self.player.take_random()
            for key in stolen:
                stolen[key] += find[key]
        self.assertEquals(stolen, self.bank_statement)

    def testDiscardHalf(self):
        two_resources = self.blank_bank_statement.copy()
        two_resources["Wheat"] = 1
        two_resources["Rock"] = 1
        self.assertFalse(self.player.discard_half(two_resources))
        four_resources = two_resources.copy()
        four_resources["Sheep"] = 1
        four_resources["Brick"] = 1
        three_resources = two_resources.copy()
        three_resources["Sheep"] += 1 
        self.player.get(three_resources)
        self.assertTrue(self.player.discard_half(four_resources))
        should_have = two_resources.copy()
        should_have["Wood"] = 1
        self.assertEquals(self.player.resources, should_have)

    def testGetDevcard(self):
        self.player.get_devcard("Knight", 2)
        self.assertEquals(self.player.facedown_devcards, [("Knight", 2)])

    def testFlipDevcard(self):
        self.player.get_devcard("Victory", 2)
        self.assertTrue(self.player.can_flip_devcard("Victory", 4))
        self.assertEqual(self.player.can_flip_devcard("Victory", 4, v=True), 0)
        self.assertTrue(self.player.flip_devcard("Victory", 4))
        self.assertFalse(self.player.flip_devcard("Victory", 5))
        self.player.get_devcard("Victory", 3)
        self.assertFalse(self.player.flip_devcard("Victory", 4))
        self.player.get_devcard("Knight", 6)
        self.assertFalse(self.player.flip_devcard("Knight", 6))


class TileTest(unittest.TestCase):
    def setUp(self):
        self.forest = board.Tile("Wood", 6)
        self.desert = board.Tile("Desert", 0)
        self.robbed = board.Tile("Wood", 3)
        self.blank_bank_statement = {
            "Wood": 0, "Brick": 0, "Wheat": 0, "Rock": 0, "Sheep": 0}
        self.robbed.rob()

    def testProduce(self):
        self.assertTrue(self.forest.produce(6))
        self.assertFalse(self.forest.produce(5))
        self.assertFalse(self.robbed.produce(3))

    def testGive(self):
        one_resource = self.blank_bank_statement.copy()
        one_resource["Wood"] = 1
        self.assertEquals(self.forest.give(), one_resource)


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.standard = board.Board(None, 3, "standard", "basic")
        # self.free = board.Board(None, 4, "random", "random")
        self.bank_statement = {"Wood": 1, "Brick": 1,
                               "Wheat": 1, "Rock": 1, "Sheep": 1}
        self.blank_bank_statement = {
            "Wood": 0, "Brick": 0, "Wheat": 0, "Rock": 0, "Sheep": 0}
        self.beginning = board.Board(None, 2, "standard", "basic")
        self.beginning.build_settlement(1, 0, initial=True)
        self.beginning.build_settlement(4, 4, initial=True)
        self.beginning.build_road(1, 0, free=True)
        self.beginning.build_road(2, 2, free=True)

    def testConversions(self):
        roadinitial = np.zeros(72, dtype=np.bool_)
        roadinitial[0] = True
        boundingsettlements = np.zeros(54, dtype=np.bool_)
        boundingsettlements[0] = True
        boundingsettlements[1] = True
        self.assertEqual(board.Board.r2s(0), boundingsettlements)
        
    def testInit(self):
        ddeck = [
            *["Knight"]*14,
            *["Monopoly"]*2,
            *["Road Building"]*2,
            *["Victory"]*5,
            *["Year of Plenty"]*2
        ]
        self.assertNotEqual(self.standard.devdeck, ddeck)
        self.assertEqual(sorted(self.standard.devdeck), ddeck)

    def testRoll(self):
        for i in range(1, 13):
            self.standard.roll(fix=i)

    def testBuyRoad(self):
        self.assertFalse(self.standard.build_road(1, 1))
        self.assertTrue(self.beginning.build_road(1, 1, free=True))

    def testBuySettlement(self):
        self.assertFalse(self.standard.build_settlement(1, 1))

    def testBuyCity(self):
        self.assertFalse(self.standard.build_city(1, 1))


if __name__ == "__main__":
    unittest.main()
