export function scorer(event, league) {
  // Two OpenLigaDB records for Madrid's Mbappé use his full and abbreviated names.
  if (
    league === 'La Liga' &&
    event.team === 1133 &&
    [19243, 19649].includes(event.player) &&
    /Mbappé$/u.test(event.name)
  ) {
    return { id: 'mbappe', name: 'Kylian Mbappé' };
  }
  return { id: String(event.player || event.name), name: event.name };
}

export function scoutLink(league, club, filters = {}, base = '/match-centre/scouting') {
  const url = new URL(base, location.origin);
  url.searchParams.set('goalsLeague', league);
  url.searchParams.set('goalsClub', club);
  for (const [key, value] of Object.entries(filters)) {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }
  url.hash = 'goals';
  return url;
}
