# GLEE agent notebook

For the newest score-oriented version, use [`GLEE_Competition_agent_v3.ipynb`](GLEE_Competition_agent_v3.ipynb). It adds bounded opponent models, continuation-value decisions, hidden-value concession inference, direct recommendation-precision learning, finite credibility budgeting, schema validation, and safe fallbacks. V2 and the original quickstart remain available for comparison.

[`GLEE_Competition_—_agent_quickstart.ipynb`](GLEE_Competition_—_agent_quickstart.ipynb) is a zero-setup agent for all three GLEE game families. It separates the policy into one function per family and exposes one dispatcher to the SDK:

$$
\pi(g)=\pi_f(g), \qquad f=\text{the game's family}.
$$

Here, the family $f$ is read from `game["game_family"]`.

This modular design makes it possible to tune and test one family without changing the others.

## Notebook comparison

| Notebook | Purpose | Main additions |
|---|---|---|
| [`GLEE_Competition_—_agent_quickstart.ipynb`](GLEE_Competition_—_agent_quickstart.ipynb) | Transparent reference policy | Game-theoretic targets, deadline awareness, Bayesian signal learning |
| [`GLEE_Competition_agent_v2.ipynb`](GLEE_Competition_agent_v2.ipynb) | First score-oriented agent | Persistent opponent profiles, aggressive surplus capture, finite-horizon reputation management, validation and fallbacks |
| [`GLEE_Competition_agent_v3.ipynb`](GLEE_Competition_agent_v3.ipynb) | Recommended adaptive agent | Bounded demand learning, continuation values, hidden-value concession inference, direct signal-precision learning, credibility budgeting |

All three are rule-based and require no LLM inference. Each reads only the game state visible under the competition's information rules.

## Common notation and constraints

Let $M$ denote the bargaining pot, $x_A$ and $x_B$ the two allocations, $v_s$ the seller's reservation value, $v_b$ the buyer's valuation, $P$ a negotiated or fixed product price, and $t\in[0,1]$ normalized progress toward a known deadline.

Every bargaining offer must satisfy

$$
x_A+x_B=M.
$$

Negotiation utilities and feasible surplus are

$$
U_s(P)=P-v_s,
\qquad
U_b(P)=v_b-P,
\qquad
S=v_b-v_s.
$$

A trade is individually rational only when the acting player's utility is non-negative. On the final round, all notebooks accept a profitable negotiation offer because continuation value is zero.

## Quickstart methods

### Bargaining

Under complete information, the proposer starts from the Rubinstein alternating-offers solution. If $d_p$ and $d_r$ are the proposer and responder discount multipliers, the proposer's reference share is

$$
s_p=\frac{1-d_r}{1-d_pd_r}.
$$

The actual share moves toward one half as the deadline approaches. Under incomplete information, the proposer begins near a 58% personal share and gradually concedes. A responder accepts when the current gain $x_i$ reaches the discounted value of proposing next:

$$
x_i \ge d_i M s_i^{\mathrm{next}}.
$$

### Negotiation

With both valuations visible, the quickstart uses a midpoint target with a temporary first-mover advantage:

$$
P_t^{\mathrm{seller}}=v_s+0.5S+0.15S(1-t),
$$

$$
P_t^{\mathrm{buyer}}=v_s+0.5S-0.15S(1-t).
$$

With hidden values, role-specific valuation anchors replace the full-information surplus calculation. After rejection, the counteroffer is blended toward the opponent's latest price with increasing weight near the deadline.

### Persuasion

The buyer estimates the seller's positive-signal rates $q_H=P(m^+\mid H)$ and $q_L=P(m^+\mid L)$ from revealed outcomes using Beta smoothing. After a positive signal, Bayes' rule gives

$$
\widehat p=P(H\mid m^+)=\frac{p q_H}{p q_H+(1-p)q_L}.
$$

Posterior expected value is

$$
\mathbb{E}[V\mid m]=\widehat p v+(1-\widehat p)u.
$$

The decision rule is deliberately written without a `cases` environment for compatibility with GitHub and notebook Markdown renderers:

$$
\mathrm{buy}=\mathrm{yes}
\quad\Longleftrightarrow\quad
\mathbb{E}[V\mid m]\ge P;
\qquad
\mathrm{buy}=\mathrm{no}\ \text{otherwise}.
$$

The seller always recommends high quality. When $u<P<v$, it can pool some low-quality products while preserving the buyer's purchase threshold. If

$$
c=\frac{P-u}{v-u},
$$

the maximum static low-quality pooling probability is

$$
q_L^*=\frac{p(1-c)}{c(1-p)},
$$

clipped to $[0,1]$.

## V2 methods

### Bargaining: acceptance-probability optimization

V2 records the largest opponent share that the opponent rejected, denoted $r_{\max}$. It combines that evidence with a configuration-aware prior to form a threshold $\tau$. Candidate responder shares $s$ receive logistic acceptance probabilities

$$
a(s)=\frac{1}{1+\exp\left(-\frac{s-\tau+0.04}{0.02}\right)}.
$$

The proposer searches for the share maximizing probability-weighted, mildly convex personal payoff:

$$
s^*=\underset{s}{\operatorname{argmax}}\;a(s)(1-s)^{1.25}.
$$

As responder, V2 compares the current allocation with a discount-adjusted estimate of the payoff from rejecting and proposing next.

### Negotiation: asymmetric surplus capture

Under complete information, V2 targets the personal surplus fraction

$$
c_t=0.85-0.25t.
$$

The seller target is $P_t=v_s+c_tS$; the buyer target is $P_t=v_s+(1-c_t)S$. Under hidden information, observed opponent prices replace some fixed valuation anchors. Acceptance requires non-negative utility and a decreasing fraction of target utility:

$$
U_{\mathrm{offer}}\ge (0.90-0.25t)U_{\mathrm{target}}.
$$

### Persuasion: Bayesian trust and finite-horizon pooling

V2 carries Beta-smoothed estimates of $q_H$ and $q_L$ across games against disclosed sellers. Its seller protects reputation early and approaches the static pooling rate near the end:

$$
q_{L,t}=q_L^*\left(0.15+0.85t^{1.5}\right).
$$

The buyer applies Bayes' rule to positive and negative signals and adds a small information bonus when an early purchase can reveal seller reliability.

## V3 methods

### Bargaining: bounded demand learning

V3 augments rejection evidence with the opponent's recent demanded shares. Its estimated acceptance floor is

$$
\tau_t=\operatorname{clip}\!\left(
\max\{\tau_{\mathrm{prior}},\ r_{\max}+0.012,\ \operatorname{median}(d)-\mu_t\},
0.30,0.62
\right),
$$

where $d$ contains recent opponent demands and $\mu_t$ is a shrinking aspiration margin. It evaluates each proposed responder share using

$$
J(s)=a(s)(1-s)^{1.18}-\bigl(1-a(s)\bigr)C_t,
$$

where $C_t$ increases with deadline pressure and delay cost. The responder accepts when the current allocation is at least the larger of a risk floor and the discounted, probability-adjusted payoff from proposing next.

### Negotiation: concession inference inside the feasible interval

Under complete information, V3 starts with a less brittle capture schedule than V2:

$$
c_t=0.74-0.14t.
$$

Observed opponent offers adjust this target. With hidden values, V3 does not multiply beyond an opponent's revealed price. If a seller with value $v_s$ observes buyer price $P_o\ge v_s$, its target is

$$
P_t=v_s+c_t(P_o-v_s).
$$

If a buyer with value $v_b$ observes seller price $P_o\le v_b$, its target is

$$
P_t=v_b-c_t(v_b-P_o).
$$

Thus the counteroffer remains inside the interval already shown to be individually rational for the agent. Acceptance compares offered utility with risk-adjusted continuation utility rather than demanding the full target.

### Persuasion: direct precision learning and credibility budgeting

Purchase history is censored because the buyer normally learns quality only after buying. Instead of treating that history as an unbiased estimate of $P(m\mid H)$ and $P(m\mid L)$, V3 directly estimates the decision-relevant precision $P(H\mid m)$. For a positive signal, it shrinks observed counts toward a strategic prior:

$$
\widehat\rho_+=\frac{\kappa\rho_{+,0}+n_{+,H}}{\kappa+n_{+,H}+n_{+,L}},
$$

where $\kappa=4$, $n_{+,H}$ and $n_{+,L}$ count revealed high- and low-quality positive recommendations, and

$$
\rho_{+,0}=\frac{0.90p}{0.90p+0.24(1-p)}.
$$

The buyer substitutes $\widehat\rho_+$ directly for $P(H\mid m^+)$ in the expected-value rule. Negative signals use analogous priors.

As seller, V3 scales the static pooling probability by deadline progress and observed buyer response:

$$
q_{L,t}=\operatorname{clip}\!\left(
q_L^*\left(0.12+0.88t^{1.65}\right)
\left(0.55+0.60r_{\mathrm{buy}}\right),0,1
\right).
$$

A low-quality positive signal is permitted only after a short truthful prefix and only if the resulting empirical positive-signal precision remains above the buyer's value threshold plus a safety margin. This is V3's finite credibility budget.

## Safety and limitations

- V2 and V3 validate every proposed action and use conservative legal fallbacks after unexpected schemas or strategy exceptions.
- Stable hashes make persuasion mixing reproducible across concurrent games.
- Named opponents receive cross-game profiles; hidden identities receive only game-local profiles.
- No hand-coded strategy guarantees a rating increase. Matchmaking, configuration draws, opponent adaptation, and rating shrinkage create substantial short-run variance.
- V3's opponent models learn only from states delivered while a move is pending; a game-ending acceptance may not produce another strategy call.

## Architecture and execution

The `STRATEGIES` dictionary maps each family name to its policy. The common `strategy(game)` function performs the dispatch, while `GleeClient.run(...)` handles matchmaking, polling, move submission, retries, and graceful draining of in-flight games.

Useful execution controls include:

```python
# Tune a single family.
client.run(strategy, game_families=["bargaining"], max_games=3)

# Play several games concurrently in a bounded session.
client.run(strategy, concurrency=8, max_games=20, max_time=600)
```

The notebook's effective decision pipeline is:

$$
\text{game state}
\rightarrow \text{family dispatcher}
\rightarrow \text{family policy}
\rightarrow \text{legal action}.
$$

## Results snapshot

Results rendered before and after a `GLEE_Competition_agent_v3.ipynb` evaluation batch on August 25, 2026:

| Game family | Before rating | Before games | After rating | After games | Rating change |
|---|---:|---:|---:|---:|---:|
| Bargaining | 1250.54 | 50 | **1305.87** | 72 | **+55.33** |
| Negotiation | 1162.31 | 50 | **1243.31** | 72 | **+81.00** |
| Persuasion | 1728.01 | 357 | **1756.91** | 379 | **+28.90** |

The batch completed 22 additional games per family, or 66 total. The unweighted three-family average rose from **1380.29** to **1435.36**, a change of **+55.08**.

- **Agent:** `myagent`
- **Agent ID:** `9edb52a0-b489-44bd-b594-af77cdba5597`
- **Active games:** 0

All three displayed ratings increased during this batch. Ratings are live, however, and this single before/after observation does not isolate policy quality from opponent mix, configuration draws, rating shrinkage, or normal variance.

## Evaluation and further improvement

- A/B test one family at a time and record the rating and game count immediately before and after each sufficiently large batch.
- Calibrate V3's bargaining acceptance curve and negotiation continuation discount from observed outcomes rather than changing several constants together.
- Retrieve completed games after each bounded run, when practical, so terminal acceptances can supplement the profiles that are learned only from pending-move states.
- Replace point estimates with credible intervals and choose more conservative actions when opponent evidence is sparse.
- Segment priors by disclosed opponent type only after enough samples exist to avoid overfitting identities or short streaks.
- Introduce an LLM only for genuinely ambiguous text messages, retaining the deterministic validated fallback for latency and schema safety.

## Security

Keep the API key outside the notebook and repository:

```python
import os
from getpass import getpass

os.environ["GLEE_API_KEY"] = getpass("GLEE API key: ")
```

If a real key has ever been saved in a notebook, revoke it in the GLEE dashboard, create a replacement, and clear the notebook's saved outputs before publishing.

## References

- [GLEE Competition](https://glee-competition.com/)
- [GLEE Competition documentation](https://glee-competition.com/docs)
- [Official `glee-sdk` guide](https://github.com/eilamshapira/GLEE_competition/blob/main/sdk/README.md)
- [GLEE paper](https://arxiv.org/abs/2410.05254)
