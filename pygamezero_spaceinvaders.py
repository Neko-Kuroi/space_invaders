import pgzrun
from random import choice, randint

# --- 設定 ---
WIDTH = 800
HEIGHT = 600
TITLE = "Space Invaders - Enhanced Edition"

# 定数
ENEMY_MOVE_DOWN = 35
ENEMY_DEFAULT_Y = 65
SHIP_SPEED = 6
BULLET_SPEED = 12
ENEMY_BULLET_SPEED = 5
MAX_PLAYER_BULLETS = 3
SHOOT_COOLDOWN = 0.2

# --- ゲーム状態管理 ---
class State:
    def __init__(self):
        self.high_score = 0
        self.reset_all()

    def reset_all(self):
        self.score = 0
        self.lives = 3
        self.round = 1
        self.status = "MENU"  # MENU, PLAYING, EXPLODING, NEXTROUND, GAMEOVER
        self.timer = 0
        self.shoot_cooldown = 0
        self.invincible_timer = 0
        
    def add_score(self, points):
        self.score += points
        if self.score > self.high_score:
            self.high_score = self.score

game = State()

# --- オブジェクト管理 ---
ship = Actor('ship', (400, 540))
ship.scale = 1.0
bullets = []
enemy_bullets = []
enemies = []
explosions = []
lives_icons = []
mystery_ship = None

# 敵グループの移動制御
enemy_data = {
    'direction': 1,
    'move_count': 0,
    'last_move': 0,
    'last_shot': 0
}

# --- 初期化関数 ---
def init_level():
    """レベル初期化"""
    enemies.clear()
    bullets.clear()
    enemy_bullets.clear()
    explosions.clear()
    
    enemy_data['move_count'] = 0
    enemy_data['direction'] = 1
    enemy_data['last_move'] = 0
    enemy_data['last_shot'] = 0
    
    # 敵を配置
    for row in range(5):
        for col in range(10):
            if row == 0: 
                img = 'enemy1_1'
            elif row in [1, 2]: 
                img = 'enemy2_1'
            else: 
                img = 'enemy3_1'
            
            enemy = Actor(img)
            enemy.row = row
            enemy.col = col
            enemy.frame = 1
            enemy.pos = (157 + (col * 50), ENEMY_DEFAULT_Y + (row * 45))
            enemies.append(enemy)
    
    update_lives_icons()
    
    # ミステリーシップのスケジュール
    schedule_mystery_ship()

def update_lives_icons():
    """残機アイコンの更新"""
    lives_icons.clear()
    for i in range(game.lives):
        icon = Actor('ship', (715 + (i * 27), 15))
        icon.scale = 0.5
        lives_icons.append(icon)

def schedule_mystery_ship():
    """ミステリーシップの出現スケジュール"""
    if game.status == "PLAYING":
        delay = randint(15, 30)
        clock.schedule_unique(spawn_mystery_ship, delay)

def spawn_mystery_ship():
    """ミステリーシップの生成"""
    global mystery_ship
    if game.status == "PLAYING" and mystery_ship is None:
        mystery_ship = Actor('mystery', (-80, 45))
        mystery_ship.direction = 1
        mystery_ship.speed = 2
        sounds.mysteryentered.play()

# --- 描画 (draw) ---
def draw():
    screen.blit('background', (0, 0))
    
    if game.status == "MENU":
        draw_menu()
        
    elif game.status in ["PLAYING", "EXPLODING", "NEXTROUND"]:
        draw_game()

    elif game.status == "GAMEOVER":
        draw_game_over()

def draw_menu():
    """メニュー画面の描画"""
    screen.draw.text("SPACE INVADERS", center=(WIDTH/2, 160), fontsize=70, color="white", shadow=(2,2))
    screen.draw.text("PRESS SPACE TO START", center=(WIDTH/2, 280), fontsize=35, color="green")
    
    # スコアテーブル
    screen.draw.text("= 30 pts", (450, 320), fontsize=25, color="purple")
    screen.draw.text("= 20 pts", (450, 370), fontsize=25, color="blue")
    screen.draw.text("= 10 pts", (450, 420), fontsize=25, color="green")
    screen.draw.text("= ??? pts", (450, 470), fontsize=25, color="red")
    
    # サンプル敵を描画
    Actor('enemy1_1', (400, 330)).draw()
    Actor('enemy2_1', (400, 380)).draw()
    Actor('enemy3_1', (400, 430)).draw()
    mystery_sample = Actor('mystery', (380, 480))
    mystery_sample.scale = 0.8
    mystery_sample.draw()
    
    if game.high_score > 0:
        screen.draw.text(f"HIGH SCORE: {game.high_score}", center=(WIDTH/2, 520), 
                        fontsize=30, color="yellow")

