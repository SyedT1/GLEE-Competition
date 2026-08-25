# GLEE Competition — `myagent`

This repository contains my entry for the [GLEE Competition](https://glee-competition.com/), the official competition of the IAB Workshop at NeurIPS 2026. GLEE (Games in Language-based Economic Environments) evaluates AI agents in multi-turn economic interactions against agents and humans.

The competition covers three game families:

- **Bargaining:** two players divide a shared resource through alternating offers while delay makes the outcome less valuable.
- **Negotiation:** a buyer and seller negotiate a price using private valuations.
- **Persuasion:** an informed seller recommends a product to a buyer who must reason about hidden quality and trust.

## Leaderboard snapshot

Latest results rendered after a `GLEE_Competition_agent_v5.ipynb` negotiation evaluation batch on August 25, 2026:

| Game family | Rating | Games played |
|---|---:|---:|
| Bargaining | **1352.06** | 97 |
| Negotiation | **1344.87** | 127 |
| Persuasion | **1756.91** | 379 |

- **Agent:** `myagent`
- **Agent ID:** `9edb52a0-b489-44bd-b594-af77cdba5597`
- **Dashboard position at the supplied snapshot:** #1
- **Dashboard short identifier shown:** `8903a6e897cd`
- **Active games:** 0

These values are a point-in-time snapshot from the competition dashboard and may change as more games are played.

During the earlier V3 batch, each family completed 22 additional games. Displayed ratings changed by **+55.33** in bargaining, **+81.00** in negotiation, and **+28.90** in persuasion. The three-family average increased from **1380.29** to **1435.36** (**+55.08**).

### V3 game-history analysis

The saved [V3 game history](game_history.txt) contains the 66-game batch summary plus selected detailed transcripts. The summary provides the following descriptive behavior evidence:

| Family | Outcomes | Mean per-game rating change | Role-level mean change |
|---|---|---:|---|
| Bargaining | 21 agreements, 1 no-deal | **+2.52** | Alice +1.95; Bob +3.34 |
| Negotiation | 12 agreements, 7 no-deals, 3 walkaways | **+3.68** | Buyer +2.28; Seller +6.14 |
| Persuasion | 22 completed | **+1.31** | Buyer +4.09; Seller -0.61 |

Across the batch, 42 game entries had positive rating changes, 23 had negative changes, and one was unchanged. The transcripts also expose meaningful deviations: an unlimited-horizon bargaining match cycled for 99 rounds and ended without agreement, while persuasion performed substantially better in the buyer role than the seller role. These observations motivate cycle detection, a more flexible unknown-horizon reservation floor, and further calibration of the persuasion seller's pooling policy.

This is a single live batch rather than a controlled V2-versus-V3 experiment. Opponent mix, configuration draws, role assignment, rating shrinkage, and normal variance prevent a causal performance claim.

### V4 bargaining evaluation

V4 then played a bargaining-only batch of 25 games. Every game reached agreement, and the displayed bargaining rating increased from **1305.87** after 72 games to **1352.06** after 97 games, an exact snapshot change of **+46.19**.

| Role | Games | Positive deltas | Negative deltas | Mean rounded per-game delta |
|---|---:|---:|---:|---:|
| Alice | 9 | 4 | 5 | **-0.10** |
| Bob | 16 | 9 | 7 | **+2.94** |
| All bargaining games | 25 | 13 | 12 | **+1.85** |

The rounded per-game changes sum to **+46.2**; the small difference from **+46.19** comes from dashboard rounding. The overall three-family average is now **1450.76**. Although agreement reached 100%, the role split shows that V4's Alice policy still needs calibration.

### V5 negotiation evaluation

V5 then played a negotiation-only batch of 55 games. The displayed negotiation rating increased from **1243.31** after 72 games to **1344.87** after 127 games, an exact snapshot change of **+101.56**. Bargaining and persuasion were not run and therefore remained unchanged. The unweighted three-family rating average increased from **1450.76** to **1484.61** (**+33.85**).

The notebook reported **zero fallbacks**, 46 named or game-local negotiation profiles, five bargaining profiles, and six role-separated persuasion profiles. The complete supplied dashboard list contains all 55 games. Its one-decimal deltas sum to **+101.6** and show the following descriptive split:

| Negotiation role | Visible games | Agreements | No-deals | Walkaways | Mean rounded delta |
|---|---:|---:|---:|---:|---:|
| Buyer | 29 | 19 | 3 | 7 | **+1.07** |
| Seller | 26 | 17 | 6 | 3 | **+2.72** |
| Complete batch | 55 | 36 | 9 | 10 | **+1.85** |

The rounded per-game sum of **+101.6** differs from the exact two-decimal snapshot change of **+101.56** by only 0.04 because the dashboard rounds each game to one decimal place. Seller performance remained stronger, but both roles had positive mean deltas.

## Agent implementation

The current live-tested candidate is [`notebooks/GLEE_Competition_agent_v5.ipynb`](notebooks/GLEE_Competition_agent_v5.ipynb). It preserves V4's cycle-safe bargaining but targets the weak Alice role, makes negotiation buyers more agreement-oriented without accepting negative surplus, and replaces conservative seller pooling with a bounded recency model and sequential trust ledger. V5 is now the strongest live-tested negotiation version in this repository; [`notebooks/GLEE_Competition_agent_v4.ipynb`](notebooks/GLEE_Competition_agent_v4.ipynb) remains the bargaining reference, and V3 remains the persuasion reference until the corresponding V5 family batches are run.

For the methods, techniques, equations, usage instructions, and limitations, see the [notebook documentation](notebooks/README.md).

## Quick start

1. Create an agent in the [GLEE dashboard](https://glee-competition.com/dashboard) and copy its API key.
2. Open the notebook in Jupyter or Google Colab.
3. Store the key in the `GLEE_API_KEY` environment variable; do not commit it.
4. Run the strategy cells and then start matchmaking with `client.run(...)`.

```python
import os
from glee_sdk import GleeClient

client = GleeClient(api_key=os.environ["GLEE_API_KEY"])
client.run(strategy, concurrency=4, max_games=20)
```

## References

- [Competition website and rules](https://glee-competition.com/)
- [Competition documentation](https://glee-competition.com/docs)
- [Official SDK repository](https://github.com/eilamshapira/GLEE_competition)
- [GLEE paper](https://arxiv.org/abs/2410.05254)
