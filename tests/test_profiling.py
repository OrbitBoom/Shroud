"""Offline journal and scoring checks, including real simulation and scene boundaries."""
import json
import sqlite3

import pygame
import pytest
from pygame import Vector2

from shroud import settings as S
from shroud.campaign import load_level
from shroud.combat import deal_damage
from shroud.game import Game, Sandbox
from shroud.history import RunHistory
from shroud.level import Room
from shroud.player import Command, InputFrame
from shroud.profile_store import APPLICATION_ID, MIGRATIONS, ProfileStore
from shroud.profiling import Interpreter, scores
from shroud.rewards import Choice


def recorded_world(store, level="training_01", biome="grounds"):
    store.begin_run()
    history = RunHistory()
    history.sink = store
    return Sandbox(history=history, room=Room(load_level(level, biome)))


def test_real_cache_choice_flow_and_uses_stay_separate(tmp_path):
    store = ProfileStore(tmp_path / "journal")
    try:
        world = recorded_world(store)
        cache = next(c for c in world.caches if c.category == "burst")
        world.rewards.stored = "haste"
        cache.offer(world.rewards, world.events)
        choice = Choice(cache)
        choice.select(1)
        assert not choice.confirm(world.rewards, world.events)
        assert choice.confirm(world.rewards, world.events)
        world.step(.01, InputFrame(commands=[Command("burst")]))
        selection = store.db.execute("SELECT details FROM preferences WHERE name='reward_confirmed'").fetchone()
        detail = json.loads(selection[0])
        assert detail["selected"] == 1 and detail["replacement"] and detail["prior"]["stored"] == "haste"
        offered = json.loads(store.db.execute("SELECT details FROM preferences WHERE name='reward_offered'").fetchone()[0])
        assert offered["offer_id"] == detail["offer_id"] and offered["effects"] == detail["offered_effects"]
        assert offered["offers"][1] == detail["reward"]
        assert store.db.execute("SELECT count(*) FROM behaviour WHERE name='burst_activated'").fetchone()[0] == 1
        assert store.profile() == scores([])
    finally:
        store.close()


@pytest.mark.parametrize("tile,expected", [((12, 16), 60), ((12, 7), 40)])
def test_audited_fork_links_to_cue_and_area_time(tmp_path, tile, expected):
    store = ProfileStore(tmp_path / "db")
    try:
        world = recorded_world(store, "temple_01", "wind")
        spawn = world.player.position.copy()
        world.player.position = Vector2(3, 13.25) * S.TILE_SIZE
        world.step(.01, InputFrame())
        assert world.route_state == "unseen"
        world.player.position = spawn
        world.step(.01, InputFrame())
        offer = json.loads(store.db.execute("SELECT details FROM events WHERE name='route_offered'").fetchone()[0])
        assert offer["navigation_version"] == 2 and offer["signpost"] == world.room.data["choices"][0]["signpost"]
        world.player.position = Vector2(tile) * S.TILE_SIZE
        world.step(.01, InputFrame())
        world.step(.01, InputFrame())
        world.sample_area(force=True)
        assert store.profile()["risk_appetite"]["score"] == expected
        assert store.db.execute("SELECT sum(seconds) FROM area_time").fetchone()[0] == pytest.approx(.04)
        evidence = store.db.execute("SELECT sources FROM evidence").fetchall()
        assert len(evidence) == 1
        sources = json.loads(evidence[0][0])
        assert [store.db.execute("SELECT name FROM events WHERE id=?", (i,)).fetchone()[0] for i in sources] == [
            "route_offered", "route_taken"]
        assert json.loads(store.db.execute("SELECT profile FROM updates").fetchone()[0]) == store.profile()
    finally:
        store.close()


