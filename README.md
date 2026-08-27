# 钢铁前线:霓虹坦克战(坦克大战 · pygame 版)

> 按 `坦克大战技术设计文档.md` 实现:经典坦克大战玩法 + 霓虹赛博视觉 + 恶搞语音包 + Roguelike 升级 + Boss 战。
> 玩法/美术/数值设计详见设计文档;代码入口架构:main() → GameState / Game / MenuController → 按 phase 分发。

## 环境依赖

| 依赖 | 版本(本机已装) | 说明 |
|------|------|------|
| Python | 3.13 | `python --version` 确认 |
| pygame | 2.6.1 | `pip install pygame` |
| numpy | 2.5.2 | `pip install numpy`(音频系统用 numpy 合成音效) |

```powershell
pip install pygame numpy
```

## 运行

在 `代码区` 目录下:

```powershell
python main.py
```

启动流程:`main()` → 初始化 pygame/mixer → 创建 `GameState`、`Game`、`MenuController` → 主循环按 `phase` 分发:
- `menu` / `level_upgrade` → 菜单分支(主菜单、三选一升级弹窗)
- 其余(`playing` / `paused` / `gameover` / `victory`)→ 游戏分支 `game.update()` + `game.render()`

## 操作

| 按键 | 功能 |
|------|------|
| WASD | 移动(鼠标瞄准炮管) |
| 鼠标右键 | 射击(子弹类型由坦克颜色决定) |
| 左 Shift | 大招(充能满 100) |
| Esc / P | 暂停 |
| 1 / 2 / 3 | 三选一升级弹窗快捷键 |

## 目录结构(代码区)

```
代码区/
├── main.py                 # 入口:main() + phase 分发主循环
├── core/                   # Game / GameState / Input / EventBus / constants
├── entities/               # Tank / Bullet / Wall / Pickup / Particle / Boss
├── systems/                # AI / Audio(numpy 合成音效) / Map / Wave / Upgrade
├── ui/                     # MenuController / HUDRenderer / ResultOverlay
└── utils/                  # 数学工具(角度/碰撞/加权随机)
```

素材库(自动定位,无需配置):
- `素材库/战胜语音/*.mp3` —— 胜利/Boss 击败随机播放(奶龙笑、黑手哥等)
- `素材库/战败语音/*.mp3` —— 失败随机播放(你干嘛哎呦、辣虾等)

存档:`代码区/savegame.json`(最高分、解锁进度)。

## 无窗口冒烟测试(可选)

```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
python -c "import main; main.main()"
```
