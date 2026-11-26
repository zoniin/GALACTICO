// The board's formations come from the server (galactico/match_centre/studio.py), with the XI
// it proposes for each. This module only moves a lineup from one formation to another: each
// player keeps his role where the new formation has it, and the rest move as little as they
// can across the whole shape.
export const positions = { GK: 'Goalkeeper', DF: 'Defender', MF: 'Midfielder', FW: 'Forward' };
export const groupNames = { GK: 'Goalkeepers', DF: 'Defenders', MF: 'Midfielders', FW: 'Forwards' };

export function reshape(lineup, previous, target) {
  const sourceByRole = new Map(previous.map((slot, index) => [slot.role, index]));
  const sourceForTarget = target.map((slot) => sourceByRole.get(slot.role) ?? -1);
  const remaining = previous.filter((_, index) => !sourceForTarget.includes(index));
  const open = target.filter((_, index) => sourceForTarget[index] === -1);
  const lines = { GK: 0, DF: 1, MF: 2, FW: 3 };
  // Choose the least disruptive assignment across the entire shape. A greedy
  // wide-role pick can otherwise leave a forward as the last available centre-back.
  const memo = new Map();
  function cheapest(index, used) {
    if (index === open.length) return { cost: 0, slots: [] };
    if (memo.has(used)) return memo.get(used);
    const destination = open[index];
    let winner = { cost: Infinity, slots: [] };
    for (const [j, origin] of remaining.entries()) {
      if (used & (1 << j)) continue;
      const rest = cheapest(index + 1, used | (1 << j));
      const cost =
        rest.cost +
        Math.hypot(destination.x - origin.x, destination.y - origin.y) +
        45 * (lines[destination.group] - lines[origin.group]) ** 2;
      if (cost < winner.cost) winner = { cost, slots: [origin, ...rest.slots] };
    }
    memo.set(used, winner);
    return winner;
  }
  const origins = cheapest(0, 0).slots;
  open.forEach((slot, i) => sourceByRole.set(slot.role, previous.indexOf(origins[i])));
  return target.map((slot) => lineup[sourceByRole.get(slot.role)]);
}