def draw_game():
    """ゲーム画面の描画"""
    # 自機（無敵時は点滅）
    if game.status != "EXPLODING":
        if game.invincible_timer <= 0 or int(game.invincible_timer * 10) % 2 == 0:
            ship.draw()
    
    # 敵
    for e in enemies: 
        e.draw()
    
    # 弾丸
    for b in bullets: 
        b.draw()
    for eb in enemy_bullets: 
        eb.draw()
    
    # ミステリーシップ
    if mystery_ship:
        mystery_ship.draw()
    
    # 爆発
    for ex in explosions: 
        ex.draw()
    
    # UI
    screen.draw.text(f"SCORE: {game.score}", (15, 8), fontsize=28, color="green")
    screen.draw.text(f"ROUND: {game.round}", center=(WIDTH/2, 12), fontsize=28, color="white")
    screen.draw.text("LIVES:", (640, 8), fontsize=28, color="white")
    
    for icon in lives_icons: 
        icon.draw()

    # ネクストラウンド表示
    if game.status == "NEXTROUND":
        screen.draw.filled_rect(Rect(150, 250, 500, 100), (0, 0, 0, 200))
        screen.draw.text(f"ROUND {game.round} CLEAR!", center=(WIDTH/2, HEIGHT/2), 
                        fontsize=60, color="yellow", shadow=(3,3))

def draw_game_over():
    """ゲームオーバー画面の描画"""
    screen.blit('background', (0, 0))
    screen.draw.text("GAME OVER", center=(WIDTH/2, 200), fontsize=90, color="red", shadow=(4,4))
    screen.draw.text(f"FINAL SCORE: {game.score}", center=(WIDTH/2, 320), fontsize=45, color="white")
    
    if game.score == game.high_score and game.score > 0:
        screen.draw.text("NEW HIGH SCORE!", center=(WIDTH/2, 380), fontsize=40, color="yellow")
    elif game.high_score > 0:
        screen.draw.text(f"HIGH SCORE: {game.high_score}", center=(WIDTH/2, 380), fontsize=35, color="green")
    
    screen.draw.text("PRESS SPACE TO CONTINUE", center=(WIDTH/2, 480), fontsize=30, color="white")

# --- 更新 (update) ---
def update(dt):
    """メインアップデート"""
    if game.status == "MENU" or game.status == "GAMEOVER":
        return

    if game.status == "PLAYING":
        update_ship(dt)
        update_bullets()
        update_enemies(dt)
        update_mystery_ship(dt)
        update_enemy_shooting(dt)
        check_collisions()
        
        # 無敵時間の減少
        if game.invincible_timer > 0:
            game.invincible_timer -= dt
            
        # 射撃クールダウン
        if game.shoot_cooldown > 0:
            game.shoot_cooldown -= dt

    # 共通：爆発アニメーションの更新
    for ex in explosions[:]:
        ex.timer -= dt
        if ex.timer <= 0:
            explosions.remove(ex)

def update_ship(dt):
    """自機の更新"""
    # 移動
    if keyboard.a or keyboard.left:
        ship.x = max(30, ship.x - SHIP_SPEED)
    if keyboard.d or keyboard.right:
        ship.x = min(WIDTH - 30, ship.x + SHIP_SPEED)

def update_bullets():
    """弾丸の更新"""
    for b in bullets[:]:
        b.y -= BULLET_SPEED
        if b.y < 0: 
            bullets.remove(b)
        
    for eb in enemy_bullets[:]:
        eb.y += ENEMY_BULLET_SPEED
        if eb.y > HEIGHT: 
            enemy_bullets.remove(eb)

def update_mystery_ship(dt):
    """ミステリーシップの更新"""
    global mystery_ship
    if mystery_ship:
        mystery_ship.x += mystery_ship.speed * mystery_ship.direction
        
        # 画面外に出たら削除
        if mystery_ship.x > WIDTH + 100 or mystery_ship.x < -100:
            mystery_ship = None
            schedule_mystery_ship()

def update_enemies(dt):
    """敵の更新"""
    enemy_data['last_move'] += dt
    
    # 敵が減るほど速くなる（難易度調整）
    enemy_count = len(enemies)
    if enemy_count <= 1:
        move_interval = 0.05
    elif enemy_count <= 10:
        move_interval = 0.15
    elif enemy_count <= 20:
        move_interval = 0.25
    else:
        move_interval = 0.35
    
    # ラウンドが進むと速くなる
    move_interval = max(0.03, move_interval - (game.round - 1) * 0.02)
    
    if enemy_data['last_move'] > move_interval:
        enemy_data['last_move'] = 0
        do_move_down = False
        
        # 方向転換判定
        if enemy_data['move_count'] >= 30:
            enemy_data['direction'] *= -1
            enemy_data['move_count'] = 0
            do_move_down = True
        
        for e in enemies:
            if do_move_down:
                e.y += ENEMY_MOVE_DOWN
            else:
                e.x += 10 * enemy_data['direction']
            
            # アニメーション切り替え
            e.frame = 2 if e.frame == 1 else 1
            e.image = f"enemy{get_enemy_type(e.row)}_{e.frame}"
            
            # 敗北条件：下まで到達
            if e.y >= 540:
                game.status = "GAMEOVER"
                sounds.shipexplosion.play()

        if not do_move_down:
            enemy_data['move_count'] += 1

