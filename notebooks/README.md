# GLEE agent notebook

Use a family-specific portfolio rather than assuming the newest notebook is uniformly superior: V4 remains the bargaining reference, V3 remains the persuasion reference, and V5/V8 remains the negotiation decision core. V11 did not change that core, but its large-batch runner lost 44.84 negotiation points over 53 games after requesting 24 at concurrency 4. V11 is therefore rejected operationally; use very small, concurrency-1 checkpoints instead.

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
| [`GLEE_Competition_agent_v3.ipynb`](GLEE_Competition_agent_v3.ipynb) | Live-tested adaptive reference | Bounded demand learning, continuation values, hidden-value concession inference, direct signal-precision learning, credibility budgeting |
| [`GLEE_Competition_agent_v4.ipynb`](GLEE_Competition_agent_v4.ipynb) | Bargaining-tested history-calibrated agent | Uncapped visible equilibrium, cycle escape, trend-aware negotiation, role-separated persuasion memory, hidden-value seller exploration |
| [`GLEE_Competition_agent_v5.ipynb`](GLEE_Competition_agent_v5.ipynb) | Negotiation-tested role-calibrated agent | Alice payoff shading, buyer-specific negotiation capture, capped stale trust, recency weighting, sequential seller credibility spending |
| [`GLEE_Competition_agent_v6.ipynb`](GLEE_Competition_agent_v6.ipynb) | Safety-strengthened experimental agent; persuasion rejected | Configuration-scoped profiles, purchased-only trust updates, credibility scheduling, negation-aware text parsing, strict contract validation |
| [`GLEE_Competition_agent_v7.ipynb`](GLEE_Competition_agent_v7.ipynb) | Live-tested conservative portfolio | Protected V4/V5/V3 arms, whole-game arm assignment, 12% bounded exploration, 40/40 bargaining agreements, completed-game reward credit, confidence-bound promotion |
| [`GLEE_Competition_agent_v8.ipynb`](GLEE_Competition_agent_v8.ipynb) | Role-gated checkpoint learner | Frozen V5 negotiation and V3 buyer, frozen Bob, Alice/seller-only exploration, persistent evidence, six-game checkpoints, clean fallback/telemetry separation; negotiation +50.96 over 44 games |
| [`GLEE_Competition_agent_v9.ipynb`](GLEE_Competition_agent_v9.ipynb) | Champion-locked controlled agent | Champion-mode default, one-completion requests, exact evidence export; no separately identified live batch |
| [`GLEE_Competition_agent_v10.ipynb`](GLEE_Competition_agent_v10.ipynb) | Rating-aligned conservative optimizer | Actual rating-delta evidence, one-game attribution guard, negotiation +3.03 over two overshot completions |
| [`GLEE_Competition_agent_v11.ipynb`](GLEE_Competition_agent_v11.ipynb) | Large-batch runner; rejected operationally | Requested 24 games at concurrency 4, completed 53, negotiation -44.84 despite zero fallbacks |

All notebook policies are rule-based and require no LLM inference. Each reads only the game state visible under the competition's information rules.

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

Define the probability-weighted, mildly convex personal payoff

$$
F(s)=a(s)(1-s)^{1.25}.
$$

The selected share $s^*$ satisfies

$$
F(s^*)=\max_{0.20\le s\le 0.65}F(s).
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

V3 augments rejection evidence with the opponent's recent demanded shares. Let $\widetilde d$ denote the median of the recent demands. Its bounded acceptance floor is

$$
\tau_t=\min\!\left(
0.62,
\max\!\left(0.30,\tau_{\mathrm{prior}},r_{\max}+0.012,\widetilde d-\mu_t\right)
\right).
$$

Here $\mu_t$ is a shrinking aspiration margin. V3 evaluates each proposed responder share using

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

As seller, V3 first computes a raw pooling rate from deadline progress and observed buyer response:

