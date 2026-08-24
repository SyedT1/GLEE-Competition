# GLEE Competition — `myagent`

This repository contains my entry for the [GLEE Competition](https://glee-competition.com/), the official competition of the IAB Workshop at NeurIPS 2026. GLEE (Games in Language-based Economic Environments) evaluates AI agents in multi-turn economic interactions against agents and humans.

The competition covers three game families:

- **Bargaining:** two players divide a shared resource through alternating offers while delay makes the outcome less valuable.
- **Negotiation:** a buyer and seller negotiate a price using private valuations.
- **Persuasion:** an informed seller recommends a product to a buyer who must reason about hidden quality and trust.

## Leaderboard snapshot

| Agent | Overall rank | Snapshot date |
|---|---:|---|
| `myagent` | **#1** | August 24, 2026 |

| Game family | Rating | Games played today |
|---|---:|---:|
| Bargaining | **1063.5** | 12 |
| Negotiation | **1018.3** | 12 |
| Persuasion | **1000.9** | 2 |

These values are a point-in-time snapshot from the competition dashboard and may change as more games are played.

## Agent implementation

The runnable quickstart is in [`notebooks/GLEE_Competition_—_agent_quickstart.ipynb`](notebooks/GLEE_Competition_—_agent_quickstart.ipynb). It uses the official [`glee-sdk`](https://pypi.org/project/glee-sdk/) and a dispatcher that routes each game to a family-specific strategy.

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
