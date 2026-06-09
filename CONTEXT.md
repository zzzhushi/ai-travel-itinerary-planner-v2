# Travel Itinerary Planner

A locally-run, Gemini-powered planner. Given a city, a number of days, and a
traveller's preferences, it helps them gather candidate places to visit and then
generates a day-by-day schedule that minimises back-and-forth travel across the city.

## Language

**Trip**:
A single planning session: one city, a fixed number of days, and the traveller's
preferences. Owns its Categories, Interests, Options, and the generated Schedule.

**Category**:
A top-level grouping of things to do, chosen during trip setup (e.g. Food, Culture,
Sightseeing). The planner offers common defaults; the traveller may add their own.

**Interest**:
A specific thing the traveller types under a Category (e.g. "ramen" under Food,
"live jazz" under Culture). Drives what the LLM searches for.
_Avoid_: activity (overloaded — sometimes meant the category, sometimes the interest).

**Option**:
A concrete, named place or experience the LLM proposes for an Interest (e.g. a
specific ramen shop). The traveller researches and rates Options. Schedules are
built from Chosen Options.
_Avoid_: result, suggestion, candidate.

**Rating**:
A 1–5 star score the traveller gives an Option. Below 3 excludes the Option from
scheduling; the highest ratings are force-included even at a travel cost. Drives the
`w_rank` priority used when trimming oversupply.

**Chosen**:
The set of Options rated 3 or above — the candidates the scheduler may place. Distinct
from what actually lands in the Schedule, which also depends on Capacity and travel fit.

**Capacity**:
How many Options the trip can hold: days × slots-per-day, where slots-per-day comes from
pace (relaxed ≈ 3, packed ≈ 6), minus a partial day 1 anchored at arrival. When Chosen
exceeds Capacity it is **oversupply** (trim lowest ratings); below it, **undersupply**
(the gate advises gathering more). The "enough options" gate is advisory, never blocking.

**Home Base**:
The trip's lodging location. Every day's Schedule starts and ends here, and travel to and
from it counts toward the day. One per trip for now.
_Avoid_: hotel, accommodation (a hotel is one kind of Home Base).

**Pinned Commitment**:
A fixed time + place item the traveller must attend — a user-added event (a wedding), a
timed/locked ticket, or a flight. The scheduler places it at its exact time and routes the
day around it; regenerating the Schedule never moves it.
_Avoid_: locked item, fixed event, appointment.

**Anchor**:
Any fixed point the scheduler must build around — a Home Base, a Pinned Commitment, or a
long-duration Option. Anchors exert spatial gravity: nearby Options are preferred for the
surrounding time slots (so 3 hours at one place pulls in things in that area).

**Schedule**:
The generated day-by-day plan: chosen Options placed into time slots across the trip's
days, starting and ending each day at Home Base, ordered to minimise travel and clustered
around Anchors.