$$
z_t=q_L^*\left(0.12+0.88t^{1.65}\right)
\left(0.55+0.60r_{\mathrm{buy}}\right).
$$

It then bounds that rate to a valid probability:

$$
q_{L,t}=\min\!\left(1,\max\!\left(0,z_t\right)\right).
$$

A low-quality positive signal is permitted only after a short truthful prefix and only if the resulting empirical positive-signal precision remains above the buyer's value threshold plus a safety margin. This is V3's finite credibility budget.

## V4 methods

### Bargaining: uncapped visible equilibrium and cycle escape

V3 bounded the complete-information responder prior near one half. The saved history showed that this was inappropriate when the proposer discounted at 10% per round and the responder did not discount: the Rubinstein responder share was close to one, but V3 repeatedly offered only 65%. V4 retains the visible equilibrium without that fairness cap:

$$
s_r=1-\frac{1-d_r}{1-d_pd_r},
\qquad
0.001\le s_r\le 0.999.
$$

Its candidate grid extends to a 99.5% responder share. V4 also counts repeated, nearly identical demands by both players. After at least three stagnant cycles, the proposer matches the opponent's last revealed demand within the legal allocation range. As responder, it accepts any strictly positive allocation after the same repeated-state threshold. This turns a persistent zero-payoff loop into a terminating outcome while leaving ordinary finite bargaining unchanged.

### Negotiation: projected concessions and safe stall termination

For hidden-value negotiation, V4 projects only concessions in the economically expected direction. If the opponent's two latest prices are $P_{o,t-1}$ and $P_{o,t}$, its short projection is

$$
\widetilde P_{o,t+1}=P_{o,t}+0.6\Delta_t,
\qquad
\Delta_t=P_{o,t}-P_{o,t-1},
$$

where a seller's $\Delta_t$ is capped above by zero and a buyer's is capped below by zero. The target stays inside the interval between this projected price and the agent's own valuation. V4 uses a hidden-value claim beginning near 70% as seller and 62% as buyer, reflecting the V3 history's weaker buyer results.

If two profitable prices repeat, V4 accepts instead of preserving a zero-surplus cycle. If an unprofitable pair repeats at least three times in an unknown-horizon game, it uses `WalkAway`. This does not convert a negative-utility trade into an agreement; it safely terminates an infeasible path that would otherwise risk a timeout.

### Persuasion: role-separated memory and hidden-value seller adaptation

V3 keyed persuasion memory only by opponent identity. If the same named opponent appeared once as buyer and later as seller, the agent could treat its own past recommendations as evidence about that opponent's reliability. V4 uses two namespaces:

$$
\mathcal M_{\mathrm{buyer\ response}}
\quad\text{and}\quad
\mathcal M_{\mathrm{seller\ reliability}}.
$$

The buyer retains V3's direct precision estimator because the V3 batch averaged $+4.09$ per game in that role. The seller changes more substantially. With visible buyer values, it uses the Bayesian pooling bound but begins from a less conservative horizon ramp:

$$
q_{L,t}=q_L^*\left(0.28+0.72t^{1.35}\right)
\left(0.60+0.55r_{\mathrm{buy}}\right),
$$

subject to credibility and probability bounds. When buyer values are hidden, V4 permits cautious low-quality exploration only after a truthful prefix, at least one revealed successful high-quality recommendation, sufficient positive-message purchase response, and adequate empirical precision. The hidden-value exploration probability never exceeds 0.34.

## V5 methods

### Bargaining: Alice calibration with V4 cycle insurance

V4's 25-game bargaining batch reached agreement in every game, but Alice averaged $-0.10$ rounded rating change while Bob averaged $+2.94$. V5 therefore changes only pre-stall aggressiveness. If $\tau_t$ is V4's responder floor, the offer search uses

$$
\tau_t^{\mathrm{search}}=
\tau_t-\epsilon_i,
$$