def update_enemy_shooting(dt):
    """敵の射撃"""
    enemy_data['last_shot'] += dt
    
    # ラウンドが進むほど射撃頻度が上がる
    shot_interval = max(0.3, 0.8 - (game.round - 1) * 0.05)
    
    if enemy_data['last_shot'] > shot_interval and enemies:
        enemy_data['last_shot'] = 0
        shooter = choice(enemies)
        eb = Actor('enemylaser', (shooter.x, shooter.y + 20))
        enemy_bullets.append(eb)

def get_enemy_type(row):
    """行から敵のタイプを取得"""
    if row == 0: return "1"
    if row in [1, 2]: return "2"
    return "3"

def get_enemy_score(row):
    """行からスコアを取得"""
    if row == 0: return 30
    if row in [1, 2]: return 20
    return 10

# --- イベント・衝突判定 ---
def on_key_down(key):
    """キー入力処理"""
    if game.status == "MENU":
        if key == keys.SPACE:
            game.reset_all()
            init_level()
            game.status = "PLAYING"
            
    elif game.status == "GAMEOVER":
        if key == keys.SPACE:
            game.status = "MENU"
            
    elif game.status == "PLAYING":
        if key == keys.SPACE and game.shoot_cooldown <= 0:
            if len(bullets) < MAX_PLAYER_BULLETS:
                bullet = Actor('laser', (ship.x, ship.y - 30))
                bullets.append(bullet)
                sounds.shoot.play()
                game.shoot_cooldown = SHOOT_COOLDOWN

def check_collisions():
    """衝突判定"""
    # 自機弾 vs 敵
    for b in bullets[:]:
        idx = b.collidelist(enemies)
        if idx != -1:
            e = enemies.pop(idx)
            bullets.remove(b)
            add_explosion(e.x, e.y, get_explosion_color(e.row))
            points = get_enemy_score(e.row)
            game.add_score(points)
            sounds.invaderkilled.play()
            
            # 全滅チェック
            if not enemies:
                game.status = "NEXTROUND"
                clock.schedule_unique(start_next_round, 2.5)
    
    # 自機弾 vs ミステリーシップ
    global mystery_ship
    if mystery_ship and bullets:
        idx = mystery_ship.collidelist(bullets)
        if idx != -1:
            bullets.pop(idx)
            bonus = choice([50, 100, 150, 200, 300])
            game.add_score(bonus)
            add_explosion(mystery_ship.x, mystery_ship.y, 'red')
            add_score_popup(mystery_ship.x, mystery_ship.y, bonus)
            sounds.mysterykilled.play()
            mystery_ship = None
            schedule_mystery_ship()

    # 敵弾 vs 自機（無敵時間中は無視）
    if game.invincible_timer <= 0 and ship.collidelist(enemy_bullets) != -1:
        handle_ship_death()

def get_explosion_color(row):
    """敵の行から爆発の色を決定"""
    if row == 0: return 'purple'
    if row in [1, 2]: return 'blue'
    return 'green'

def handle_ship_death():
    """自機の死亡処理"""
    game.lives -= 1
    add_explosion(ship.x, ship.y, 'purple')
    sounds.shipexplosion.play()
    enemy_bullets.clear()
    bullets.clear()
    update_lives_icons()
    
    if game.lives <= 0:
        game.status = "GAMEOVER"
    else:
        game.status = "EXPLODING"
        clock.schedule_unique(respawn_ship, 2.0)

def add_explosion(x, y, color):
    """爆発エフェクトの追加"""
    ex = Actor(f'explosion{color}', (x, y))
    ex.timer = 0.4
    explosions.append(ex)

def add_score_popup(x, y, score):
    """スコアポップアップの追加"""
    popup = Actor('laser', (x, y))  # ダミーアクター
    popup.score = score
    popup.timer = 1.5
    popup.draw = lambda: screen.draw.text(
        str(score), 
        center=(popup.x, popup.y), 
        fontsize=30, 
        color="yellow",
        shadow=(2, 2)
    )
    explosions.append(popup)

def respawn_ship():
    """自機の復活"""
    ship.pos = (400, 540)
    game.invincible_timer = 3.0  # 3秒間無敵
    game.status = "PLAYING"

def start_next_round():
    """次のラウンド開始"""
    game.round += 1
    init_level()
    ship.pos = (400, 540)
    game.invincible_timer = 2.0
    game.status = "PLAYING"

# --- ゲーム開始 ---
pgzrun.go()
