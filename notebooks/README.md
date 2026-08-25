# GLEE agent notebook

For the newest score-oriented version, use [`GLEE_Competition_agent_v3.ipynb`](GLEE_Competition_agent_v3.ipynb). It adds bounded opponent models, continuation-value decisions, hidden-value concession inference, direct recommendation-precision learning, finite credibility budgeting, schema validation, and safe fallbacks. V2 and the original quickstart remain available for comparison.

[`GLEE_Competition_—_agent_quickstart.ipynb`](GLEE_Competition_—_agent_quickstart.ipynb) is a zero-setup agent for all three GLEE game families. It separates the policy into one function per family and exposes one dispatcher to the SDK:

$$
\pi(g)=\pi_f(g), \qquad f=\text{the game's family}.
$$

Here, the family $f$ is read from `game["game_family"]`.

This modular design makes it possible to tune and test one family without changing the others.

## Method

The notebook uses a **Bayesian and game-theoretic hybrid policy**. Each policy reads the visible game state, information structure, deadline, and legal action type. No model training or LLM inference is required.

### 1. Bargaining: fairness plus an acceptance threshold

Let $M$ be the available money and let $x_A,x_B$ be the proposed gains. Every valid offer must satisfy

$$
x_A+x_B=M.
$$

Under complete information, the proposer starts from the Rubinstein alternating-offers share. If $d_p$ and $d_r$ are the proposer and responder discount multipliers, respectively, the proposer's equilibrium share is

$$
s_p=\frac{1-d_r}{1-d_pd_r}.
$$

The implemented offer is bounded for robustness and converges toward an equal split as the deadline approaches. When the opponent's multiplier is hidden, the policy starts at 58% for itself and concedes toward 50%.

As responder, the agent compares the current gain with the discounted value of becoming proposer next round:

$$
\mathrm{accept}(x_i)=
\begin{cases}
1, & x_i \ge d_iMs_i^{\mathrm{next}},\\
0, & \text{otherwise}.
\end{cases}
$$

On the final round, any non-negative offer is accepted because continuation has zero value.

**Techniques:** alternating-offers equilibrium, continuation-value acceptance, deadline-aware concession, incomplete-information fallback, and valid-budget enforcement.

**Current limitation:** the incomplete-information policy uses a conservative prior rather than learning an opponent-specific acceptance threshold from rejected offers.

### 2. Negotiation: valuation anchoring and individual rationality

Let $v_s$ be the seller's minimum valuation, $v_b$ the buyer's maximum valuation, and $P$ the proposed price. A trade is individually rational when the relevant surplus is non-negative:

$$
U_s(P)=P-v_s \ge 0,
\qquad
U_b(P)=v_b-P \ge 0.
$$

When both valuations are visible, the policy divides the feasible surplus $S=v_b-v_s$. It targets the midpoint plus a temporary first-mover advantage that disappears by the deadline:

$$
P_t=
\begin{cases}
v_s+0.5S+0.15S(1-t), & \text{seller},\\
v_s+0.5S-0.15S(1-t), & \text{buyer},
\end{cases}
$$

where $t$ is normalized progress toward the final round. With hidden valuations, time-varying versions of the original valuation anchors provide a conservative fallback.

The agent accepts when the offer is profitable and reaches its current target. On the final round, it accepts every profitable offer:

$$
\mathrm{accept}(P)=
\begin{cases}
1, & P\ge \max(v_s,P_t) \quad \text{(seller)},\\
1, & P\le \min(v_b,P_t) \quad \text{(buyer)},\\
0, & \text{otherwise}.
\end{cases}
$$

The final-round rule drops the $P_t$ requirement and retains only individual rationality.

After rejecting, it blends its target toward the opponent's latest price, with the weight on that price increasing as the deadline approaches.

**Techniques:** Nash-style surplus division, role-conditioned logic, continuation value, deadline-aware acceptance, and concession.

**Current limitation:** under incomplete information, the policy does not yet estimate the opponent's reservation value from its sequence of counteroffers.

### 3. Persuasion: expected-value purchasing

Let $p$ be the prior probability of high quality, $v$ the buyer's value for high quality, $u$ the value for low quality, and $P$ the product price. After observing message $m$, the buyer estimates

$$
\widehat p=P(H\mid m), \qquad \mathbb{E}[V\mid m]=\widehat p v+(1-\widehat p)u.
$$

The buyer estimates the seller's positive-recommendation rates conditional on previously revealed high and low quality, using Beta smoothing. It applies Bayes' rule to the current signal, then buys only when posterior expected surplus is non-negative:

$$
\mathrm{buy}=
\begin{cases}
\text{yes}, & \mathbb{E}[V\mid m]\ge P,\\
\text{no}, & \mathbb{E}[V\mid m]<P.
\end{cases}
$$

The seller recommends every high-quality product. When buyer values are visible, it pools a calculated fraction of low-quality products into the positive signal while keeping a Bayesian buyer's posterior at or above its purchasing threshold. The notebook uses a stable hash of game and round identifiers for reproducible mixing.

**Techniques:** Bayesian updating, Beta-smoothed likelihood estimation, Bayesian persuasion, reproducible mixed strategies, and action-mode handling.

**Current limitation:** posterior learning depends on history records containing both a revealed outcome and its associated seller signal. Unrevealed quality cannot contribute evidence.

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

Results rendered by `GLEE_Competition_agent_v2.ipynb` on August 25, 2026:

| Game family | Rating | Games played |
|---|---:|---:|
| Bargaining | **1250.54** | 50 |
| Negotiation | **1162.31** | 50 |
| Persuasion | **1728.01** | 357 |

- **Agent:** `myagent`
- **Agent ID:** `9edb52a0-b489-44bd-b594-af77cdba5597`
- **Active games:** 0

Ratings are live and can change after every game.

## Improvement directions

- Use `game_state["history"]` to estimate opponent thresholds and concession rates.
- Make offers time-aware using the round, horizon, and inflation/discount parameters.
- Replace fixed negotiation multipliers with an adaptive reservation-value estimate.
- In persuasion, update the buyer's belief with Bayes' rule after observing recommendation accuracy:

  $$
  P(H\mid m)=\frac{P(m\mid H)P(H)}{P(m\mid H)P(H)+P(m\mid L)P(L)}.
  $$

- A/B test changes by family and compare rating over a sufficiently large game sample.
- Add an LLM only where language or history interpretation improves on the safe rule-based fallback.

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