def test_persistence_needs_recovery_and_death_retains_run(tmp_path):
    path = tmp_path / "journal"
    store = ProfileStore(path)
    world = recorded_world(store)
    run = store.run
    deal_damage(world, world.player, 100, "bolt", "enemy")
    world.step(.01, InputFrame())
    world.retry_checkpoint()
    assert store.run == run and store.profile() == scores([])
    target = world.enemies[0]
    for enemy in world.enemies:
        if enemy.group == target.group:
            deal_damage(world, enemy, 100, "slash")
    assert store.profile()["fortitude"]["signals"]["persistence"]["score"] == 60
    world.history.finish(world,"completed")
    store.close()
    reopened = ProfileStore(path)
    try:
        row = reopened.db.execute("SELECT * FROM run_summary").fetchone()
        assert (row["status"], row["attempts"], row["deaths"]) == ("completed", 2, 1)
        assert reopened.profile()["fortitude"]["score"] == 55
        assert reopened.profile()["fortitude"]["confidence"] == 0
        reopened.begin_run()
        assert reopened.run != run
    finally:
        reopened.close()


def test_pressure_and_tactic_rules_require_order_attribution_and_context():
    engine = Interpreter()
    def event(number, name, **detail):
        active = detail.pop("active", None)
        return engine.consume(dict(timestamp=number / 10, event=name, details=detail,
                                   context={"area":"room", "health":1, "max_health":4,
                                            "modifiers":{"active":active}}), number)
    event(1, "enemy_warning", enemy=1, attack_available=False)
    assert not event(2, "player_slash", action_id=1)
    event(3, "enemy_warning", enemy=1, attack_available=True)
    event(4, "enemy_fired", enemy=2)
    assert event(5, "player_slash", action_id=2)[0].value is None
    event(6, "enemy_warning", enemy=1, attack_available=True)
    event(7, "enemy_fired", enemy=1)
    restraint, = event(8, "player_slash", action_id=3)
    assert restraint.value == 1 and restraint.sources == (6,7,8)
    event(9, "player_hit")
    event(10, "player_throw_shuriken", action_id=4)
    assert not event(11, "enemy_hit", owner="echo", source="shuriken", action_id=4)
    revision, = event(12, "enemy_hit", owner="player", source="shuriken", action_id=4)
    assert revision.value == 1 and revision.sources == (8,9,10,12)
    event(13, "player_hit")
    event(14, "player_throw_shuriken", action_id=5)
    assert event(15, "enemy_hit", owner="player", source="shuriken", action_id=5)[0].value is None
    event(16, "room_entered")
    assert not event(17, "route_taken", fork="test", branch="exposed")
    event(18, "route_offered", fork="test")
    assert event(19, "route_taken", fork="test", branch="exposed", causeway_guards=0)[0].value is None
    event(20, "player_slash", action_id=6, active="flow")
    event(21, "player_hit")
    event(22, "player_throw_shuriken", action_id=7)
    assert event(23, "enemy_hit", owner="player", source="shuriken", action_id=7)[0].value is None


def test_one_long_run_cannot_buy_confidence():
    one = [("route", 1, "first", "temple", "wind", "gentle")]
    first = scores(one)["risk_appetite"]
    assert first["confidence"] < .1 and first["score"] == 60
    assert scores(one * 2000) == scores(one)
    contexts = [("route", 1, str(i), "temple", biome, "gentle") for i, biome in enumerate(("snow","wind","grounds","snow"))]
    assert scores(contexts)["risk_appetite"]["confidence"] == 1
    assert scores(contexts)["risk_appetite"]["score"] == 75
    assert scores(one + [("route", -1, "second", "temple", "snow", "gentle")])["risk_appetite"]["score"] == 50
    assert scores([("revision", None, "a", "b", "c", "d")]) == scores([])


