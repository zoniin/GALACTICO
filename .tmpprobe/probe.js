(async () => {
  const d = await fetch('/api/players?q=modric&limit=1').then(r=>r.json());
  try { await showPlayer(d.players[0].player_id); return 'RENDERED len=' + document.getElementById('profile').innerHTML.length; }
  catch(e){ return 'THREW: ' + e; }
})()