with $\epsilon_A=0.018$ for Alice and $\epsilon_B=0.006$ for Bob. Alice's personal payoff exponent increases from 1.15 to 1.22, and her modeled rejection cost is multiplied by 0.40 before a stall. In the reconstructed extreme-discount state, this changes the initial split from V4's 0.5/99.5 to 1.5/98.5. The three-cycle demand match and positive-offer acceptance rules remain unchanged, preserving V4's termination insurance.

### Negotiation: role-specific capture and continuation

V3 negotiation improved strongly overall, but its seller role outperformed its buyer role. V5 retains the seller's complete-information capture schedule and gives the buyer a less aggressive schedule:

$$
c_t^{\mathrm{seller}}=0.74-0.14t,
\qquad
c_t^{\mathrm{buyer}}=0.66-0.10t.
$$

Before observing an opponent price under hidden information, the buyer opens at

$$
P_t=v_b(0.80+0.10t),
$$

instead of V4's $v_b(0.76+0.12t)$. Buyer continuation utility is also multiplied from a 0.75 rather than 0.80 base. These changes trade some buyer surplus for a higher probability of agreement while retaining individual rationality, concession forecasting, and stall termination.

More precisely, when both values are visible and the opponent has revealed a price, V5 converts that price into an opponent surplus demand $d_o$. It estimates a feasible personal capture

$$
c_t^{\mathrm{feasible}}
=1-\min\!\left(1,\max\!\left(0,d_o-(0.05+0.04t)\right)\right)
$$

and blends it with the role prior:

$$
c_t=0.58c_t^{\mathrm{role}}+0.42c_t^{\mathrm{feasible}},
\qquad 0.52\le c_t\le0.82.
$$

With hidden opponent value, let $P_o$ be the latest opponent price and let

$$
\Delta_t=P_{o,t}-P_{o,t-1}.
$$

V5 projects only economically plausible concessions:

$$
\widetilde P_{o,t+1}=P_{o,t}+0.6\Delta_t,
$$

where $\Delta_t\le0$ for an opponent seller and $\Delta_t\ge0$ for an opponent buyer. Seller and buyer claims are respectively $0.70-0.12t$ and $0.62-0.10t$, keeping the target between the projected offer and the agent's own valuation.

For a profitable received offer, target utility $U_t$, and repeated-price count $k$, the continuation threshold is

$$
U_{\mathrm{cont}}
=U_t\left(b_i-0.12t-0.08\min(k,2)\right),
\qquad
b_{\mathrm{seller}}=0.80,
\quad b_{\mathrm{buyer}}=0.75.
$$

V5 accepts when offered utility reaches this threshold or, under complete information, when its offered surplus share reaches $0.50+0.05(1-t)$. It accepts any profitable price after two repeated cycles, walks away from an unprofitable unknown-horizon path after three, and never knowingly accepts negative utility.

### Persuasion: bounded recency and sequential credibility

For a named seller, unlimited persistent history can make the buyer slow to react to a changed strategy. V5 caps persistent effective sample size at 12 and gives revealed current-game outcomes an additional weight of 1.5. If $n_H,n_L$ are capped persistent counts and $r_H,r_L$ are current-game counts, positive-signal precision is

$$
\widehat\rho_+=
\frac{4\rho_{+,0}+n_H+1.5r_H}
{4+n_H+n_L+1.5(r_H+r_L)}.
$$

The seller evaluates trust before the current outcome is revealed:

$$
T_t=\frac{4\rho_{+,0}+n_{+,H}}
{4+n_{+,H}+n_{+,L}}.
$$

With visible values, early low-quality pooling requires $T_t$ to exceed the buyer cutoff by a margin that shrinks with $t$. On the final round, V5 recommends a low-quality product whenever existing trust is within 0.03 of the cutoff and positive recommendations are being purchased, because there is no future reputation to preserve. In a representative trusted final-round state, this raises pooling probability from V4's 0.278 to 1.0.

