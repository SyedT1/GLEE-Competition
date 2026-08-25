# GLEE Competition — `myagent`

This repository contains my entry for the [GLEE Competition](https://glee-competition.com/), the official competition of the IAB Workshop at NeurIPS 2026. GLEE (Games in Language-based Economic Environments) evaluates AI agents in multi-turn economic interactions against agents and humans.

The competition covers three game families:

- **Bargaining:** two players divide a shared resource through alternating offers while delay makes the outcome less valuable.
- **Negotiation:** a buyer and seller negotiate a price using private valuations.
- **Persuasion:** an informed seller recommends a product to a buyer who must reason about hidden quality and trust.

## Leaderboard snapshot

Latest results rendered after a `GLEE_Competition_agent_v11.ipynb` negotiation evaluation on August 25, 2026:

| Game family | Rating | Games played |
|---|---:|---:|
| Bargaining | **1361.95** | 137 |
| Negotiation | **1353.32** | 228 |
| Persuasion | **1741.90** | 414 |

- **Agent:** `myagent`
- **Agent ID:** `9edb52a0-b489-44bd-b594-af77cdba5597`
- **Dashboard position in the earlier supplied V5 snapshot:** #1
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

### V6 persuasion evaluation

V6 then played a persuasion-only batch of 35 games. The displayed persuasion rating decreased from **1756.91** after 379 games to **1741.90** after 414 games, an exact snapshot change of **-15.01**. Bargaining and negotiation were unchanged. The unweighted three-family average consequently moved from **1484.61** to **1479.61** (**-5.00**).

| Persuasion role | Games | Positive deltas | Negative deltas | Rounded sum | Mean rounded delta |
|---|---:|---:|---:|---:|---:|
| Buyer | 21 | 11 | 10 | **+0.3** | **+0.01** |
| Seller | 14 | 3 | 11 | **-15.3** | **-1.09** |
| Complete batch | 35 | 14 | 21 | **-15.0** | **-0.43** |

The notebook again reported **zero fallbacks**, so the decline is evidence of a strategy regression rather than malformed actions or execution failures. Seller play accounts for essentially the entire rounded loss. V6's buyer was approximately neutral but also materially weaker than the earlier V3 buyer sample. V6 persuasion should therefore not be deployed further without revision.

### V7 bargaining evaluation

V7 played a bargaining-only batch of 40 games. All 40 reached agreement, and the displayed bargaining rating increased from **1352.06** after 97 games to **1361.95** after 137 games, an exact snapshot change of **+9.89**. Negotiation and persuasion were unchanged. The unweighted three-family average increased from **1479.61** to **1482.91** (**+3.30**).

| Bargaining role | Games | Positive | Negative | Zero | Rounded sum | Mean rounded delta |
|---|---:|---:|---:|---:|---:|---:|
| Alice | 27 | 8 | 19 | 0 | **-9.9** | **-0.37** |
| Bob | 13 | 7 | 5 | 1 | **+19.7** | **+1.52** |
| Complete batch | 40 | 15 | 24 | 1 | **+9.8** | **+0.25** |

The 0.09 difference between the rounded sum and exact rating change comes from one-decimal dashboard deltas. V7 harvested completed-game rewards for all 40 live games. Its displayed diagnostic count of five is not evidence of five live action fallbacks: the reward harvester attempted to query five synthetic IDs installed by the offline candidate tests. The batch remained positive with 100% agreement, but its mean rounded gain was much smaller than V4's earlier +1.85, and Alice remained negative. V7 therefore supplies a cautious positive result, not evidence that its challenger dominates V4.

### V8 negotiation evaluation

V8 froze the successful V5 negotiation decision core and ran negotiation in checkpointed batches. Across the complete 44-game run, the displayed negotiation rating increased from **1344.87** after 127 games to **1395.83** after 171 games, an exact change of **+50.96**. The final 21-game checkpoint alone moved from 1383.62 to 1395.83 (**+12.21**). Bargaining and persuasion were unchanged. The unweighted three-family average increased from **1482.91** to **1499.89** (**+16.99**).

| Negotiation role | Games | Agreements | No-deals | Walkaways | Rounded sum | Mean rounded delta |
|---|---:|---:|---:|---:|---:|---:|
| Buyer | 15 | 5 | 8 | 2 | **+10.7** | **+0.71** |
| Seller | 29 | 12 | 12 | 5 | **+40.2** | **+1.39** |
| Complete batch | 44 | 17 | 20 | 7 | **+50.9** | **+1.16** |

Twenty-nine deltas were positive and 15 negative. Agreements averaged +2.35, no-deals +0.68, and walkaways -0.39, showing that agreement count alone is not the competition objective. V8 harvested all 44 terminal rewards across the full run, including 21 in the final checkpoint, with **zero live action fallbacks and zero telemetry diagnostics**. Both roles were positive, although seller performance remained stronger.

### V10 negotiation evaluation

V10 ran the locked V5/V8 negotiation champion in `champion` mode. The authoritative pre-run snapshot was **1395.13 after 173 games**; this differs from V8's documented endpoint because two intervening negotiation games moved the rating by -0.70 before the supplied V10 run. The V10 SDK call requested one completion, but two games completed before control returned. Both games assigned the agent the buyer role and ended in walkaways:

| Role | Outcome | Rounded rating change |
|---|---|---:|
| Buyer | Walkaway | **+2.9** |
| Buyer | Walkaway | **+0.2** |
| Complete V10 run | 2 walkaways | **+3.1** |

The displayed negotiation rating increased from **1395.13 after 173 games** to **1398.16 after 175 games**, an exact snapshot gain of **+3.03**. The rounded game deltas sum to +3.1; the 0.07 difference is dashboard rounding. Bargaining and persuasion were unchanged, and the unweighted three-family average increased from **1499.66** to **1500.67** (**+1.01**).

V10 harvested both terminal-payoff diagnostics with **zero live action fallbacks and zero telemetry diagnostics**. Because the completion delta was two rather than one, its rating-alignment guard correctly recorded `Rating credit: None`, declined to attribute the aggregate rating change to either game, and stopped immediately with `completion overshoot: 2`. The console's `Rating-attributed outcomes: 1` is the synthetic record created by V10's offline rating-credit test, not a live attributed outcome. Thus this run supports the locked negotiation policy's continued positive performance, but it supplies no arm-promotion evidence and is far too small for a new causal claim.

### V11 negotiation evaluation

V11 deliberately replaced the one-completion driver with a larger champion-mode batch. It requested 24 negotiation games at concurrency 4, but the SDK completed **53 games** before returning. All 53 used the locked `v5_safe` arm. The displayed negotiation rating fell from **1398.16 after 175 games** to **1353.32 after 228 games**, an exact change of **-44.84**. Bargaining and persuasion were unchanged, so the unweighted three-family average fell from **1500.67** to **1485.72** (**-14.95**).

| Split | Games | Agreements | No-deals | Walkaways | Positive / negative | Rounded sum | Mean rounded delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| Buyer | 30 | 19 | 9 | 2 | 15 / 15 | **-19.4** | **-0.65** |
| Seller | 23 | 10 | 11 | 2 | 8 / 15 | **-25.5** | **-1.11** |
| Complete batch | 53 | 29 | 20 | 4 | 23 / 30 | **-44.9** | **-0.85** |

Agreements summed to -26.6 across 29 games (mean -0.92), no-deals summed to -23.9 across 20 games (mean -1.20), and four walkaways summed to +5.6 (mean +1.40). The rounded total differs from the exact snapshot change by 0.06 because dashboard deltas have one decimal place. V11 harvested all 53 terminal diagnostics with **zero action fallbacks and zero telemetry diagnostics**, so the loss is not explained by malformed actions or execution exceptions.

This is not evidence that V11 changed the negotiation decision policy: every game used the same `v5_safe` core as V5, V8, and V10. It is evidence that the V11 batch runner created unacceptable exposure. The SDK completed more than twice the requested count, and aggregate batch accounting could not stop during the run. V11's 24-game/concurrency-4 execution configuration is therefore rejected. Do not rerun it unchanged; return to concurrency 1, very small checkpoints, and an external authoritative-count stop between SDK calls.

## Agent implementation

The evidence-backed deployment portfolio is family-specific: [`notebooks/GLEE_Competition_agent_v4.ipynb`](notebooks/GLEE_Competition_agent_v4.ipynb) for bargaining, [`notebooks/GLEE_Competition_agent_v5.ipynb`](notebooks/GLEE_Competition_agent_v5.ipynb) for negotiation, and V3 for persuasion. [`notebooks/GLEE_Competition_agent_v6.ipynb`](notebooks/GLEE_Competition_agent_v6.ipynb) adds stronger validation and configuration-safe memory, but its live persuasion policy is rejected after the negative 35-game batch.

[`notebooks/GLEE_Competition_agent_v7.ipynb`](notebooks/GLEE_Competition_agent_v7.ipynb) packages those three protected policies into one conservative portfolio. It assigns one arm for the entire game, limits under-sampled challenger exploration to 12%, records completed-game payoff when the installed SDK exposes it, and permits promotion only from role- and configuration-local evidence. Its challengers are a quantal-response bargaining calibration, a bounded buyer-only negotiation residual, and separate empirical-seller/lower-confidence buyer persuasion policies. Its first live bargaining batch gained 9.89 points over 40 games with 40/40 agreements, but Alice averaged -0.37 and the overall per-game gain was weaker than V4's earlier batch. Continue to evaluate one family at a time with concurrency 1.

[`notebooks/GLEE_Competition_agent_v8.ipynb`](notebooks/GLEE_Competition_agent_v8.ipynb) tightens exploration to the weak roles only, freezes the V5 negotiation core and V3 persuasion buyer, persists terminal evidence, evaluates in checkpoints, and separates gameplay fallbacks from telemetry. Its first negotiation run gained **50.96** points over 44 games; buyer and seller means were both positive, and all 44 rewards were harvested with zero action fallbacks or telemetry errors. V8 remains the strongest larger-sample negotiation record, while the family policy references remain V4 bargaining, V5 negotiation, and V3 persuasion.

[`notebooks/GLEE_Competition_agent_v10.ipynb`](notebooks/GLEE_Competition_agent_v10.ipynb) is the current recommended unified execution notebook. It preserves the same family champions, uses actual unambiguous one-game dashboard rating changes rather than normalized payoff proxies for calibration evidence, and defaults to the replicated negotiation champion. Its first supplied run gained **3.03** negotiation points over two buyer games with zero fallbacks or telemetry errors. The SDK nevertheless completed two games after a one-game request, so V10 correctly withheld rating credit and stopped; future runs should continue from zero active games with concurrency 1 and retain the overshoot guard.

[`notebooks/GLEE_Competition_agent_v11.ipynb`](notebooks/GLEE_Competition_agent_v11.ipynb) is retained as a documented negative operational result, not a recommended runner. Its unchanged negotiation core lost **44.84** points over 53 games after a request for 24 at concurrency 4. The run had zero policy fallbacks and telemetry errors, but its inability to interrupt the oversized batch exposed the agent to 29 excess completions. V10's small-checkpoint execution remains preferred pending stronger server-side game-count control.

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
client.run(strategy, game_families=["bargaining"], concurrency=1, max_games=12)
```

## References

- [Competition website and rules](https://glee-competition.com/)
- [Competition documentation](https://glee-competition.com/docs)
- [Official SDK repository](https://github.com/eilamshapira/GLEE_competition)
- [GLEE paper](https://arxiv.org/abs/2410.05254)
