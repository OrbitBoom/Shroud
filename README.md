# SHROUD

SHROUD is a top-down action game built with Python and pygame-ce. Fight through
handcrafted maps using slashes, shuriken, dashes and a Shadow Echo that repeats
your next attack from the spot you left behind.

Each run contains **five different layouts** sampled from a collection of 18.
Every level independently receives a training grounds, snow, marsh, crosswind or bamboo
biome. Clear the required enemy groups, open the seals and reach the exit.

## Install and play

Requires **Python 3.10 or newer**.

```sh
git clone https://github.com/TheUnknownBSYT/Shroud.git
cd Shroud
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, create and activate the environment with:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Run the game from the cloned source tree so the map data and artwork are available.

Start with **Tutorial** for a short practice session. Walk, slash, throw, then open one chest. Each step appears when you finish the previous one. Esc leaves practice. Training uses silent sentries and contributes no profile observations.

The desktop soundtrack is an original, looping plucked melody. Slashes, throws, dashes, hits, and scroll choices have short sound cues. Controls → Sound toggles music and effects for the session.

Normal launch opens a title screen. Choose **Play**, then **Gentle**, **Balanced**
or **Demanding**. New journeys begin in First Lantern, where chests introduce
upgrades. Balanced preserves the original combat pace. Gentle gives 40% longer
enemy warnings, 25% longer firing cooldowns and 25% slower shots. Demanding uses
20% shorter warnings, 15% shorter cooldowns and 15% faster shots. Player damage,
health and movement are shared. Gentle uses an ordinary dash and offers one sword upgrade. Balanced uses E for nearby chests and otherwise for a stored burst. Demanding uses E for chests and Q for bursts. The chosen pace lasts
through the run and retries and is included in event context; it never adapts
silently. Choose New journey from pause to choose another pace.

The resizable desktop window letterboxes the original play area. F11 or Controls → Toggle fullscreen switches display mode, and pointer coordinates follow the viewport. Interface text is rendered
at window resolution. The supported resize minimum is 960×600; 1280×800 is
recommended for reading. Native Retina/fullscreen behaviour can vary with SDL
and the operating system.

Escape opens a mouse/keyboard pause menu with Controls, Techniques, Restart and
Quit. Menu restarts and quitting require confirmation. Advanced shortcuts below
remain available; R still restarts immediately. Controls includes **M: Reduce
motion**, which removes impact shake/trails and makes menu highlights immediate.
Preferences are session-only. Explicit `--level` and headless launches bypass the
title screen for development.

Typography is bundled offline: Spectral Regular and Source Sans 3 Regular, under
the SIL Open Font License. Their licence notices are in `assets/fonts/`.


## Controls

| Input | Action |
| --- | --- |
| WASD / arrow keys | Move |
| Mouse | Aim independently while moving |
| Tap Space | Dash on release and leave a Shadow Echo |
| Hold Space | Sprint; release to stop |
| Hold / release left mouse | Charge and release a slash |
| Hold / release right mouse | Focus and throw a shuriken |
| J / K | Immediate slash / shuriken |
| E | Open a nearby available scroll cache |
| Q | Consume the stored burst (when no burst is active) |
| 1 / 2 or click (scroll screen) | Select a scroll; Enter or Confirm applies it |
| Left / Right / Tab (scroll screen) | Focus a card; Enter selects it, then confirms |
| Enter | Continue after completion or retry after death |
| R | Restart the current level with a newly rolled biome |
| F2 | Choose the first layout and biome for a new run |
| B (in F2 menu) | Cycle Random / Grounds / Snow / Marsh / Wind / Bamboo |
| Tab | Pause and show the full map |
| P | Pause / resume |
| F1 | Toggle collision and combat debugging |
| Esc | Back from an overlay, or open the pause menu |
| F11 | Toggle fullscreen; restore the previous window size |
| Arrows / Tab / Enter (menus) | Move focus and confirm |

Space held for 0.18 seconds starts sprinting; a shorter press dashes on release.
Sprinting blocks attacks. Slashing toward an incoming bolt during the opening
attack window can reflect it. Dashes deal damage but do not grant invulnerability.

## Finding your way

The upper-right minimap shows the whole layout with north at the top. The cream
diamond follows the ninja, coral dots show living enemies, and a green outline
marks the exit. In marsh mist, enemy dots appear inside the clear radius.
Press Tab for a larger view. A gold ring identifies each enemy holding a seal.

At The Pilgrim Fork, Lantern Causeway, and Chimney Switchbacks, two wooden boards with compass bearings on a
single post describe the routes before they split. Try
`python main.py --level temple_01 --biome grounds` to see the guarded shortcut
and the longer gallery from the start.

## Shadow Echo and progression

On Balanced and Demanding, a dash leaves one stationary Echo. Your next accepted slash or throw queues its
repeat after **0.35 seconds**, preserving the attack direction and slash charge.
An unused Echo expires after **3 seconds**; another dash replaces it.

Gold markers identify enemies required to open a seal. Other encounters can be
left unfinished. After opening all seals, reach the exit and press Enter to
continue. The run ends after its configured number of levels.

Refuges restore health once and unlock a checkpoint retry. Enter after death
retries that checkpoint with the same biome. R restarts the entire current level
and rolls its biome again. F2 starts a fresh run. Progress is held in memory and
is lost when the game closes.

## Scroll caches and power-ups

First Lantern offers one chest on Gentle, two on Balanced, and five on Demanding.

```sh
python main.py --level training_01 --biome grounds --seed 7
```

On Demanding, three technique caches and two burst caches reward the starting area, garden
detour and cleared courtyard. Encounter caches unlock when the lesson seal opens.
Other layouts do not have caches yet. The usual random starting-layout behavior
is unchanged; choose First Lantern with the command above or F2 to try them.

Press **E** nearby to pause and reveal two distinct scrolls from one category.
Click or press **1/2** to select, then **Enter** or Confirm to take it. Hovering
does not select. **Esc** closes unclaimed; reopening preserves the same offers.
If fewer than two techniques remain eligible, the cache stays unclaimed.

| Run technique | Rank I / II / III total bonus |
| --- | --- |
| Sharpening | Slash damage +15% / +25% / +30% |
| Reach | Slash reach +10% / +20% / +25%; parry reach stays unchanged |
| Quick Charge | Full slash charge time -15% / -25% / -30% |
| Footwork | Dash cooldown -15% / -25% / -30% |
| Rapid Throw | Shuriken cooldown -15% / -25% / -30%, subject to action completion |
| Long Throw | Shuriken range +20% / +35% / +50%; speed unchanged |
| Lingering Echo | Waiting lifetime +1 / +1.5 / +2 seconds; delay/fade unchanged |
| Parry | Opening window +0.05 / +0.08 / +0.10 seconds; geometry unchanged |

Repeat picks increase rank; capped techniques leave future offer pools. Bonuses
are relative to base values. Slash damage rounds to whole points. Gentle and Balanced cards describe the effect in one sentence. Demanding cards also show the rank and the values before and after the upgrade. Charged
slashes and Echo use the upgraded damage/reach. Gentle keeps your chosen sword effect on screen. On the other paces, hover over an owned icon to recall its effect or open Techniques from the pause menu for the numbers.
Techniques survive level transitions and clear on death, restart or run end.

A burst occupies one stored slot. On Balanced, press **E** away from an available chest to use it. On Demanding, press **Q**. Each lasts **10 simulation seconds**.
**Smoke Veil** cancels enemy windups and blocks new targeting/shots; existing
projectiles still hurt. **Haste** multiplies normal walking speed by 1.5, including
walking while aiming/attacking; sprint and dash retain their original speeds.
**Frenzy** multiplies slash/throw cooldowns by 0.65 and halves only recovery after
the hit/release phase. **Flow** gives +40% damage to an accepted slash following a
throw or a throw following a slash. Its first attack establishes the sequence;
repeats get no bonus, and dashes leave the sequence alone. The HUD hints at the
next boosted attack. Echo copies damage and timing without advancing Flow.
Only one burst can be active. A stored replacement can wait during it, but Q
cannot consume that replacement until the active burst ends. Replacing an occupied
stored slot requires a second confirmation; cancel keeps the old charge.

All menus and focus loss freeze burst time. P resumes after focus loss. UI clicks
never attack, and leaving a menu requires a fresh attack/Space press. Bursts clear
on death, restart and final completion. The HUD shows acquired ranks, stored/active
bursts, paused countdowns and expiry. No progress is saved to disk.

Cooldowns cannot finish before their action: normal Rapid Throw I/II/III gives
0.238/0.22/0.22 seconds. During Frenzy those become 0.1547/0.14/0.14 seconds.
Frenzy keeps the slash's 0.06–0.22s hit window and the throw's initial 0.06s
release pose, shortening total durations to 0.26s and 0.14s. Throws still emit
immediately. Extended parry windows are protected before recovery is shortened.
Accepted actions and queued Echo copies retain their timing/damage/range even
after a burst expires.

Each run retains up to 4,096 detached in-memory event records: available choices,
confirmed picks, actual attacks/burst use, hits, parries and damage, with context.
Records span level transitions and remain after completion/death until a new
run or retry. Older records are discarded when full; `history.dropped` counts
them. To retain journeys across launches, enable local recording.

## Your playstyle in five minutes

- Finish the last level to see **Your playstyle so far**. The three rows summarize the journeys in your current profile. A normal desktop launch keeps this session in memory. Closing the game clears it. Launch with `python main.py --profile` to keep building the same local profile across launches. Tutorial practice contributes no observations.
- **Risk taking.** At the Pilgrim Fork, the sign offers a short causeway with two archers and a longer gallery with cover. Entering the guarded causeway gives +1. Taking the gallery gives −1. The rule checks that the choice was offered and both guards were alive. Skipping the fork supplies no vote.
- **Adaptability.** Suppose you slash, take damage, switch to a throw and land it in the same area within the recovery window. That counts as revising your tactic. With Flow active, alternating attacks earns a damage bonus, so the rule leaves your intent undecided.
- **Fortitude.** Two signals share the score. Persistence can be observed when you retry after a death and clear the setback area or finish the level. Restraint can be observed when you have an attack available at low health, wait through an enemy warning, then attack just after the shot. Dying or missing a shot alone gives neither signal a negative vote.
- **How a number moves.** The game saves events, matches a rule, and links its vote to the events that explain it. Votes are averaged within a situation, then within a journey. Four neutral starting votes dampen early swings. One guarded shortcut moves Risk taking from 50 to 60. A sheltered choice on the next journey brings it back to 50.
- **What coverage means.** One journey in one situation gives about 8% coverage. Four qualifying journeys across three different combinations of layout, biome and pace reach 100% for a signal. Fortitude uses the less-observed of its two signals for coverage. “No observation yet” means the rule has seen no qualifying example. A score describes play in SHROUD, and coverage describes how much the rules have seen.
- **What changes today.** You pick the difficulty. The game draws layouts and biomes using its existing random rules. Gates respond to cleared encounters. Profile scores currently have no say in layouts, enemies, chest offers or difficulty.

## Work for later

- [ ] Add a password-free local player picker with **New player** and **Continue as**. Give each player a stable ID so two people can share a device and keep separate histories.
- [ ] Let a returning player attach their existing anonymous saved profile to their new account. Test switching, renaming and reopening accounts without mixing records.
- [ ] Playtest the rules. Ask people why they chose a route or changed attacks, then compare their answers with the recorded reasons.
- [ ] Next week, try one optional change driven by the profile, such as offering a guarded shortcut. Decide how much evidence it needs and keep a neutral route available.
- [ ] Record what the adaptive system offered before scoring the response. Compare ordinary and adaptive runs to check whether the offer itself steered the choice.
- [ ] Revisit the end screen after playtesting. Decide which scores and examples players actually find useful.

## Optional saved playstyle profile

Run `python main.py --profile` to keep an offline journal in `~/.shroud/profile.sqlite3`.
A normal desktop launch keeps a temporary profile in memory. One file represents one player. To choose another
file, add `--profile-db PATH` when playing and `--db PATH` before the inspection command.
The journal includes gameplay decisions, their alternatives, actions, outcomes, and
the event IDs behind each rule-based score. The three scores describe patterns seen
in play. Coverage grows across journeys and situations. Level selection stays as authored.

With the game closed, use:

```sh
python -m shroud.profile_store show
python -m shroud.profile_store export ~/shroud-profile.json
python -m shroud.profile_store delete
```

Export requires a new filename. Delete clears all sessions, journeys, events, and scores
in the selected database. Existing exports remain separate files.

## Run options

```sh
python main.py --levels 3                   # Choose a run length from 1 to 18
python main.py --level rooftop_03           # Choose the first layout
python main.py --levels 5 --seed 42         # Reproduce layout and biome draws
python main.py --list-levels                # List all available layouts
python main.py --level temple_01 --biome bamboo --levels 1  # Try breakable cover
```

Layouts do not repeat within a run; biome draws can repeat. A seed reproduces
layout/biome choices for the same sequence of level loads. Combat spread and
visual effects have their own randomness. Map names and IDs such as `snow_01`
identify geometry and do not restrict the selected biome. `--biome` pins a biome
for the run and restarts; omit it for random selection. In F2, press B to choose
any biome or return to Random, then Enter to start. Random gives each biome a 20%
chance per load, so a five-level run need not contain every biome. The selector
shows layout dimensions separately from the biome choice.

## Biomes

Every layout supports all five gameplay conditions:

| Biome | What changes |
| --- | --- |
| Training grounds | Immediate movement and full visibility |
| Snow | Accelerate into movement and slide when braking; sprint needs more stopping room |
| Marsh | Distant scenery and enemies fade into mist; enemies attack only inside the clear radius. Incoming shots remain visible, and Tab keeps landmarks but hides distant enemies |
| Crosswind | Three seconds calm, one-second directional warning, then an eight-second gust. Wind bends all shots, including Echo and reflected shots |
| Bamboo | Authored solid walls on every map; cut a shortcut or take a clear route around them |

Bamboo clusters absorb three friendly or hostile shots, including the breaking
shot. One player/Echo slash cuts a cluster immediately. Pale notches show damage.
Walking and dashing stop at intact walls. Cutting opens movement and firing lanes
for both sides. Restart/checkpoint retry restores all bamboo.

Snow, mist and wind strength/direction are tuned per layout. Retry starts with
zero movement momentum and a calm wind cycle. Wind affects projectiles in the
shown world direction; it never pushes the player.

## Current development status

- All 18 layouts support five playable biomes, including authored bamboo walls.
- Ranged enemies and practice targets are playable. Four additional enemy art
  families are included for future behaviors.
- Biome rules, planned enemy counterplay and 180 future encounter drafts are described in
  [design/biomes.json](design/biomes.json), [design/enemies.json](design/enemies.json)
  and [design/encounters.json](design/encounters.json).
- Optional local profiling records journeys across launches. Starting the game begins a fresh journey.
- All eight techniques and four bursts are implemented, with contextual event
  history. Authored caches remain in First Lantern; other maps await placement.

## Development

Tune gameplay in [shroud/settings.py](shroud/settings.py). Edit layouts in
`data/levels/`; positions use tile units, with 96 world pixels per tile. Floor
materials are `earth`, `stone`, `platform` and `mat`. Runtime biome selection
changes their appearance and gameplay rules. Static geometry stays fixed; bamboo
adds destructible walls with validated bypasses. Each JSON has `biome_settings`
for snow acceleration/braking, marsh radii and wind direction/strength, plus
`bamboo_walls` start/end segments. Shared defaults live in `BIOME_SETTINGS` in
settings.py; `shroud/biomes.py` merges and validates per-room values.
Reload with R or F2 after editing a layout.

```sh
python -m pytest -q
python -m shroud.level_validation
python main.py --headless --levels 5 --seed 42 --frames 120 --screenshot /tmp/shroud.png
python -m tools.export_map_gallery
python -m tools.powerup_lab --all-ranks 3 --burst frenzy
python -m tools.powerup_lab --rank parry=1 --offers parry lingering_echo
python -m tools.powerup_lab --burst haste --offers flow frenzy
```

The opt-in power-up lab opens First Lantern with deterministic ranks, a stored
burst and/or a real two-card cache. Press Q to activate the stored burst. Use
`--rank KEY=0..3` repeatedly to override individual ranks; offers must be distinct,
eligible and in one category. It also accepts `--headless --frames N --screenshot
PATH`. Developer setup records are marked; normal `main.py` never imports the lab.

The tests cover combat, Echo timing, input, run progression and route clearance
across all 90 layout–biome combinations. The gallery exporter writes map and
biome previews to the ignored `local/map_gallery/` directory.
