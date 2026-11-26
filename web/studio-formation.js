// The board's formations come from the server (galactico/match_centre/studio.py), with the XI
// it proposes for each. This module only moves a lineup the reader edited from one formation to
// another: each player keeps his role where the new formation has it; the rest go to the places
// of their own position (goalkeeper, defender, midfielder, forward) first, and move as little
// as they can across the whole shape. A defender is never put in a midfield or forward place
// while a place of his own position is open to him.
export const positions = { GK: 'Goalkeeper', DF: 'Defender', MF: 'Midfielder', FW: 'Forward' };
export const groupNames = { GK: 'Goalkeepers', DF: 'Defenders', MF: 'Midfielders', FW: 'Forwards' };

const LINES = { GK: 0, DF: 1, MF: 2, FW: 3 };

export function reshape(lineup, previous, target, groupOf = () => null) {
  // A player's own position: his squad position where it is known, else his place's.
  const own = (index) => groupOf(lineup[index]) || previous[index].group;
  const sourceByRole = new Map(previous.map((slot, index) => [slot.role, index]));
  const sourceForTarget = target.map((slot) => {
    const index = sourceByRole.get(slot.role);
    return index != null && own(index) === slot.group ? index : -1;
  });
  const remaining = previous.map((_, index) => index).filter((index) => !sourceForTarget.includes(index));
  const open = target.map((_, index) => index).filter((index) => sourceForTarget[index] === -1);
  // The least disruptive assignment across the whole shape: a place of another position costs
  // far more than any distance, and a line further away more than a nearer one.
  const memo = new Map();
  function cheapest(at, used) {
    if (at === open.length) return { cost: 0, picks: [] };
    const key = at + ':' + used;
    if (memo.has(key)) return memo.get(key);
    const destination = target[open[at]];
    let winner = { cost: Infinity, picks: [] };
    for (const [j, origin] of remaining.entries()) {
      if (used & (1 << j)) continue;
      const rest = cheapest(at + 1, used | (1 << j));
      const from = previous[origin];
      const group = own(origin);
      const cost =
        rest.cost +
        Math.hypot(destination.x - from.x, destination.y - from.y) +
        45 * (LINES[destination.group] - LINES[group]) ** 2 +
        (group === destination.group ? 0 : 1000);
      if (cost < winner.cost) winner = { cost, picks: [origin, ...rest.picks] };
    }
    memo.set(key, winner);
    return winner;
  }
  const picks = cheapest(0, 0).picks;
  const result = target.map((_, index) => (sourceForTarget[index] >= 0 ? lineup[sourceForTarget[index]] : null));
  open.forEach((index, i) => {
    result[index] = lineup[picks[i]];
  });
  return result;
}
