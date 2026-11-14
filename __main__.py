# pygbag（pygame-web）の実行入口。
#
# 以前はここにゲーム本体の写しが置かれていたが、main.py と内容がずれて
# 壊れてしまった（227行目で文が途切れていた）ため、本体は main.py に
# 一本化し、ここはそれを起動するだけの薄い入口にした。
# pygbag は apk の中の __main__.py を実行するので、このファイルが要る。
import asyncio

import main as _main
from main import SpaceInvaders

# main.py 内の各クラスは、全域の game 経由で本体を参照する
_main.game = SpaceInvaders()

if __name__ == '__main__':
    asyncio.run(_main.game.main())
