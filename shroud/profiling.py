"""Versioned, deterministic interpretation of discrete gameplay opportunities."""
from collections import defaultdict
from dataclasses import dataclass

RULE_VERSION = 1
SIGNALS = {"risk_appetite": ("route",), "adaptability": ("revision",),
           "fortitude": ("persistence", "restraint")}
# Four neutral runs keep a single observation close to the starting point.
NEUTRAL_RUNS = 4
CONFIDENCE_RUNS = 4
CONFIDENCE_CONTEXTS = 3
SIGNAL_WEIGHTS = {signal: 1.0 for signals in SIGNALS.values() for signal in signals}
PRESSURE_WINDOW = 3.0
RECOVERY_WINDOW = 8.0


@dataclass(frozen=True)
class Evidence:
    signal: str
    value: int | None
    reason: str
    sources: tuple


@dataclass(frozen=True)
class Action:
    name: str
    action_id: int
    event_id: int
    time: float
    area: str
    flow_active: bool


@dataclass
class Warning:
    event_id: int
    time: float
    enemy: int
    area: str
    release: int | None = None


class Interpreter:
    """One interpreter per attempt. Source IDs refer to committed events."""
    def __init__(self):
        self.route = self.last_action = self.setback = self.warning = self.retry = None

    def consume(self, row, event_id):
        name, detail, ctx = row["event"], row["details"], row["context"]
        now, area = row["timestamp"], ctx["area"]
        evidence = []
        if name == "room_entered":
            self.__init__()
        elif name == "retry_started":
            self.retry = (detail.get("previous_death_event"), event_id, detail.get("setback_area"))
        elif name == "route_offered":
            self.route = (detail["fork"], event_id)
        elif name == "route_taken" and self.route and detail["fork"] == self.route[0]:
            branch = detail["branch"]
            value = {"exposed": 1, "sheltered": -1}.get(branch)
            guarded = detail.get("causeway_guards") == 2
            reason = f"Entered {branch} branch after fork cue" if guarded else "Original causeway pressure unconfirmed"
            evidence.append(Evidence("route", value if guarded else None, reason,
                                     (self.route[1], event_id)))
            self.route = None
        elif name == "enemy_warning" and detail.get("attack_available", False) and ctx["health"] <= ctx["max_health"] / 2:
            self.warning = Warning(event_id, now, detail["enemy"], area)
        elif name == "enemy_fired" and self.warning and detail["enemy"] == self.warning.enemy:
            self.warning.release = event_id
        elif name in ("player_slash", "player_throw_shuriken"):
            flow_active = ctx.get("modifiers", {}).get("active") == "flow"
            self.last_action = Action(name, detail["action_id"], event_id, now, area, flow_active)
            if self.warning:
                cue = self.warning
                held = cue.release is not None and now - cue.time <= PRESSURE_WINDOW and area == cue.area
                sources = (cue.event_id, cue.release, event_id) if cue.release else (cue.event_id, event_id)
                reason = ("Waited through a low-health warning and attacked after release" if held
                          else "Attack timing has several possible explanations")
                evidence.append(Evidence("restraint", 1 if held else None, reason, sources))
                self.warning = None
        elif name == "player_hit":
            self.warning = self.setback = None
            old = self.last_action
            if old and now - old.time <= PRESSURE_WINDOW and old.area == area:
                self.setback = (old, event_id)
        elif name == "enemy_hit" and detail["owner"] == "player" and self.setback and self.last_action:
            old, injury = self.setback
            new = self.last_action
            if new.action_id != old.action_id and new.action_id == detail["action_id"] and detail["source"] in ("slash", "shuriken"):
                changed = old.name != new.name and now - old.time <= RECOVERY_WINDOW and old.area == new.area == area
                reason = "Recovery did not establish a change of tactic"
                if changed:
                    reason = "Changed attack type and landed a hit after taking damage"
                if old.flow_active or new.flow_active:
                    changed = False
                    reason = "Flow rewards alternating attacks, so intent is unclear"
                evidence.append(Evidence("revision", 1 if changed else None, reason,
                                         (old.event_id, injury, new.event_id, event_id)))
                self.setback = None
        if name in ("encounter_cleared", "level_completed") and self.retry:
            death, retry, setback_area = self.retry
            if name == "level_completed" or area == setback_area:
                sources = (death, retry, event_id) if death is not None else (retry, event_id)
                evidence.append(Evidence("persistence", 1, "Retried after death and recovered in the setback area or finished the level",
                                         sources))
                self.retry = None
        return evidence


def scores(rows):
    """Average within a situation, then within a run. Every run has equal weight."""
    buckets = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for signal, value, run, level, biome, pace in rows:
        if value is not None:
            buckets[signal][run][level, biome, pace].append(value)

    result = {}
    for pillar, signals in SIGNALS.items():
        parts = {}
        for signal in signals:
            runs = buckets[signal]
            contexts = {key for groups in runs.values() for key in groups}
            means = []
            for groups in runs.values():
                context_means = [sum(values) / len(values) for values in groups.values()]
                means.append(sum(context_means) / len(context_means))
            score = 50 + 50 * sum(means) / (NEUTRAL_RUNS + len(means))
            confidence = min(1, len(runs) / CONFIDENCE_RUNS) * min(1, len(contexts) / CONFIDENCE_CONTEXTS)
            parts[signal] = dict(score=round(score, 2), confidence=round(confidence, 3),
                                 runs=len(runs), contexts=len(contexts))
        weight = sum(SIGNAL_WEIGHTS[s] for s in signals)
        average = sum(parts[s]["score"] * SIGNAL_WEIGHTS[s] for s in signals) / weight
        result[pillar] = dict(score=round(average, 2), confidence=min(p["confidence"] for p in parts.values()),
                              signals=parts)
    return result