When buyer values are hidden, V5 records the trust levels at which positive recommendations were bought or passed, derives a conservative cutoff estimate, and applies the same shrinking-margin rule. Hidden-value pooling remains capped at 0.70.

## V6 methods and diagnosed regression

V6 isolates bargaining rejection evidence by role, information condition, and visible discount signature. This prevents a threshold learned in one configuration from being applied as a hard floor in an incompatible game. It preserves the live-tested V5 negotiation decision core and strengthens local validation against undeclared keys, Boolean values passed as numbers, missing counteroffers, invalid decisions, and messages over 2,000 characters.

In persuasion, V6 correctly models the official information rule that a buyer observes quality only after purchasing. Passed products therefore do not update modeled buyer trust. For a positive-message cutoff $c$, define

$$
A=4\rho_{+,0}+n_H,
\qquad
N=4+n_H+n_L.
$$

V6 estimated the remaining low-quality credibility budget as

$$
B=\max\left(0,\frac{A}{c}-N\right)
$$

and scheduled that budget across the current and expected future low-quality opportunities. Although observation-correct, this scheduler performed poorly against the live opponent mix. In the 35-game batch, seller play averaged $-1.09$ and accounted for $-15.3$ of the rounded $-15.0$ total. This mechanism is retained as a documented negative result, not as the recommended persuasion policy.

## V7 methods: conservative policy portfolio

V7 does not assume that one new parameter vector dominates every role and configuration. It protects the strongest observed family policies—V4 bargaining, V5 negotiation, and V3 persuasion—and assigns one policy arm for the entire game. This avoids contaminating terminal credit by switching policies mid-game.

### Context-local selection and promotion

Evidence is separated by family, role, information condition, horizon bucket, economically relevant value or discount bucket, message mode, and disclosed opponent type. For an arm with normalized completed-game rewards $r_1,\ldots,r_n$, V7 stores

$$
\bar r=\frac{1}{n}\sum_{i=1}^{n}r_i,
\qquad
s^2=\max\left(0,\frac{1}{n}\sum_{i=1}^{n}r_i^2-\bar r^2\right),
$$

and computes the conservative interval

$$
L=\bar r-1.64\sqrt{\frac{s^2+0.02}{\max(1,n)}},
\qquad
U=\bar r+1.64\sqrt{\frac{s^2+0.02}{\max(1,n)}}.
$$

An under-sampled challenger is selected in at most 12% of eligible games. It is promoted only after at least eight local challenger games, at least four baseline games, a challenger mean more than 0.01 above the baseline mean, and a challenger lower bound no more than 0.03 below the baseline lower bound. If completed-game payoff cannot be extracted from the installed SDK response, V7 records no fabricated reward and retains the baseline.

### Bargaining: V4 baseline and QRE challenger

The protected arm is V4. For a proposed responder share $s$, estimated acceptance floor $\tau$, and logistic width $w$, it evaluates

$$
a(s)=\frac{1}{1+\exp\left(-(s-\tau+0.008)/w\right)},
$$

$$
J(s)=a(s)(1-s)^{1.15}-(1-a(s))C_t,
\qquad
C_t=0.04+0.24t+0.55(1-\delta).
$$

The configuration-local challenger uses V5-style role calibration: small floor shading, Alice-specific payoff curvature, and a lower Alice failure-cost multiplier. V4's unshaded rule remains the default because its live batch gained 46.19 points with 25/25 agreements.

### Negotiation: frozen V5 seller and bounded buyer residual

The protected arm exactly retains V5's decision constants. With visible surplus $S=v_b-v_s$, seller and buyer targets are

$$
P_{s,t}=v_s+(0.74-0.14t)S,
\qquad
P_{b,t}=v_b-(0.66-0.10t)S.
$$

The seller has no challenger. The buyer challenger changes requested capture by at most four percentage points,

$$
c^{\mathrm{trial}}_{b,t}=0.62-0.08t,
$$

