"""pgzero 版（pygamezero_spaceinvaders.py）の修正に対する回帰テスト。

pgzero の組み込み（Actor / screen / sounds / clock / keyboard / keys）は
pgzrun が実行時に差し込むものなので、ここでは実画像の大きさを持つ代役を
builtins に差し込んでからゲームモジュールを取り込む。代役の Actor は
実在しない画像名では読み込みに失敗するため、「無い画像を読みに行く」
種類の不具合もそのまま再現できる。
"""
import builtins
import importlib.util
import os
import sys
import types
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
sys.path.insert(0, REPO)

import pygame  # noqa: E402

# 画面は作らない（画像の読み込みと大きさの取得だけが目的なので）。
# ここで display.set_mode してしまうと、同じプロセスで後から取り込む
# spaceinvaders.py 側の画面生成（SCALED）と競合するため。
pygame.init()

_IMAGE_CACHE = {}


def _image_size(name):
    if name not in _IMAGE_CACHE:
        surf = pygame.image.load(os.path.join(REPO, "images", name + ".png"))
        _IMAGE_CACHE[name] = surf.get_size()
    return _IMAGE_CACHE[name]


class FakeActor:
    def __init__(self, image, pos=None, **kw):
        self.image = image
        self.width, self.height = _image_size(image)
        self.x, self.y = pos if pos else (0, 0)

    @property
    def pos(self):
        return (self.x, self.y)

    @pos.setter
    def pos(self, value):
        self.x, self.y = value

    def _rect(self):
        return pygame.Rect(self.x - self.width // 2, self.y - self.height // 2,
                           self.width, self.height)

    def collidelist(self, others):
        r = self._rect()
        for i, o in enumerate(others):
            if r.colliderect(o._rect()):
                return i
        return -1

    def draw(self):
        pass


class _FakeSound:
    def play(self, *a, **k): pass
    def stop(self, *a, **k): pass


class _FakeSounds:
    def __getattr__(self, name):
        return _FakeSound()


class FakeClock:
    def __init__(self):
        self.scheduled = []

    def schedule_unique(self, fn, delay):
        self.scheduled.append((fn, delay))

    def unschedule(self, fn):
        pass


class _FakeDraw:
    def __getattr__(self, name):
        return lambda *a, **k: None


class _FakeScreen:
    draw = _FakeDraw()

    def blit(self, *a, **k): pass
    def fill(self, *a, **k): pass


class _FakeKeyboard:
    def __getattr__(self, name):
        return False


FAKE_CLOCK = FakeClock()

builtins.Actor = FakeActor
builtins.screen = _FakeScreen()
builtins.sounds = _FakeSounds()
builtins.clock = FAKE_CLOCK
builtins.keyboard = _FakeKeyboard()
builtins.keys = types.SimpleNamespace(SPACE="SPACE", A="A", D="D",
                                      LEFT="LEFT", RIGHT="RIGHT")
builtins.Rect = pygame.Rect

# pgzrun だけは代役にする（本体はテストでは使わない）
sys.modules["pgzrun"] = types.SimpleNamespace(go=lambda *a, **k: None)


def load_game():
    spec = importlib.util.spec_from_file_location(
        "pgzero_game", os.path.join(REPO, "pygamezero_spaceinvaders.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPgzeroFixes(unittest.TestCase):
    def setUp(self):
        FAKE_CLOCK.scheduled.clear()
        self.g = load_game()
        # メニューで SPACE を押してゲーム開始
        self.g.on_key_down(builtins.keys.SPACE)

    def test_enemies_use_scaled_assets(self):
        g = self.g
        self.assertEqual(len(g.enemies), 50)
        for e in g.enemies:
            self.assertTrue(e.image.endswith("_40"), e.image)
            self.assertEqual((e.width, e.height), (40, 35))

    def test_lives_icons_use_small_ship(self):
        for icon in self.g.lives_icons:
            self.assertEqual((icon.width, icon.height), (23, 23))

    def test_mystery_scheduled_on_game_start(self):
        fns = [fn for fn, delay in FAKE_CLOCK.scheduled]
        self.assertIn(self.g.spawn_mystery_ship, fns)

    def test_mystery_spawn_and_kill(self):
        g = self.g
        g.spawn_mystery_ship()
        self.assertIsNotNone(g.mystery_ship)
        self.assertEqual(g.mystery_ship.width, 80)
        bullet = FakeActor('laser', (g.mystery_ship.x, g.mystery_ship.y))
        g.bullets.append(bullet)
        before = g.game.score
        g.check_collisions()  # 例外なく処理できること（赤い爆発画像が実在）
        self.assertIsNone(g.mystery_ship)
        self.assertGreater(g.game.score, before)
        self.assertTrue(any(ex.image == 'explosionred_40' for ex in g.explosions))

    def test_fleet_stays_on_screen(self):
        g = self.g
        max_y_seen = max(e.y for e in g.enemies)
        for _ in range(600):
            g.update_enemies(1.0)  # dt を大きくして毎回1ステップ進める
            for e in g.enemies:
                self.assertGreaterEqual(e.x - 20, 0)
                self.assertLessEqual(e.x + 20, 800)
            max_y_seen = max(max_y_seen, max(e.y for e in g.enemies))
        # 端で下降に転じたこと（y が初期配置より下がっている）
        self.assertGreater(max_y_seen, 95 + 4 * 45)

    def test_enemy_shooter_is_bottom_of_column(self):
        g = self.g
        g.enemy_data['last_shot'] = 999.0
        g.update_enemy_shooting(0.0)
        self.assertEqual(len(g.enemy_bullets), 1)
        eb = g.enemy_bullets[0]
        same_column = [e for e in g.enemies if e.x == eb.x]
        self.assertTrue(same_column)
        self.assertEqual(eb.y - 20, max(e.y for e in same_column))


if __name__ == "__main__":
    unittest.main()
