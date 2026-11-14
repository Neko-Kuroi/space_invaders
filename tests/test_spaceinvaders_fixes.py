"""spaceinvaders.py の点検で見つけた不具合に対する回帰テスト。

実行方法（リポジトリのルートで）:
    python -m unittest tests.test_spaceinvaders_fixes -v
pygame が必要。画面と音は SDL のダミードライバで代替する。
"""
import os
import subprocess
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)  # 素材の相対パス解決のため、import 前にルートへ移る
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pygame  # noqa: E402
import spaceinvaders as si  # noqa: E402


def make_game():
    game = si.SpaceInvaders()
    game.set4Blocker()
    game.reset(0)
    return game


class KeyUpResetTest(unittest.TestCase):
    """中-1: KEYUP 判定 `e.key == K_d or K_a` が常に真だった件。"""

    def setUp(self):
        self.game = make_game()
        self.orig_get = pygame.event.get

    def tearDown(self):
        si.event.get = self.orig_get

    def send_keyup(self, key_code):
        ev = pygame.event.Event(pygame.KEYUP, key=key_code)
        si.event.get = lambda *a, **k: [ev]
        self.game.check_input()

    def test_unrelated_keyup_does_not_reset_vx(self):
        self.game.player.vx = 999
        self.send_keyup(pygame.K_z)
        self.assertEqual(self.game.player.vx, 999)

    def test_movement_keyup_resets_vx(self):
        self.game.player.vx = 999
        self.send_keyup(pygame.K_d)
        self.assertEqual(self.game.player.vx, si.SHIP_VX)


class RandomBottomTest(unittest.TestCase):
    """中-2: 生きている列が空だと random_bottom が IndexError だった件。"""

    def setUp(self):
        self.game = make_game()

    def test_random_bottom_with_no_alive_columns_returns_none(self):
        self.game.enemies._aliveColumns = []
        self.assertIsNone(self.game.enemies.random_bottom())

    def test_make_enemies_shoot_without_shooter_does_nothing(self):
        self.game.enemies._aliveColumns = []
        old_level = si.LEVEL
        si.LEVEL = 10
        try:
            self.game.timer = 0  # 発射間隔を満たした状態にする
            self.game.make_enemies_shoot()
        finally:
            si.LEVEL = old_level
        self.assertEqual(len(self.game.enemyBullets), 0)


class RemoveInternalBookkeepingTest(unittest.TestCase):
    """remove_internal 経由の台帳更新（EnemiesGroup.kill）が壊れていないことの確認。

    点検報告書の初版では、この kill を「Group.kill() の上書きで未使用」と
    書いたが、両方とも誤りだった（remove_internal から使われている。
    また pygame の Group には kill メソッド自体が無い）。そのため修正対象
    から外し、ここでは本来の後片付けが効くことだけを固定する。
    """

    def setUp(self):
        self.game = make_game()

    def test_killing_a_full_column_updates_the_ledger(self):
        enemies = self.game.enemies
        column0 = [enemies.enemies[row][0] for row in range(enemies.rows)]
        for enemy in column0:
            enemy.kill()
        self.assertEqual(len(enemies), 45)
        self.assertTrue(all(enemies.enemies[row][0] is None
                            for row in range(enemies.rows)))
        self.assertNotIn(0, enemies._aliveColumns)
        self.assertEqual(enemies._leftAliveColumn, 1)


class UpdateSpeedEmptyTest(unittest.TestCase):
    """update_speed: 空グループで状態を書き換えてしまっていた件。"""

    def setUp(self):
        self.game = make_game()

    def test_update_speed_on_empty_group_keeps_state(self):
        group = si.EnemiesGroup(10, 5)
        group.minRow = 2
        group.maxRow = 3
        group.moveTime = 123
        group.update_speed()
        self.assertEqual(group.moveTime, 123)
        self.assertEqual(group.minRow, 2)
        self.assertEqual(group.maxRow, 3)


class GameOverTimerTest(unittest.TestCase):
    """create_game_over が敵の射撃と共用の self.timer を基準にしていた件。"""

    def setUp(self):
        self.game = make_game()

    def test_game_over_sets_its_own_timer_on_player_death(self):
        # 残機を全て使い切った状態で敵弾を自機に当てる
        for life in (self.game.life1, self.game.life2, self.game.life3):
            life.kill()
        bullet = si.Bullet(self.game.player.rect.x, self.game.player.rect.y,
                           1, 5, 'enemylaser', 'center')
        self.game.enemyBullets.add(bullet)
        before = pygame.time.get_ticks()
        self.game.check_collisions()
        self.assertTrue(self.game.gameOver)
        timer = getattr(self.game, "gameOverTimer", None)
        self.assertIsNotNone(timer)
        self.assertGreaterEqual(timer, before - 100)
        self.assertLessEqual(timer, pygame.time.get_ticks() + 100)

    def test_create_game_over_ignores_stale_shared_timer(self):
        now = pygame.time.get_ticks()
        self.game.timer = now - 10000  # 最後の射撃から大きく経った想定
        self.game.gameOverTimer = now  # ゲームオーバーになったのは今
        self.game.mainScreen = False
        self.game.create_game_over(now)
        self.assertFalse(self.game.mainScreen)


class ImportUseTest(unittest.TestCase):
    """中-3: import して使うと reset() が NameError（全域 game 依存）だった件。

    きれいなプロセスで確かめる。
    """

    def test_import_instantiate_reset_in_fresh_process(self):
        code = (
            "import spaceinvaders as si\n"
            "g = si.SpaceInvaders()\n"
            "g.reset(0)\n"
            "assert len(g.enemies) == 50, len(g.enemies)\n"
            "print('ok')\n"
        )
        env = dict(os.environ)
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
