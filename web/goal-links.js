// A link that opens Goals by opponent (scouting.html) on one club of one competition, with the
// explorer's other choices (the opponent group, a scorer, an opponent) where a view has them.
export function scoutLink(league, club, filters = {}, base = '/match-centre/scouting') {
  const url = new URL(base, location.origin);
  url.searchParams.set('goalsLeague', league);
  url.searchParams.set('goalsClub', club);
  for (const [key, value] of Object.entries(filters)) {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }
  url.searchParams.delete('goalsPeer');
  url.hash = 'goals';
  return url;
}
