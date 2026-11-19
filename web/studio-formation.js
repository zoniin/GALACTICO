// Coordinates describe the tactics board with the opponent's goal at the top.
const forward = (role, x, y) => ({ role, x, y, group: 'FW' });
const mid = (role, x, y) => ({ role, x, y, group: 'MF' });
const back = (role, x, y) => ({ role, x, y, group: 'DF' });
const keeper = { role: 'GK', x: 50, y: 88, group: 'GK' };
const four = [back('LB', 13, 68), back('LCB', 37, 71), back('RCB', 63, 71), back('RB', 87, 68)];
export const shapes = {
  '4-3-3': [
    forward('LW', 20, 19),
    forward('ST', 50, 13),
    forward('RW', 80, 19),
    mid('LCM', 24, 42),
    mid('DM', 50, 50),
    mid('RCM', 76, 42),
    ...four,
    keeper,
  ],
  '4-2-3-1': [
    forward('ST', 50, 12),
    mid('LAM', 17, 31),
    mid('AM', 50, 34),
    mid('RAM', 83, 31),
    mid('LDM', 33, 52),
    mid('RDM', 67, 52),
    ...four,
    keeper,
  ],
  '4-4-2': [
    forward('LS', 36, 16),
    forward('RS', 64, 16),
    mid('LM', 13, 42),
    mid('LCM', 37, 47),
    mid('RCM', 63, 47),
    mid('RM', 87, 42),
    ...four,
    keeper,
  ],
  '3-5-2': [
    forward('LS', 36, 15),
    forward('RS', 64, 15),
    mid('LWB', 12, 43),
    mid('LCM', 32, 39),
    mid('DM', 50, 54),
    mid('RCM', 68, 39),
    mid('RWB', 88, 43),
    back('LCB', 25, 71),
    back('CB', 50, 73),
    back('RCB', 75, 71),
    keeper,
  ],
};

// An editable editorial starting shape. Only players returned by the current roster can enter it.
const preferred = {
  LW: 'Vinícius_Júnior',
  ST: 'Kylian_Mbappé',
  RW: 'Rodrygo',
  LCM: 'Jude_Bellingham',
  DM: 'Aurélien_Tchouaméni',
  RCM: 'Federico_Valverde',
  LB: 'Álvaro_Carreras',
  LCB: 'Antonio_Rüdiger',
  RCB: 'Éder_Militão',
  RB: 'Trent_Alexander-Arnold',
  GK: 'Thibaut_Courtois',
};
export const positions = { GK: 'Goalkeeper', DF: 'Defender', MF: 'Midfielder', FW: 'Forward' };
export function initialXI(players) {
  const slots = shapes['4-3-3'];
  const chosen = slots.map((s) => players.find((p) => p.id === preferred[s.role])?.id ?? null);
  const pool = [...players].sort((a, b) => (b.apps ?? -1) - (a.apps ?? -1) || a.number - b.number);
  for (const [i, s] of slots.entries()) {
    if (chosen[i]) continue;
    const available = pool.filter((p) => !chosen.includes(p.id));
    chosen[i] = (available.find((p) => p.group === s.group) || available[0])?.id ?? null;
  }
  return chosen;
}
export function reshape(lineup, before, after) {
  const previous = shapes[before],
    target = shapes[after];
  const sourceByRole = new Map(previous.map((slot, index) => [slot.role, index]));
  const sourceForTarget = target.map((slot) => sourceByRole.get(slot.role) ?? -1);
  const remaining = previous.filter((_, index) => !sourceForTarget.includes(index));
  const open = target.filter((_, index) => sourceForTarget[index] === -1);
  const lines = { GK: 0, DF: 1, MF: 2, FW: 3 };
  // Choose the least disruptive assignment across the entire shape. A greedy
  // wide-role pick can otherwise leave a forward as the last available centre-back.
  const memo = new Map();
  function best(index, used) {
    if (index === open.length) return { cost: 0, slots: [] };
    if (memo.has(used)) return memo.get(used);
    const destination = open[index];
    let winner = { cost: Infinity, slots: [] };
    for (const [j, origin] of remaining.entries()) {
      if (used & (1 << j)) continue;
      const rest = best(index + 1, used | (1 << j));
      const cost =
        rest.cost +
        Math.hypot(destination.x - origin.x, destination.y - origin.y) +
        45 * (lines[destination.group] - lines[origin.group]) ** 2;
      if (cost < winner.cost) winner = { cost, slots: [origin, ...rest.slots] };
    }
    memo.set(used, winner);
    return winner;
  }
  const origins = best(0, 0).slots;
  open.forEach((slot, i) => sourceByRole.set(slot.role, previous.indexOf(origins[i])));
  return target.map((slot) => lineup[sourceByRole.get(slot.role)]);
}
export function shortName(player) {
  const parts = player.name.split(' ');
  if (parts.length === 2 && ['Júnior', 'Junior', 'Silva'].includes(parts[1])) return player.name;
  return parts.at(-1);
}