def test_migration_recovery_lock_export_and_delete(tmp_path):
    path = tmp_path / "journal"
    db = sqlite3.connect(path)
    with db:
        for statement in MIGRATIONS[0]:
            db.execute(statement)
        db.execute(f"PRAGMA application_id={APPLICATION_ID}")
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO sessions(id,status) VALUES('old','playing')")
        db.execute("INSERT INTO runs VALUES('r','old','playing')")
        db.execute("INSERT INTO attempts(id,run,status) VALUES('a','r','playing')")
    db.close()
    store = ProfileStore(path)
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        ProfileStore(path)
    assert store.db.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
    for table in ("sessions", "runs", "attempts"):
        assert store.db.execute(f"SELECT count(*) FROM {table} WHERE status='interrupted'").fetchone()[0] == 1
    recorded_world(store)
    store.db.close()  # Simulate loss of the process without a shutdown callback.
    after = ProfileStore(path)
    assert after.db.execute("SELECT count(*) FROM runs WHERE status='interrupted'").fetchone()[0] == 2
    after.close()
    admin = ProfileStore(path, playing=False)
    try:
        destination = tmp_path / "export.json"
        admin.export(destination)
        data = json.loads(destination.read_text())
        assert data["events"][0]["name"] == "room_entered"
        assert isinstance(data["events"][0]["context"], dict)
        with pytest.raises(FileExistsError):
            admin.export(destination)
        admin.delete_data()
        assert admin.profile() == scores([])
        for table in ("sessions","runs","attempts","events","evidence","updates"):
            assert admin.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    finally:
        admin.close()


def test_refuses_foreign_newer_or_absent_admin_database(tmp_path):
    path = tmp_path / "save"
    with pytest.raises(ValueError):
        ProfileStore(path, playing=False)
    assert not path.exists()
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE treasure(coins)")
    db.close()
    with pytest.raises(ValueError, match="Unrecognised"):
        ProfileStore(path)
    db = sqlite3.connect(path)
    assert db.execute("SELECT * FROM treasure").fetchall() == []
    db.execute(f"PRAGMA application_id={APPLICATION_ID}")
    db.execute("PRAGMA user_version=99")
    db.close()
    with pytest.raises(ValueError, match="Unsupported"):
        ProfileStore(path)


