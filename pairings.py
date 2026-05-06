import random
from collections import defaultdict

def compute_standings(t):
    rows = {r.player_id: {"player": r.player, "tp":0.0, "kp":0.0, "wins":0, "losses":0, "draws":0, "opponents":[], "dropped": r.dropped} for r in t.registrations}
    for rnd in t.rounds:
        for m in rnd.matches:
            if not m.has_result: continue
            for pid, opid, tp, kp, opp_tp in [(m.player1_id, m.player2_id, m.p1_tp, m.p1_kp, m.p2_tp), (m.player2_id, m.player1_id, m.p2_tp, m.p2_kp, m.p1_tp)]:
                if pid is None or pid not in rows: continue
                rows[pid]["tp"] += tp or 0
                rows[pid]["kp"] += kp or 0
                if opid is not None: rows[pid]["opponents"].append(opid)
                if opp_tp is None: rows[pid]["wins"] += 1
                elif (tp or 0) > (opp_tp or 0): rows[pid]["wins"] += 1
                elif (tp or 0) < (opp_tp or 0): rows[pid]["losses"] += 1
                else: rows[pid]["draws"] += 1
    for row in rows.values():
        row["sos"] = sum(rows[oid]["tp"] for oid in row["opponents"] if oid in rows)
    standings = sorted(rows.values(), key=lambda r: (-r["tp"], -r["kp"], -r["sos"], r["player"].display_name.lower()))
    for i, row in enumerate(standings, 1):
        row["rank"] = i
    return standings

def all_results_in(rnd): return all(m.has_result for m in rnd.matches)

def previous_opponents(t):
    played = defaultdict(set)
    for rnd in t.rounds:
        for m in rnd.matches:
            if m.player2_id is not None:
                played[m.player1_id].add(m.player2_id)
                played[m.player2_id].add(m.player1_id)
    return played

def random_pairings(t):
    players = [r.player for r in t.registrations if not r.dropped]
    random.shuffle(players); return _pair_list(players)

def swiss_pairings(t):
    standings = compute_standings(t)
    ordered = [s["player"] for s in standings if not s["dropped"]]
    played = previous_opponents(t)
    pairings, used = [], set()
    for i, p in enumerate(ordered):
        if p.id in used: continue
        opp = next((q for q in ordered[i+1:] if q.id not in used and q.id not in played[p.id]), None)
        if opp is None: opp = next((q for q in ordered[i+1:] if q.id not in used), None)
        if opp is not None: pairings.append((p, opp)); used.update([p.id, opp.id])
        else: pairings.append((p, None)); used.add(p.id)
    return pairings

def _pair_list(players):
    pairs, it = [], iter(players)
    for p in it:
        try: pairs.append((p, next(it)))
        except StopIteration: pairs.append((p, None))
    return pairs
