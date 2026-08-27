# -*- coding: utf-8 -*-
"""
音频系统
"""
import os
import random
import pygame


class AudioSystem:
    def __init__(self, assets_root=None):
        self.enabled = True
        self.volume_sfx = 0.7
        self.volume_voice = 0.9
        self.volume_bgm = 0.4
        self._mixer_ok = pygame.mixer.get_init() is not None
        self.assets_root = assets_root or self._find_assets_root()
        self.victory_voices = self._load_voices("战胜语音")
        self.defeat_voices = self._load_voices("战败语音")
        # BGM (愤怒的小鸟) 循环播放; 语音播放时暂停, 播完恢复
        self.bgm_path = None
        self._bgm_started = False
        self._bgm_paused_by_voice = False
        self._voice_channel = None
        # Boss BGM 状态
        self._boss_bgm_active = False  # Boss BGM 是否正在播放
        self._boss_bgm_path = None
        self._boss_bgm_listener = None  # Boss BGM 播完回调 (用于 Boss 15 判定失败)
        # 无条件初始化 (素材目录缺失时不能 AttributeError 崩掉 Boss 关)
        self._boss_bgm_paths = {}
        self.boss_voices = []
        self.kangaroo_voices = []
        self.boss_voice_pools = {}
        if self._mixer_ok:
            try:
                pygame.mixer.set_reserved(1)  # 保留 channel 0 给语音
            except Exception:
                pass
        if self.assets_root:
            import os as _os
            p = _os.path.join(self.assets_root, "音效", "愤怒的小鸟.mp3")
            if _os.path.exists(p):
                self.bgm_path = p
            # 预加载 Boss BGM 路径
            boss_dir = _os.path.join(self.assets_root, "首领敌人", "首领敌人出场音频")
            if _os.path.exists(boss_dir):
                for i in range(1, 6):
                    bp = _os.path.join(boss_dir, f"{i}.mp3")
                    if _os.path.exists(bp):
                        self._boss_bgm_paths[i] = bp
            # Boss 语音池: 华强(5) + 美团袋鼠(4), 按关键词调用
            self.boss_voices = self._load_voices(
                _os.path.join("首领敌人", "华强语音"))
            self.kangaroo_voices = self._load_voices(
                _os.path.join("首领敌人", "美团袋鼠语音"))
            self.boss_voice_pools = {4: self.kangaroo_voices,
                                     5: self.boss_voices}
        # BGM 压低声 (语音播放期间自动压低 BGM, 播完恢复)
        self._bgm_ducked = False

    def start_bgm(self):
        if not self._mixer_ok or not self.bgm_path:
            return
        try:
            pygame.mixer.music.load(self.bgm_path)
            pygame.mixer.music.set_volume(self.volume_bgm)
            pygame.mixer.music.play(loops=-1)
            self._bgm_started = True
            self._bgm_paused_by_voice = False
        except Exception as e:
            print(f"[Audio] BGM 启动失败: {e}")

    def stop_bgm(self):
        if not self._mixer_ok:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._bgm_started = False
        self._bgm_paused_by_voice = False
        self._bgm_ducked = False
        # 同时清掉 Boss BGM 状态, 防止停表后 update 误触发"播完"回调
        self._boss_bgm_active = False
        self._boss_bgm_listener = None

    def _duck_bgm(self):
        """语音播放时把 BGM 压低到 15%, 播完恢复 (不暂停, 手感更顺)"""
        if self._bgm_ducked or not self._mixer_ok:
            return
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(self.volume_bgm * 0.15)
                self._bgm_ducked = True
        except Exception:
            pass

    def _restore_bgm_volume(self):
        if not self._bgm_ducked:
            return
        try:
            pygame.mixer.music.set_volume(self.volume_bgm)
        except Exception:
            pass
        self._bgm_ducked = False

    def pause_bgm(self):
        if not self._mixer_ok or not self._bgm_started:
            return
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass

    def resume_bgm(self):
        if not self._mixer_ok or not self._bgm_started:
            return
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass

    def play_boss_bgm(self, boss_index, on_end=None):
        """播放Boss BGM (暂停普通BGM, 播放完后根据on_end回调决定行为)
        on_end: 'resume_bgm' 恢复普通BGM (Boss 5/10)
                'game_over' 触发游戏失败 (Boss 15)
                None 则仅恢复普通BGM
        """
        if not self._mixer_ok:
            return
        path = self._boss_bgm_paths.get(boss_index)
        if not path:
            # 没有Boss BGM文件 -> 直接恢复普通BGM
            if on_end != 'game_over':
                self.resume_bgm()
            return
        try:
            # 先暂停普通BGM
            pygame.mixer.music.stop()
            self._bgm_started = False
            self._bgm_ducked = False
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume_bgm)
            pygame.mixer.music.play(loops=0)  # 只放一次
            self._boss_bgm_active = True
            self._boss_bgm_path = path
            self._boss_bgm_listener = on_end
        except Exception as e:
            print(f"[Audio] Boss BGM 播放失败: {e}")
            if on_end != 'game_over':
                self.start_bgm()

    def stop_boss_bgm_and_resume(self):
        """停止Boss BGM并恢复普通BGM (用于Boss 5/10被击败后)"""
        if not self._mixer_ok:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._boss_bgm_active = False
        self._boss_bgm_path = None
        self._boss_bgm_listener = None
        self.start_bgm()

    def stop_voice_resume_bgm(self):
        """停止当前语音并恢复 BGM (用于进入下一关)"""
        if self._voice_channel is not None:
            try:
                self._voice_channel.stop()
            except Exception:
                pass
            self._voice_channel = None
        self._bgm_paused_by_voice = False
        self._restore_bgm_volume()
        self.resume_bgm()

    def update(self):
        """每帧调用: 语音播完后自动恢复 BGM; Boss BGM 播完触发回调"""
        # 普通 BGM 语音恢复
        if self._voice_channel is not None:
            try:
                busy = self._voice_channel.get_busy()
            except Exception:
                busy = False
            if not busy:
                self._voice_channel = None
                if self._bgm_paused_by_voice:
                    self._bgm_paused_by_voice = False
                    self.resume_bgm()
                if self._bgm_ducked:
                    self._restore_bgm_volume()
        # Boss BGM 播放结束检测
        if self._boss_bgm_active:
            try:
                if not pygame.mixer.music.get_busy():
                    # Boss BGM 播放结束
                    self._boss_bgm_active = False
                    listener = self._boss_bgm_listener
                    self._boss_bgm_listener = None
                    if listener == 'game_over':
                        # Boss 15: BGM 播完 -> 游戏失败
                        if hasattr(self, '_on_boss_bgm_end'):
                            self._on_boss_bgm_end('game_over')
                    elif listener == 'resume_bgm':
                        self.start_bgm()
            except Exception:
                pass

    def _play_voice_on_reserved(self, snd, pause_bgm, volume=None):
        if not self._mixer_ok:
            return
        try:
            ch = pygame.mixer.Channel(0)
            ch.set_volume(self.volume_voice if volume is None else volume)
            if pause_bgm:
                self.pause_bgm()
                self._restore_bgm_volume()
            else:
                self._duck_bgm()
            ch.play(snd)
            self._voice_channel = ch
            if pause_bgm:
                self._bgm_paused_by_voice = True
        except Exception as e:
            print(f"[Audio] 播放语音异常: {e}")

    def _find_assets_root(self):
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, "..", "..", "..", "素材库"),
            os.path.join(here, "..", "..", "素材库"),
            os.path.join(here, "素材库"),
            os.path.abspath(os.path.join(here, "..", "..", "..", "..", "素材库")),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def _load_voices(self, sub_dir_name):
        voices = []
        if not self.assets_root:
            return voices
        d = os.path.join(self.assets_root, sub_dir_name)
        if not os.path.exists(d):
            return voices
        exts = (".mp3", ".wav", ".ogg")
        try:
            for f in sorted(os.listdir(d)):
                if f.lower().endswith(exts):
                    full = os.path.join(d, f)
                    try:
                        if not self._mixer_ok:
                            continue
                        snd = pygame.mixer.Sound(full)
                        voices.append((snd, f))
                    except Exception as e:
                        print(f"[Audio] 加载失败 {full}: {e}")
        except Exception as e:
            print(f"[Audio] 扫描 {d} 异常: {e}")
        return voices

    def play_sfx(self, name):
        if not self.enabled or not self._mixer_ok:
            return
        try:
            if name == "shoot":
                self._beep(880, 40, vol=0.25, wave="square")
            elif name == "explosion":
                self._noise(350, vol=0.5)
            elif name == "hit":
                self._beep(260, 60, vol=0.3, wave="sawtooth")
            elif name == "pickup":
                self._beep(1200, 80, vol=0.3)
            elif name == "boss_shoot":
                self._beep(160, 90, vol=0.4, wave="sawtooth")
            elif name == "victory":
                self._melody([523, 659, 784, 1047], 180)
            elif name == "defeat":
                self._melody([330, 294, 262, 196], 260)
            elif name == "combo":
                self._melody([660, 990], 90)
            elif name == "button":
                self._beep(660, 30, vol=0.2)
        except Exception as e:
            pass

    def play_boss_voice(self, keyword, boss_index=5, pause_bgm=False, volume=1.0):
        """播放Boss专属语音 (按文件名关键词匹配); 无匹配则静默跳过
        boss_index: 4=美团袋鼠, 5=华强
        """
        if not self._mixer_ok:
            return
        pool = self.boss_voice_pools.get(boss_index) or self.boss_voices
        matches = [(s, f) for s, f in pool if keyword in f]
        if not matches:
            return
        try:
            snd, _fname = random.choice(matches)
            self._play_voice_on_reserved(snd, pause_bgm, volume=volume)
        except Exception:
            pass

    def play_random_voice(self, victory=True, force=False, pause_bgm=False):
        if (not self.enabled and not force) or not self._mixer_ok:
            return
        pool = self.victory_voices if victory else self.defeat_voices
        if not pool:
            self.play_sfx("victory" if victory else "defeat")
            return
        try:
            snd, fname = random.choice(pool)
            self._play_voice_on_reserved(snd, pause_bgm)
        except Exception as e:
            print(f"[Audio] 播放语音异常: {e}")

    def play_voice_for_tank_color(self, color, victory=True, pause_bgm=True):
        """按坦克颜色播放指定语音; 无对应文件则回退随机语音"""
        from core.constants import TANK_COLOR_CONFIG
        if not self.enabled or not self._mixer_ok:
            return
        cfg = TANK_COLOR_CONFIG.get(color)
        if not cfg:
            self.play_random_voice(victory=victory, pause_bgm=pause_bgm)
            return
        key = cfg["victory_voice"] if victory else cfg["defeat_voice"]
        if not key:
            # 该颜色未配置语音 (如蓝色) -> 回退合成音效
            self.play_sfx("victory" if victory else "defeat")
            return
        pool = self.victory_voices if victory else self.defeat_voices
        match = None
        for snd, fname in pool:
            if key in fname:
                match = snd
                break
        if match is None:
            self.play_random_voice(victory=victory, pause_bgm=pause_bgm)
            return
        self._play_voice_on_reserved(match, pause_bgm)

    def _beep(self, freq, dur_ms, vol=0.3, wave="sine"):
        try:
            import numpy as np
            sr = 44100
            n = int(sr * dur_ms / 1000)
            if n <= 0:
                return
            t = np.linspace(0, dur_ms / 1000, n, False)
            if wave == "sine":
                wv = np.sin(2 * np.pi * freq * t)
            elif wave == "square":
                wv = np.sign(np.sin(2 * np.pi * freq * t))
            else:
                wv = 2 * (t * freq - np.floor(0.5 + t * freq))
            audio = (wv * vol * 32767).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            snd = pygame.sndarray.make_sound(stereo)
            snd.set_volume(self.volume_sfx)
            snd.play()
        except Exception:
            pass

    def _noise(self, dur_ms, vol=0.5):
        try:
            import numpy as np
            sr = 44100
            n = int(sr * dur_ms / 1000)
            noise = np.random.uniform(-1, 1, n)
            env = np.exp(-np.linspace(0, 5, n))
            audio = (noise * env * vol * 32767).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            snd = pygame.sndarray.make_sound(stereo)
            snd.set_volume(self.volume_sfx)
            snd.play()
        except Exception:
            pass

    def _melody(self, freqs, note_ms):
        """numpy 一次合成整段旋律并播放(不阻塞主循环)。"""
        if not self._mixer_ok:
            return
        try:
            import numpy as np
            sr = 44100
            n = int(sr * note_ms / 1000)
            t = np.linspace(0, note_ms / 1000, n, False)
            env = np.minimum(np.linspace(0, 1, n) * 8,
                             np.linspace(1, 0, n) * 3)
            parts = []
            gap = np.zeros(int(sr * 0.04))
            for f in freqs:
                wv = np.sin(2 * np.pi * f * t) * env
                parts.append(wv)
                parts.append(gap)
            audio = (np.concatenate(parts) * 0.3 * 32767).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            snd = pygame.sndarray.make_sound(stereo)
            snd.set_volume(self.volume_sfx)
            snd.play()
        except Exception:
            pass