def test_title_preview_disabled_mode_and_run_replacement(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    path = tmp_path / "journal"
    try:
        disabled = Game("training_01", run_length=1)
        disabled.world.step(.01, InputFrame())
        assert not disabled.history.recording and not path.exists()
        store = ProfileStore(path)
        try:
            game = Game("training_01", run_length=1, title=True, profile_store=store)
            assert store.run is None
            game.load("temple_01")
            previous = store.run
            game.world.step(.01, InputFrame())
            game.load("training_01")
            assert store.run != previous
            row = store.db.execute("SELECT * FROM run_summary WHERE id=?", (previous,)).fetchone()
            assert row["status"] == "replaced" and row["seconds"] == pytest.approx(.01)
            game.history.clear()
            assert store.db.execute("SELECT start_reason FROM attempts WHERE id=?", (store.attempt,)).fetchone()[0] == "restart"
        finally:
            store.close()
    finally:
        pygame.quit()


def test_recording_does_not_change_simulation(tmp_path):
    store = ProfileStore(tmp_path / "journal")
    try:
        tracked = recorded_world(store, "temple_01", "wind")
        control = Sandbox(room=Room(load_level("temple_01","wind")))
        for tick in range(350):
            for world in (tracked, control):
                commands = [Command("throw")] if tick % 50 == 0 else []
                world.step(S.SIMULATION_STEP, InputFrame(Vector2(1,0), commands))
            assert tracked.player.position == control.player.position
            assert tracked.player.health == control.player.health
            assert tracked.stats == control.stats
            assert [(p.position,p.velocity) for p in tracked.projectiles] == [(p.position,p.velocity) for p in control.projectiles]
        assert store.db.execute("SELECT count(*) FROM events WHERE name='area_sample'").fetchone()[0] < 10
    finally:
        store.close()


def test_flow_transitions_projectile_miss_and_burst_expiry(tmp_path):
    store = ProfileStore(tmp_path / "journal")
    try:
        world = recorded_world(store)
        world.rewards.stored = "flow"
        world.step(.01, InputFrame(commands=[Command("burst"), Command("slash")]))
        for _ in range(90):
            world.step(S.SIMULATION_STEP, InputFrame())
        world.step(.01, InputFrame(commands=[Command("throw", Vector2(-1, 0))]))
        for _ in range(round(11 / S.SIMULATION_STEP)):
            world.step(S.SIMULATION_STEP, InputFrame())
        details = [json.loads(row[0]) for row in store.db.execute(
            "SELECT details FROM behaviour WHERE name='flow_transition' ORDER BY id")]
        assert [d["earned"] for d in details] == [False, True]
        miss = json.loads(store.db.execute(
            "SELECT details FROM performance WHERE name='projectile_missed'").fetchone()[0])
        assert miss["action_id"] == details[-1]["action_id"] and miss["owner"] == "player"
        assert store.db.execute("SELECT count(*) FROM behaviour WHERE name='burst_expired'").fetchone()[0] == 1
        assert store.profile() == scores([])
    finally:
        store.close()


def test_migration_interprets_existing_fork_without_replacing_events(tmp_path):
    path = tmp_path / "journal"
    db = sqlite3.connect(path)
    with db:
        for statement in MIGRATIONS[0]:
            db.execute(statement)
        db.execute(f"PRAGMA application_id={APPLICATION_ID}")
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO sessions(id,status) VALUES('s','quit')")
        db.execute("INSERT INTO runs VALUES('r','s','quit')")
        db.execute("INSERT INTO attempts(id,run,status) VALUES('a','r','quit')")
        context = json.dumps(dict(area="fork",level="temple_01",biome="grounds",difficulty="balanced"))
        for seq, name in enumerate(("route_offered","route_taken"), 1):
            db.execute("""INSERT INTO events(attempt,seq,seconds,name,kind,developer,schema_version,context,details)
                VALUES('a',?,?,?,'choice',0,1,?,?)""", (seq,seq,name,context,json.dumps(dict(fork="temple", branch="exposed", causeway_guards=2))))
    db.close()
    admin = ProfileStore(path, playing=False)
    try:
        assert admin.profile()["risk_appetite"]["score"] == 60
        assert admin.db.execute("SELECT count(*) FROM events").fetchone()[0] == 2
        assert admin.db.execute("SELECT count(*) FROM updates").fetchone()[0] == 1
    finally:
        admin.close()


def test_bolt_must_cross_previous_body_for_dash_avoidance(tmp_path):
    from shroud.combat import Projectile, resolve_enemy_projectile
    from shroud.player import PlayerState

    store = ProfileStore(tmp_path / "journal")
    try:
        world = recorded_world(store)
        world.before_move = Vector2(100, 100)
        world.player.position = Vector2(100, 160)
        world.player.state = PlayerState.DASHING
        bolt = Projectile(Vector2(50,100), Vector2(1,0), 1, "enemy", 500, "bolt")
        bolt.position = Vector2(150,100)
        resolve_enemy_projectile(world, bolt, stop_at=.1)
        assert store.db.execute("SELECT count(*) FROM performance").fetchone()[0] == 0
        resolve_enemy_projectile(world, bolt)
        resolve_enemy_projectile(world, bolt)
        assert store.db.execute("SELECT count(*) FROM performance WHERE name='dash_avoided_bolt'").fetchone()[0] == 1
        assert world.player.health == world.player.max_health and bolt.alive
    finally:
        store.close()


def test_actual_level_exit_and_advance_share_one_journey(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    store = ProfileStore(tmp_path / "journal")
    try:
        game = Game("temple_01", run_length=2, seed=4, profile_store=store)
        original = store.run, store.attempt
        for slot in (1, 2):
            world = game.world
            for enemy in world.enemies:
                deal_damage(world, enemy, 100, "slash")
            world.player.position = Vector2(world.room.exit_rect.center)
            world.step(.01, InputFrame())
            assert world.complete
            if slot == 1:
                assert game.advance() and (store.run, store.attempt) == original
        row = store.db.execute("SELECT * FROM run_summary").fetchone()
        assert row["status"] == "completed" and row["attempts"] == 1 and row["seconds"] == pytest.approx(.02)
        assert store.db.execute("SELECT count(*) FROM events WHERE name='level_completed'").fetchone()[0] == 2
    finally:
        store.close()
        pygame.quit()
