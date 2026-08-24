# GLEE agent notebook

[`GLEE_Competition_—_agent_quickstart.ipynb`](GLEE_Competition_—_agent_quickstart.ipynb) is a zero-setup agent for all three GLEE game families. It separates the policy into one function per family and exposes one dispatcher to the SDK:

$$
\pi(g)=\pi_f(g), \qquad f=g[\texttt{game\_family}].
$$

This modular design makes it possible to tune and test one family without changing the others.

## Method

The notebook uses a **rule-based, utility-aware baseline**. Each policy reads the visible game state and legal action type, then returns a valid deterministic action. No model training or LLM inference is required.

### 1. Bargaining: fairness plus an acceptance threshold

Let $M$ be the available money and let $x_A,x_B$ be the proposed gains. Every valid offer must satisfy

$$
x_A+x_B=M.
$$

The proposer uses an equal split:

$$
x_A=x_B=\frac{M}{2}.
$$

If the agent is receiving an offer, it accepts when its own gain $x_i$ is at least 40% of the pot:

$$
\operatorname{accept}(x_i)=
\begin{cases}
1, & x_i \ge 0.4M,\\
0, & x_i < 0.4M.
\end{cases}
$$

**Techniques:** symmetric anchoring, fairness signaling, reservation-threshold decision making, and valid-budget enforcement.

**Current limitation:** although the state exposes round history, horizon, and player-specific inflation multiplier $\delta_i$, this baseline does not yet adapt its offer or threshold over time.

### 2. Negotiation: valuation anchoring and individual rationality

Let $v_s$ be the seller's minimum valuation, $v_b$ the buyer's maximum valuation, and $P$ the proposed price. A trade is individually rational when the relevant surplus is non-negative:

$$
U_s(P)=P-v_s \ge 0,
\qquad
U_b(P)=v_b-P \ge 0.
$$

The initial price is anchored to the agent's own valuation $v_i$:

$$
P_0=
\begin{cases}
1.5v_s, & \text{seller},\\
0.7v_b, & \text{buyer}.
\end{cases}
$$

The agent accepts exactly when the offer is profitable:

$$
\operatorname{accept}(P)=
\begin{cases}
1, & P\ge v_s \quad \text{(seller)},\\
1, & P\le v_b \quad \text{(buyer)},\\
0, & \text{otherwise}.
\end{cases}
$$

After rejecting, it counters closer to its valuation:

$$
P_{\text{counter}}=
\begin{cases}
1.3v_s, & \text{seller},\\
0.8v_b, & \text{buyer}.
\end{cases}
$$

**Techniques:** role-conditioned logic, private-value anchoring, non-negative-surplus acceptance, and concession through less aggressive counteroffers.

**Current limitation:** the multipliers are fixed; the policy does not infer the opponent's reservation value from prior offers or react to the remaining horizon.

### 3. Persuasion: expected-value purchasing

Let $p$ be the probability of high quality, $v$ the buyer's value for high quality, $u$ the value for low quality, and $P$ the product price. The buyer estimates

$$
\mathbb{E}[V]=pv+(1-p)u
$$

and buys only when the expected surplus is positive:

$$
\operatorname{buy}=
\begin{cases}
\text{yes}, & \mathbb{E}[V]>P,\\
\text{no}, & \mathbb{E}[V]\le P.
\end{cases}
$$

The seller always recommends the product, using either a text message or a binary recommendation according to `valid_actions["type"]`.

**Techniques:** probabilistic expected-utility calculation, action-mode handling, and a consistent seller signal.

**Current limitation:** the buyer uses the prior $p$ directly and does not update it from the seller's history. The seller also ignores current quality, so its recommendation is not calibrated and may lose credibility over repeated rounds.

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

As reported from the dashboard on August 24, 2026, `myagent` was ranked **#1**:

| Game family | Rating | Games played today |
|---|---:|---:|
| Bargaining | **1063.5** | 12 |
| Negotiation | **1018.3** | 12 |
| Persuasion | **1000.9** | 2 |

Because the number of persuasion games is much smaller, its rating is less tested than the other two family ratings. Ratings are live and can change after every game.

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
