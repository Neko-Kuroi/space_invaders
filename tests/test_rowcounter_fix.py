"""ROW_counter の包み直し条件に関する回帰テスト。

不具合（外部レビューで発見、原典でも再現を確認済み）:
    EnemiesGroup.update の包み直しが `ROW_counter == minRow - 1` の
    一致判定だけだったため、上の行が全滅して minRow が上がると、
    カウンタが一致を飛び越えて下がり続け、敵集団が横にも下にも
    動かなくなった（残り4体以下になると別分岐で復活する）。
    あわせて、ROW_counter は reset() で初期値に戻らなかったため、
    止まった状態が次のゲームにも持ち越され得た。

実行方法（リポジトリのルートで）:
    python -m unittest tests.test_rowcounter_fix -v
"""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pygame  # noqa: E402
import spaceinvaders as si  # noqa: E402


def make_game():
    game = si.SpaceInvaders()
    game.set4Blocker()
    game.reset(0)
    return game


def step_group(game, steps=200):
    """moveTime を超える間隔で EnemiesGroup.update を進め、
    移動サイクル数と敵の移動量を返す。"""
    grp = game.enemies
    base = pygame.time.get_ticks()
    xs_before = sorted(e.rect.x for e in grp)
    cycles = 0
    for f in range(steps):
        before = grp.moveNumber
        grp.update(base + f * 250)
        if grp.moveNumber != before:
            cycles += 1
    xs_after = sorted(e.rect.x for e in grp)
    return cycles, xs_after[0] - xs_before[0]


class RowCounterStallTest(unittest.TestCase):
    def setUp(self):
        self._saved = si.ROW_counter
        self.game = make_game()

    def tearDown(self):
        si.ROW_counter = self._saved

    def wipe_rows(self, rows):
        grp = self.game.enemies
        for e in list(grp):
            if e.row in rows:
                grp.remove(e)

    def test_fleet_moves_when_top_rows_wiped_and_counter_low(self):
        """上2行が全滅し minRow=2、カウンタが 0 の状態でも動き続ける。"""
        self.wipe_rows({0, 1})
        self.assertEqual(self.game.enemies.minRow, 2)
        si.ROW_counter = 0
        cycles, dx = step_group(self.game)
        self.assertGreater(cycles, 0)
        self.assertNotEqual(dx, 0)

    def test_fleet_moves_when_counter_at_min_row_minus_one(self):
        """カウンタがちょうど minRow-1 の位置から始まっても止まらない。"""
        self.wipe_rows({0, 1})
        si.ROW_counter = 1
        cycles, dx = step_group(self.game)
        self.assertGreater(cycles, 0)
        self.assertNotEqual(dx, 0)

    def test_counter_stays_in_range(self):
        """包み直しが効いていれば、カウンタは大きく負に沈まない。"""
        self.wipe_rows({0, 1})
        si.ROW_counter = 0
        step_group(self.game)
        self.assertGreaterEqual(si.ROW_counter, -1)
        self.assertLessEqual(si.ROW_counter, 4)

    def test_reset_restores_row_counter(self):
        """reset() で ROW_counter が初期値 4 に戻る（持ち越しの防止）。"""
        si.ROW_counter = -50
        self.game.reset(0)
        self.assertEqual(si.ROW_counter, 4)

    def test_normal_fleet_still_moves(self):
        """通常状態の動きが壊れていないことの確認。"""
        si.ROW_counter = 4
        cycles, dx = step_group(self.game)
        self.assertGreater(cycles, 0)
        self.assertNotEqual(dx, 0)


if __name__ == "__main__":
    unittest.main()