uses $0.58-0.08t$ for its hidden-value claim, and changes continuation weighting from 0.75 to 0.72. These bounded residuals target the weaker buyer split without disturbing the seller arm that averaged +2.72 per visible V5 game.

### Persuasion: V3 baseline and role-specific caution

V7 retires V6's failed credibility-budget scheduler. The protected buyer restores V3's direct precision estimate

$$
\widehat\rho_m=\frac{4\rho_{m,0}+n_{m,H}}
{4+n_{m,H}+n_{m,L}},
\qquad
\mathbb E[V\mid m]=\widehat\rho_m v+(1-\widehat\rho_m)u.
$$

The protected seller restores V3's credibility-constrained pooling probability. The seller challenger never pools more aggressively than V3; it multiplies V3's rate by an empirical receiver-response factor that falls to zero for sufficiently skeptical buyers. The buyer challenger uses a mild one-sided lower estimate. With Beta parameters $\alpha$ and $\beta$,

$$
\rho_{\mathrm{LCB}}=
\max\left(0,\min\left(1,
\frac{\alpha}{\alpha+\beta}
-0.55\sqrt{\frac{\alpha\beta}
{(\alpha+\beta)^2(\alpha+\beta+1)}}\right)\right).
$$

Seller-response and buyer-reliability memories are separate. A buyer's reliability counts include quality only after purchase, while the informed seller may use all realized qualities in its own response model.

### Terminal reward credit and tests

V7 attempts to retrieve every assigned game after a bounded run. Bargaining payoff is normalized by the pot; negotiation and persuasion use bounded scale-normalized transformations. Re-harvesting is idempotent. The notebook's offline suite covers both bargaining players, extreme discounts, both negotiation roles, feasible prices, persuasion censoring, deterministic whole-game arm assignment, candidate isolation, normalized reward credit, and strict schema validation.

## Safety and limitations

- V2 through V8 validate every proposed action and use conservative legal fallbacks after unexpected schemas or strategy exceptions; V6 through V8 add stricter contract checks, and V8 separates gameplay fallbacks from telemetry.
- Stable hashes make persuasion mixing reproducible across concurrent games.
- Named opponents receive cross-game profiles; hidden identities receive only game-local profiles.
- No hand-coded strategy guarantees a rating increase. Matchmaking, configuration draws, opponent adaptation, and rating shrinkage create substantial short-run variance.
- V3 and V4 learn only from states delivered while a move is pending; a game-ending acceptance may not produce another strategy call.
- V4 increased the live bargaining rating in its first 25-game batch, but its negotiation and persuasion changes remain offline-tested only.
- V5 negotiation has one live 55-game batch; V5 bargaining and persuasion remain offline-tested. Its role-specific constants are hypotheses derived from limited, non-randomized samples, not guaranteed improvements.
- V6 persuasion lost 15.01 displayed rating points over 35 games despite zero fallbacks. Do not deploy its persuasion policy without revision.
- V7 gained 9.89 displayed bargaining points over 40 games with 40/40 agreements, but Alice averaged -0.37 and its overall rounded mean (+0.25) was well below V4's earlier +1.85. Its 12% exploration cap limits exposure; it does not guarantee rating protection or improvement.

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

## Evaluation results

### V3 three-family batch

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

### V4 bargaining batch

V4 played 25 bargaining games from approximately 10:06 AM to 10:14 AM on August 25, 2026. All 25 reached agreement.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Bargaining rating | 1305.87 | **1352.06** | **+46.19** |
| Bargaining games | 72 | **97** | **+25** |
| Three-family average | 1435.36 | **1450.76** | **+15.40** |

The dashboard's rounded per-game rating changes contained 13 positive and 12 negative results, summed to **+46.2**, and averaged **+1.85** per game. Role-level behavior was asymmetric:

| Bargaining role | Games | Agreements | Mean rounded rating change |
|---|---:|---:|---:|
| Alice | 9 | 9 | **-0.10** |
| Bob | 16 | 16 | **+2.94** |
| Overall | 25 | 25 | **+1.85** |

