"""main.py（pygbag 用）の ROW_counter 包み直し条件に関する回帰テスト。

不具合（外部レビューで発見、main.py の実コードでも再現を確認済み）:
    原典 spaceinvaders.py で直した ROW_counter の停止バグが、
    pygbag 用の写しである main.py には直っていないまま残っていた。
    EnemiesGroup.update の包み直しが `ROW_counter == minRow - 1` の
    一致判定だけのため、上の行が全滅して minRow が上がると、
    カウンタが一致を飛び越えて下がり続け、敵集団が止まってしまう。
    reset() でカウンタを初期値に戻していない点も原典の修正前と同じ。

実行方法（リポジトリのルートで）:
    python -m unittest tests.test_main_rowcounter_fix -v

注意: main.py と spaceinvaders.py はどちらも import 時に画面を
作るため、同じプロセスに両方を読み込むと2つ目の画面作成で落ちる。
そのため各シナリオは子プロセスで実行し、結果だけを受け取る。
"""
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCENARIO = r"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.chdir(sys.argv[2])
sys.path.insert(0, sys.argv[2])
import pygame
import main as mp

def make_game():
    game = mp.SpaceInvaders()
    game.set4Blocker()
    game.reset(0)
    return game

def step_group(game, steps=200):
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

name = sys.argv[1]
game = make_game()
grp = game.enemies
if name == "normal":
    mp.ROW_counter = 4
    cycles, dx = step_group(game)
    print("RESULT cycles=%d dx=%d counter=%d" % (cycles, dx, mp.ROW_counter))
elif name in ("stall0", "stall1", "range"):
    for e in list(grp):
        if e.row in (0, 1):
            grp.remove(e)
    assert grp.minRow == 2, grp.minRow
    mp.ROW_counter = 0 if name != "stall1" else 1
    cycles, dx = step_group(game)
    print("RESULT cycles=%d dx=%d counter=%d" % (cycles, dx, mp.ROW_counter))
elif name == "reset":
    mp.ROW_counter = -50
    game.reset(0)
    print("RESULT counter=%d" % mp.ROW_counter)
"""


def run_scenario(name):
    env = dict(os.environ)
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    proc = subprocess.run(
        [sys.executable, "-c", SCENARIO, name, REPO_ROOT],
        capture_output=True, text=True, env=env, timeout=60,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "scenario %s failed:\n%s" % (name, proc.stderr[-2000:]))
    result = {}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            for kv in line[len("RESULT "):].split():
                k, v = kv.split("=")
                result[k] = int(v)
    if not result:
        raise AssertionError("scenario %s produced no RESULT: %s"
                             % (name, proc.stdout[-500:]))
    return result


class MainRowCounterStallTest(unittest.TestCase):
    def test_fleet_moves_when_top_rows_wiped_and_counter_low(self):
        """上2行が全滅し minRow=2、カウンタが 0 の状態でも動き続ける。"""
        r = run_scenario("stall0")
        self.assertGreater(r["cycles"], 0)
        self.assertNotEqual(r["dx"], 0)

    def test_fleet_moves_when_counter_at_min_row_minus_one(self):
        """カウンタがちょうど minRow-1 の位置から始まっても止まらない。"""
        r = run_scenario("stall1")
        self.assertGreater(r["cycles"], 0)
        self.assertNotEqual(r["dx"], 0)

    def test_counter_stays_in_range(self):
        """包み直しが効いていれば、カウンタは大きく負に沈まない。"""
        r = run_scenario("range")
        self.assertGreaterEqual(r["counter"], -1)
        self.assertLessEqual(r["counter"], 4)

    def test_reset_restores_row_counter(self):
        """reset() で ROW_counter が初期値 4 に戻る（持ち越しの防止）。"""
        r = run_scenario("reset")
        self.assertEqual(r["counter"], 4)

    def test_normal_fleet_still_moves(self):
        """通常状態の動きが壊れていないことの確認。"""
        r = run_scenario("normal")
        self.assertGreater(r["cycles"], 0)
        self.assertNotEqual(r["dx"], 0)


if __name__ == "__main__":
    unittest.main()
