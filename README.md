# GLEE Competition — `myagent`

This repository contains my entry for the [GLEE Competition](https://glee-competition.com/), the official competition of the IAB Workshop at NeurIPS 2026. GLEE (Games in Language-based Economic Environments) evaluates AI agents in multi-turn economic interactions against agents and humans.

The competition covers three game families:

- **Bargaining:** two players divide a shared resource through alternating offers while delay makes the outcome less valuable.
- **Negotiation:** a buyer and seller negotiate a price using private valuations.
- **Persuasion:** an informed seller recommends a product to a buyer who must reason about hidden quality and trust.

## Leaderboard snapshot

Latest results rendered after a `GLEE_Competition_agent_v3.ipynb` evaluation batch on August 25, 2026:

| Game family | Rating | Games played |
|---|---:|---:|
| Bargaining | **1305.87** | 72 |
| Negotiation | **1243.31** | 72 |
| Persuasion | **1756.91** | 379 |

- **Agent:** `myagent`
- **Agent ID:** `9edb52a0-b489-44bd-b594-af77cdba5597`
- **Active games:** 0

These values are a point-in-time snapshot from the competition dashboard and may change as more games are played.

During this V3 batch, each family completed 22 additional games. Displayed ratings changed by **+55.33** in bargaining, **+81.00** in negotiation, and **+28.90** in persuasion. The three-family average increased from **1380.29** to **1435.36** (**+55.08**).

### V3 game-history analysis

The saved [V3 game history](game_history.txt) contains the 66-game batch summary plus selected detailed transcripts. The summary provides the following descriptive behavior evidence:

| Family | Outcomes | Mean per-game rating change | Role-level mean change |
|---|---|---:|---|
| Bargaining | 21 agreements, 1 no-deal | **+2.52** | Alice +1.95; Bob +3.34 |
| Negotiation | 12 agreements, 7 no-deals, 3 walkaways | **+3.68** | Buyer +2.28; Seller +6.14 |
| Persuasion | 22 completed | **+1.31** | Buyer +4.09; Seller -0.61 |

Across the batch, 42 game entries had positive rating changes, 23 had negative changes, and one was unchanged. The transcripts also expose meaningful deviations: an unlimited-horizon bargaining match cycled for 99 rounds and ended without agreement, while persuasion performed substantially better in the buyer role than the seller role. These observations motivate cycle detection, a more flexible unknown-horizon reservation floor, and further calibration of the persuasion seller's pooling policy.

This is a single live batch rather than a controlled V2-versus-V3 experiment. Opponent mix, configuration draws, role assignment, rating shrinkage, and normal variance prevent a causal performance claim.

## Agent implementation

The experimental history-calibrated candidate is [`notebooks/GLEE_Competition_agent_v4.ipynb`](notebooks/GLEE_Competition_agent_v4.ipynb). It fixes the extreme-discount bargaining cap and 99-round cycle observed in V3, adds negotiation stall termination and trend inference, and separates persuasion memory by opponent role while making the seller adaptive under hidden buyer values. The live-tested reference remains [`notebooks/GLEE_Competition_agent_v3.ipynb`](notebooks/GLEE_Competition_agent_v3.ipynb) until V4 completes comparable controlled batches. Both use the official [`glee-sdk`](https://pypi.org/project/glee-sdk/) and validated family dispatchers.

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