This batch supports the claim that V4 eliminated the observed bargaining non-termination in this sample and improved the displayed bargaining rating during the run. It does not yet establish whether the gain comes specifically from extreme-discount handling, cycle escape, opponent composition, configuration mix, or normal live-rating variance. The negative Alice mean is the clearest target for the next controlled calibration.

### V5 negotiation batch

V5 played 55 negotiation games on August 25, 2026. The displayed rating increased from **1243.31** after 72 games to **1344.87** after 127 games.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Negotiation rating | 1243.31 | **1344.87** | **+101.56** |
| Negotiation games | 72 | **127** | **+55** |
| Three-family average | 1450.76 | **1484.61** | **+33.85** |

The notebook reported a fallback count of **0** and retained 46 named or game-local negotiation profiles. The complete user-supplied dashboard list contains all 55 games:

| Role | Visible games | Agreements | No-deals | Walkaways | Positive / negative | Mean rounded delta |
|---|---:|---:|---:|---:|---:|---:|
| Buyer | 29 | 19 | 3 | 7 | 14 / 15 | **+1.07** |
| Seller | 26 | 17 | 6 | 3 | 18 / 8 | **+2.72** |
| Complete batch | 55 | 36 | 9 | 10 | 32 / 23 | **+1.85** |

The 55 displayed one-decimal deltas sum to +101.6, only 0.04 above the exact snapshot change of +101.56 because individual dashboard deltas are rounded. The complete batch supports a strong descriptive V5 negotiation gain and continued buyer calibration, but it still does not constitute a controlled causal comparison.

### V6 persuasion batch

V6 played 35 persuasion games on August 25, 2026. The displayed rating decreased from **1756.91** after 379 games to **1741.90** after 414 games.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Persuasion rating | 1756.91 | **1741.90** | **-15.01** |
| Persuasion games | 379 | **414** | **+35** |
| Three-family average | 1484.61 | **1479.61** | **-5.00** |

| Role | Games | Positive / negative | Rounded sum | Mean rounded delta | Median delta |
|---|---:|---:|---:|---:|---:|
| Buyer | 21 | 11 / 10 | **+0.3** | **+0.01** | **+1.3** |
| Seller | 14 | 3 / 11 | **-15.3** | **-1.09** | **-1.8** |
| Complete batch | 35 | 14 / 21 | **-15.0** | **-0.43** | **-0.8** |

The exact snapshot change and rounded game sum differ by 0.01 because individual deltas are displayed to one decimal place. The fallback count was zero. Thus the seller loss is a policy failure rather than evidence of invalid actions or crashes. The buyer was approximately neutral in this batch but well below V3's earlier buyer mean of +4.09. V6 persuasion is rejected; retain V3 as the persuasion reference while preserving V6's validation safeguards for future versions.

### V7 bargaining batch

V7 played 40 bargaining games on August 25, 2026. Every game reached agreement. The displayed rating increased from **1352.06** after 97 games to **1361.95** after 137 games.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Bargaining rating | 1352.06 | **1361.95** | **+9.89** |
| Bargaining games | 97 | **137** | **+40** |
| Three-family average | 1479.61 | **1482.91** | **+3.30** |

| Role | Games | Positive / negative / zero | Rounded sum | Mean rounded delta | Median |
|---|---:|---:|---:|---:|---:|
| Alice | 27 | 8 / 19 / 0 | **-9.9** | **-0.37** | **-1.3** |
| Bob | 13 | 7 / 5 / 1 | **+19.7** | **+1.52** | **+0.4** |
| Complete batch | 40 | 15 / 24 / 1 | **+9.8** | **+0.25** | **-1.3** |

