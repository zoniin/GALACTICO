"""How this season's numbers are gathered: the "About the numbers" section of the current-season
pages, for both apps.

Claim: every sentence here describes a rule the code applies (``openfootball``, ``openligadb``,
``freshness``, ``goal_scout``, ``scouting.opponent_groups``, ``studio``) in plain words; it
names no club, no player and no number the data does not fix. The hosted app hands this section
to the shell (``app.state.about_sections``); the full local app lists it after the archive's.

Non-claim: it says nothing about why a feed lags or when a result will arrive. The hosted app
cannot import the copy guard (``galactico.domain``); a test reads the section through
``scan_labels``.
"""

from __future__ import annotations

import html

from ..site_nav import Section

__all__ = ["CURRENT_ANSWERS", "POINTS", "current_season"]

CURRENT_ANSWERS = "how this season's results, tables and goals are gathered"
"""The clause of the page's opening sentence that this section answers."""

POINTS: tuple[tuple[str, str], ...] = (
    ("Results and tables",
     "Fixtures, results and league tables come from OpenFootball's free files, which "
     "volunteers update after play, so results can arrive days or weeks late. Each page says "
     "how far a competition's results reach (\"Results through Sun 20 Sep\"): the latest date "
     "with a reported result. A later fixture without a result is counted as missing, never "
     "guessed, and a table whose results stop early says which matchday it is after."),
    ("Filled-in results",
     "Bundesliga and Premier League results missing from OpenFootball are filled in from "
     "OpenLigaDB, a community feed, once both clubs and the matchday match. A result "
     "OpenFootball already has is never replaced, and a filled-in result takes the date "
     "OpenLigaDB gives the match."),
    ("Champions League",
     "Champions League fixtures, results and scorers come from OpenLigaDB alone. Its table is "
     "the league phase, ordered by points, goal difference and goals scored. Clubs take the "
     "name OpenFootball gives them, or the English form."),
    ("Scorers",
     "Scorers and minutes are OpenLigaDB's, for the Champions League, the Premier League and "
     "the Bundesliga. The free La Liga, Serie A and Ligue 1 feeds don't name scorers. Where "
     "the feed lists one player under two forms of his name (\"N. Jackson\" and \"Nicolas "
     "Jackson\"), his goals are counted once; different initials are never joined."),
    ("Goals by opponent",
     "Each match goes in a group by the opponent's place before kick-off, from a table of "
     "that competition's results dated before the match: places 1-6, places 7 and below, or "
     "not classified. A match is not classified while any club has played fewer than five "
     "games, or when the opponent is level on sixth place."),
    ("Squad, appearances and goals",
     "The squad, each player's appearances and his goals come from the Wikipedia article on "
     "Real Madrid's season, in all competitions, as of the article's last edit, which the "
     "pages date. The proposed lineup puts each player where the first position in his own "
     "Wikipedia article places him, else by shirt number."),
)
"""Each rule as the section states it: a short heading and one paragraph."""


def current_season() -> Section:
    """The section, its body escaped markup the server wrote."""
    items = "".join(f"<li><strong>{html.escape(head)}.</strong> {html.escape(text)}</li>"
                    for head, text in POINTS)
    body = f'<ul class="about-list">{items}</ul>'
    return Section("this-season", "This season's results, tables and goals", body,
                   answers=CURRENT_ANSWERS)
