"""Local soundtrack and short event cues. The simulation owns all timing."""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parents[1] / "assets" / "audio"
EFFECTS = {"player_slash": "slash", "player_throw_shuriken": "throw", "player_dash": "dash",
           "enemy_hit": "hit", "player_hit": "hurt", "reward_confirmed": "scroll"}


class Audio:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init()
            for name in ("lantern", *EFFECTS.values()):
                sound = pygame.mixer.Sound(ROOT / (name + ".wav"))
                sound.set_volume(.28 if name == "lantern" else .52)
                self.sounds[name] = sound
            pygame.mixer.set_reserved(1)
            self.music = pygame.mixer.Channel(0)
            self.toggle()
        except pygame.error:
            self.sounds.clear()

    def toggle(self):
        if self.sounds:
            self.enabled = not self.enabled
            if self.enabled:
                self.music.play(self.sounds["lantern"], loops=-1, fade_ms=400)
            else:
                self.music.stop()
                for name in EFFECTS.values():
                    self.sounds[name].stop()

    def attach(self, events):
        for event, name in EFFECTS.items():
            events.subscribe(event, lambda payload, cue=name: self.play(cue))

    def play(self, name):
        if self.enabled:
            self.sounds[name].play()
