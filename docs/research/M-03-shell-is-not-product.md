# M-03 — A 200 response is not a working application

**Methodology note. Permanent.**

## What was claimed, and what was true

Over two turns this project reported that Player Lab rendered five construct
cards, separated style from quality visually, drew percentile strips, encoded
estimator grade by border form and withheld gated values.

None of it had ever appeared on a screen. `strip()` interpolated an undeclared
`w` into its SVG viewBox and threw `ReferenceError` on its first call, inside the
loop that builds the quality cards. `showPlayer()` is `async`, so the throw
rejected a promise nobody awaited, `el.innerHTML` was never assigned, and
`#profile` kept its `hidden` class. The page showed a headline, a lede and a
search box over empty space — and did so for every player, every time.

## What the verification could actually prove

The check that produced the false confidence was:

    for ep in "/" "/api/meta" "/api/players?q=isco" ...; do
      curl -s -o /dev/null -w "%{http_code}" "$ep"
    done

Every endpoint returned 200, and the API data printed alongside was correct. All
of that was true. None of it was evidence about the thing being claimed.

`GET /` returns `web/index.html` from disk. FastAPI does not execute the script
inside it, and `curl` does not either. The response is 200 whether the JavaScript
runs perfectly or throws on line one. **The check was measuring the file server.**

The renderer tests added afterwards were better and still insufficient: they
called `strip()` in isolation under a stubbed DOM. They proved the function
worked. They could not prove the function was reached, that the promise resolved,
that the class was removed, or that the browser agreed.

## The inference that failed

Evidence from one system boundary was treated as evidence about another:

| Observed | Inferred | Valid? |
|---|---|---|
| 200 on `/` | the application works | no |
| API returns correct JSON | the page shows correct numbers | no |
| `strip()` returns markup under node | the profile renders in a browser | no |
| correct metric state | correctly communicated state | no |

Each inference skips a boundary where a real failure lives: script execution,
async resolution, CSS visibility, and human reading.

## The verification layers that now exist

**Renderer tests** (`tests/test_web_render.py`) execute the render functions under
node with a stubbed DOM. Fast, run pre-commit, catch semantic branches.

**Browser E2E** (`e2e/smoke.spec.js`) drives the real page in Chromium: search,
select, wait for async render, assert the profile becomes visible and contains the
player's name and every construct card. It fails on `pageerror`, on
`console.error`, and on failed resource requests, so
`ReferenceError: w is not defined` can never coexist with a green run again.

**Playwright owns the server.** The first E2E run reported a fix as failing
because it was talking to a stale uvicorn still holding the previous bundle in an
`lru_cache`. A test must never depend on a process it did not start — that is the
same class of error one layer up.

**Screenshots from the running app.** Looking at `01-profile.png` immediately
showed a defect no assertion had: the geometric-reference marker was a `<circle>`
inside a `preserveAspectRatio="none"` viewBox, stretched from 100 units to ~870
pixels, rendering as a wide gold lozenge that reads as exactly the filled
magnitude bar the geometric reference exists to prevent.

## The pattern, which has now recurred four times

- A licence test asserted UEFA belonged in the hostable set, encoding the wrong
  posture and locking it in.
- The pre-commit hook guarded licensing and not tests, so a commit went in red.
- An endpoint smoke test never executed the frontend.
- An E2E test ran against a server it did not start.

In every case the check existed and was well written. In every case it ran at the
wrong boundary.

> **Verification placement matters as much as verification existence.** A perfect
> test run manually once is weaker than a good test enforced at the failure
> boundary.

The corollary that keeps proving itself: when reporting that something works, name
the boundary the evidence came from. "The API returns the right JSON" and "the
page shows the right numbers" are different sentences, and only one of them was
ever checked.