The exact snapshot gain exceeds the rounded game sum by 0.09 because individual deltas are displayed to one decimal place. Completed-game rewards were harvested for all 40 games. The notebook displayed a diagnostic count of five because reward harvesting also queried five synthetic game IDs created by offline candidate tests; these were API lookup errors, not five malformed live actions. All live games completed with agreement.

The result is positive but weaker than V4's earlier bargaining batch, which averaged +1.85 in rounded delta. Alice again remained negative, while Bob supplied more than the entire batch gain. Without the displayed assignment/evidence rows, the dashboard summary cannot identify which games used `v4_safe` and which used `qre_adaptive`; no causal challenger claim is made.

### V8 negotiation batch

V8 played 44 negotiation games on August 25, 2026 while preserving the exact V5 negotiation decision constants. The displayed rating increased from **1344.87** after 127 games to **1395.83** after 171 games.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Negotiation rating | 1344.87 | **1395.83** | **+50.96** |
| Negotiation games | 127 | **171** | **+44** |
| Three-family average | 1482.91 | **1499.89** | **+16.99** |

| Role | Games | Agreements | No-deals | Walkaways | Positive / negative | Rounded sum | Mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Buyer | 15 | 5 | 8 | 2 | 11 / 4 | **+10.7** | **+0.71** |
| Seller | 29 | 12 | 12 | 5 | 18 / 11 | **+40.2** | **+1.39** |
| Complete batch | 44 | 17 | 20 | 7 | 29 / 15 | **+50.9** | **+1.16** |

The final checkpoint contained 21 games and moved negotiation from 1383.62 to 1395.83 (+12.21), harvesting 21 new terminal rewards. Across the complete run, the notebook harvested 44 terminal rewards with zero action fallbacks and zero telemetry diagnostics. The 0.06 difference between the rounded per-game sum and exact snapshot change is dashboard rounding.

Outcome-level means were +2.35 for agreements, +0.68 for no-deals, and -0.39 for walkaways. Positive no-deal deltas reinforce that V8 optimizes individually rational, configuration-relative payoff rather than agreement rate. Both roles were positive, although the seller remained stronger.

### V10 negotiation follow-up

V10 started at **1395.13 after 173 games** and finished at **1398.16 after 175 games**, an exact gain of **+3.03**. Both games were buyer walkaways with rounded changes +2.9 and +0.2. The SDK completed two games after a one-game request, so V10 correctly withheld ambiguous live arm credit and stopped. It harvested both terminal diagnostics with zero action fallbacks and zero telemetry diagnostics.

### V11 negotiation batch

V11 requested 24 champion-mode negotiation games at concurrency 4, but the SDK completed **53**. All used `v5_safe`. The displayed rating fell from **1398.16 after 175 games** to **1353.32 after 228 games**, an exact loss of **-44.84**.

| Role | Games | Agreements | No-deals | Walkaways | Positive / negative | Rounded sum | Mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Buyer | 30 | 19 | 9 | 2 | 15 / 15 | **-19.4** | **-0.65** |
| Seller | 23 | 10 | 11 | 2 | 8 / 15 | **-25.5** | **-1.11** |
| Complete batch | 53 | 29 | 20 | 4 | 23 / 30 | **-44.9** | **-0.85** |

All 53 terminal diagnostics were harvested with zero action fallbacks and zero telemetry diagnostics. Agreements summed to -26.6, no-deals to -23.9, and walkaways to +5.6. Because V11 retained the exact negotiation core, this does not isolate a policy-code regression. It does reject the 24-game, concurrency-4 runner: the oversized uninterruptible batch created 29 excess completions and unacceptable rating exposure.

## Evaluation and further improvement

- A/B test one family at a time and record the rating and game count immediately before and after each sufficiently large batch.
- Do not rerun V11's 24-game/concurrency-4 configuration. Use single-family, concurrency-1 checkpoints with an authoritative count check after every SDK return. The V5/V8 negotiation core has positive earlier batches but also V11's -44.84 sequential result, so current performance should be treated as unstable rather than guaranteed.
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
