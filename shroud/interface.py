"""Shared offline typography and deliberately small desktop menu vocabulary."""
from functools import lru_cache
from pathlib import Path
import pygame

INK = (23, 31, 30)
PAPER = (238, 229, 210)
SAGE = (171, 191, 163)
MUTED = (184, 190, 175)
RED = (181, 70, 59)

@lru_cache(maxsize=32)
def font(size=22, serif=False):
    name = 'Spectral-Regular.ttf' if serif else 'SourceSans3-Regular.otf'
    return pygame.font.Font(str(Path(__file__).resolve().parents[1] / 'assets/fonts' / name), size)

@lru_cache(maxsize=512)
def rendered(message, size, color, serif=False):
    return font(size, serif).render(message, True, color)

def text(surface, message, pos, size=22, color=PAPER, serif=False, center=False):
    image = rendered(str(message), size, color, serif)
    surface.blit(image, image.get_rect(center=pos) if center else pos)

def button(surface, label, rect, focused=False):
    amount = float(focused)
    fill = tuple(round(a+(b-a)*amount) for a,b in zip(INK,(46,57,50)))
    pygame.draw.rect(surface, fill, rect)
    pygame.draw.rect(surface, SAGE if amount >= .5 else (87, 98, 83), rect, 2 if amount >= .5 else 1)
    text(surface, label, rect.center, center=True)

DIFFICULTIES = {
    'gentle': ('Gentle', 'Slower enemies. A simple dash and one sword upgrade.', 1.4, 1.25, .75),
    'balanced': ('Balanced', 'Standard pace. E handles chests and stored bursts.', 1., 1., 1.),
    'demanding': ('Demanding', 'Faster enemies. Time your stored burst with Q.', .8, .85, 1.15),
}

class Menu:
    def __init__(self, page='title'):
        self.page = page
        self.focus = 0
        self.back = 'title'
        self.difficulty = 'balanced'
        self.profile_stats = None
        self.sound_enabled = False
        self.reduced_motion = False
        self.pointer = (-1,-1)
        self.highlight = {}
        self.last_draw = pygame.time.get_ticks()

    def options(self):
        return {
            'title': ['Play', 'Tutorial', 'Controls', 'Quit'], 'trained': ['Play', 'Back'],
            'difficulty': ['Gentle', 'Balanced', 'Demanding', 'Back'],
            'pause': ['Resume', 'Techniques', 'Controls', 'Restart level', 'New journey', 'Quit'],
            'controls': ['Sound '+('on' if self.sound_enabled else 'off'), 'Toggle fullscreen', 'Reduce motion: '+('On' if self.reduced_motion else 'Off'), 'Back'], 'techniques': ['Back'],
            'complete': ['Continue', 'New journey', 'Quit'],
            'finished': ['New journey', 'Quit'], 'retry': ['Retry', 'New journey', 'Quit'],
            'restart': ['Restart level', 'Cancel'], 'quit': ['Quit game', 'Cancel'],
        }[self.page]

    def rects(self):
        options = self.options()
        if self.page == "controls":
            return [pygame.Rect(440, 534+i*51, 400, 44) for i in range(len(options))]
        if self.page == "finished":
            return [pygame.Rect(440, 545+i*64, 400, 52) for i in range(len(options))]
        y = 620 if self.page == 'techniques' else 310
        return [pygame.Rect(440, y+i*64, 400, 52) for i in range(len(options))]

    def handle(self, events):
        for event in events:
            if event.type == pygame.MOUSEMOTION: self.pointer = event.pos
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p): return 'back'
                if event.key in (pygame.K_DOWN, pygame.K_TAB): self.focus = (self.focus+1)%len(self.options())
                if event.key == pygame.K_UP: self.focus = (self.focus-1)%len(self.options())
                if event.key == pygame.K_RETURN: return self.options()[self.focus]
                if event.key == pygame.K_m and self.page == 'controls': self.reduced_motion = not self.reduced_motion
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(self.rects()):
                    if rect.collidepoint(event.pos): self.focus=i; return self.options()[i]
        return None

    def draw(self, surface, world, reward_ui=None, portrait=None):
        clear_text(surface)
        surface.fill(INK)
        pygame.draw.line(surface, RED, (600, 112), (680, 112), 3)
        titles={'title':'Shroud', 'difficulty':'Choose your pace', 'pause':'Paused',
                'trained':'Training complete', 'controls':'Controls', 'techniques':'Your techniques',
                'restart':'Begin this level again?', 'quit':'Leave the shadows?',
                'complete':'Path cleared', 'finished':'Journey complete', 'retry':'Back to the shadows'}
        text(surface,titles[self.page],(640,175),48,serif=True,center=True)
        subtitle={'trained':'Choose Play when you’re ready for your first journey.', 'title':'A ninja’s journey', 'difficulty':'You can choose again when starting a new run.',
                  'pause':DIFFICULTIES[self.difficulty][0], 'restart':'Your upgrades and progress in this level will reset.',
                  'quit':'This run is not saved.'}.get(self.page,'')
        text(surface,subtitle,(640,244),22,MUTED,center=True)
        if self.page == "finished":
            text(surface, "Your playstyle so far", (640, 250), 30, serif=True, center=True)
            if self.profile_stats is None:
                text(surface, "Profile unavailable for this journey.", (640, 350), 22, MUTED, center=True)
            else:
                for i, (key, label) in enumerate((("fortitude", "Fortitude"), ("adaptability", "Adaptability"),
                                                  ("risk_appetite", "Risk taking"))):
                    item = self.profile_stats[key]
                    observed = any(signal["runs"] for signal in item["signals"].values())
                    value = (f"{item['score']:g}/100   ·   {item['confidence']:.0%} coverage"
                             if observed else "No observation yet")
                    text(surface, label, (355, 300 + 55*i), 24)
                    text(surface, value, (624, 300 + 55*i), 22, MUTED)
                text(surface, "Coverage grows across journeys and different situations.", (640, 483), 20, MUTED, center=True)
        if self.page == 'title' and portrait is not None:
            surface.blit(portrait, portrait.get_rect(center=(640,635)))
        if self.page=='controls':
            lines=['WASD  Move    ·    Mouse  Aim', 'Left click  Slash    ·    Hold to charge',
                   'Right click  Throw    ·    Hold to steady your aim', 'Space  Tap to dash, hold to run',
                   'E  Open a nearby chest    ·    Q  Use your stored burst',
                   'Esc  Pause    ·    F11  Fullscreen', 'Optional: J / K quick attacks · Tab map · F2 level selection']
            if self.difficulty == 'gentle':
                lines = ['WASD  Move    ·    Mouse  Aim', 'Left click  Slash    ·    Right click  Throw',
                         'Space  Dash    ·    E  Open chest', 'Esc  Pause    ·    Tab  Map']
            elif self.difficulty == 'balanced':
                lines[4] = 'E  Open chest or activate stored burst'
            for i,line in enumerate(lines): text(surface,line,(640,285+i*36),22,center=True)
        if self.page=='difficulty':
            key=list(DIFFICULTIES)[min(self.focus,2)]
            text(surface,DIFFICULTIES[key][1],(640,602),22,MUTED,center=True)
        if self.page=='techniques':
            from shroud.rewards import REWARDS,RANKS,TECHNIQUE_HELP
            from shroud.reward_ui import value_text, STAT_LABELS
            values=world.rewards.effective()
            for i,(key,r) in enumerate((k,v) for k,v in REWARDS.items() if v.category=='technique' and (world.difficulty != 'gentle' or k in ('reach','sharpening'))):
                x,y=170+(i//4)*520,290+(i%4)*75
                if reward_ui:
                    surface.blit(reward_ui.small_icons[key], (x-34,y+5))
                text(surface,r.name if world.difficulty == 'gentle' else r.name+' '+RANKS[world.rewards.ranks.get(key,0)],(x,y),26)
                text(surface,TECHNIQUE_HELP[key] if world.difficulty == "gentle" else STAT_LABELS[r.stat]+': '+value_text(key,getattr(values,r.stat)),(x,y+32),20,MUTED)
        now = pygame.time.get_ticks()
        blend = min(1., (now-self.last_draw)/100)
        self.last_draw = now
        for i,(label,rect) in enumerate(zip(self.options(),self.rects())):
            target = float(i==self.focus or rect.collidepoint(self.pointer))
            old = self.highlight.get((self.page,i),target)
            amount = target if self.reduced_motion else old+(target-old)*blend
            self.highlight[self.page,i] = amount
            button(surface,label,rect,amount)
        text(surface,'↑ ↓  Choose     Enter  Confirm     Esc  Back',(640,740),20,MUTED,center=True)


# Text is replayed at the window's native resolution after world/art scaling.
TEXT_TARGET = None
TEXT_QUEUE = []
_original_text = text

def text(surface, message, pos, size=22, color=PAPER, serif=False, center=False):
    if surface is TEXT_TARGET:
        TEXT_QUEUE.append((str(message),pos,size,tuple(color),serif,center))
    else:
        _original_text(surface,message,pos,size,color,serif,center)

def clear_text(surface):
    if surface is TEXT_TARGET: TEXT_QUEUE.clear()
