# GLEE Competition — `myagent`

This repository contains my entry for the [GLEE Competition](https://glee-competition.com/), the official competition of the IAB Workshop at NeurIPS 2026. GLEE (Games in Language-based Economic Environments) evaluates AI agents in multi-turn economic interactions against agents and humans.

The competition covers three game families:

- **Bargaining:** two players divide a shared resource through alternating offers while delay makes the outcome less valuable.
- **Negotiation:** a buyer and seller negotiate a price using private valuations.
- **Persuasion:** an informed seller recommends a product to a buyer who must reason about hidden quality and trust.

## Leaderboard snapshot

Latest authoritative snapshots after the V33 run on August 30, 2026:

| Game family | Rating | Games played |
|---|---:|---:|
| Bargaining | **1535.92** | 483 |
| Negotiation | **1661.30** | 582 |
| Persuasion | **1825.84** | 639 |

- **Agent:** `myagent`
- **Agent ID:** `8903a6e897cd`
- **Dashboard position in the earlier supplied V5 snapshot:** #1
- **Dashboard short identifier shown:** `8903a6e897cd`
- **V33 live action fallbacks:** 0
- **V33 action fallbacks and assignment overshoots:** 0
- **Reward-harvest telemetry entries:** 500; the checkpoint counted telemetry before harvesting and therefore failed to expose them to its guard

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

### V23 adaptive-defender evaluation

V23 used deterministic, role-aware heuristics with a one-queue controller and attempted up to 50 authoritative completions per family. It applied both a 20-point loss limit from the starting rating and a 15-point trailing drawdown from the best rating observed during the batch. Bargaining and persuasion stopped early; negotiation reached its full target.

| Family | Games | Initial rating | Final rating | Exact change | Peak drawdown | Stop reason |
|---|---:|---:|---:|---:|---:|---|
| Bargaining | 11 | 1313.92 | 1301.09 | **-12.83** | 16.47 | Trailing rating drawdown |
| Negotiation | 50 | 1383.79 | 1561.56 | **+177.77** | 0.00 | Target reached |
| Persuasion | 10 | 1798.92 | 1785.07 | **-13.85** | 17.70 | Trailing rating drawdown |

The live-only rating records reveal sharper role effects than the family totals:

| Family and role | Games | Positive / negative | Exact sum | Mean delta |
|---|---:|---:|---:|---:|
| Bargaining, Alice (`player_1`) | 5 | 1 / 4 | **-15.13** | **-3.026** |
| Bargaining, Bob (`player_2`) | 6 | 3 / 3 | **+2.30** | **+0.383** |
| Negotiation, buyer | 24 | 22 / 2 | **+68.14** | **+2.839** |
| Negotiation, seller | 26 | 24 / 2 | **+109.63** | **+4.217** |
| Persuasion, buyer | 5 | 3 / 2 | **+5.96** | **+1.192** |
| Persuasion, seller | 5 | 0 / 5 | **-19.81** | **-3.962** |

This is strong descriptive evidence for retaining V23's defensive negotiation heuristic: 46 of 50 games were positive and both roles gained. It rejects V23's Alice bargaining challenger and identifies persuasion seller outcomes as the principal observed weakness; all five seller games were negative while the buyer role was positive overall. The stop controller also behaved as designed, limiting the two adverse families to 11 and 10 completions instead of blindly running 50. These sequential observations are still not randomized causal comparisons because matchmaking, opponents, configurations, roles, rating level, and time vary.

### V24 bargaining and persuasion repair

V24 froze V23 negotiation and changed only the two roles rejected by V23: Alice received a surplus-protecting bargaining policy, while the persuasion seller became truthful before the final round and pooled low quality only in the terminal round. Both live families stopped after ten games on the configured trailing-drawdown guard.

| Family | Games | Initial rating | Final rating | Exact change | Peak rating | Peak drawdown |
|---|---:|---:|---:|---:|---:|---:|
| Bargaining | 10 | 1301.09 | 1292.96 | **-8.13** | 1305.56 | 12.60 |
| Persuasion | 10 | 1784.12 | 1788.27 | **+4.15** | 1800.37 | 12.10 |

The persuasion initial rating is 0.95 below the documented V23 endpoint, indicating an intervening dashboard movement or decay before V24; V24's change is therefore measured from its own authoritative starting snapshot.

| Family and role | Games | Positive / negative | Exact sum | Mean delta |
|---|---:|---:|---:|---:|
| Bargaining, Alice (`player_1`) | 4 | 1 / 3 | **+1.70** | **+0.425** |
| Bargaining, Bob (`player_2`) | 6 | 2 / 4 | **-9.83** | **-1.638** |
| Persuasion, buyer | 5 | 3 / 2 | **+0.93** | **+0.186** |
| Persuasion, seller | 5 | 3 / 2 | **+3.22** | **+0.644** |

V24 repaired the targeted roles descriptively: Alice changed from V23's -15.13 to a positive +1.70 sample, and persuasion sellers changed from -19.81 to +3.22. Persuasion was positive in both roles and improved overall, supporting terminal-only seller pooling for further controlled evaluation. Bargaining was still negative because the retained Bob branch lost 9.83 points; the result rejects the assumption that the earlier V4 Bob heuristic remained stable under the current opponent and configuration mix. The ten-game role samples remain too small and non-randomized for causal superiority claims. V24 reported zero action fallbacks and zero telemetry diagnostics.

### V25 deterministic bargaining and V23 negotiation

V25 removed the language-model experiment, ran deterministic V24-derived bargaining, and reused the exact V23 negotiation decision code. Persuasion was not exposed. Both selected families stopped on their trailing-drawdown guards while retaining positive net changes.

| Family | Games | Initial rating | Final rating | Exact change | Peak rating | Peak drawdown |
|---|---:|---:|---:|---:|---:|---:|
| Bargaining | 8 | 1292.96 | 1298.82 | **+5.86** | 1309.36 | 10.54 |
| Negotiation | 43 | 1561.56 | 1571.86 | **+10.30** | 1588.26 | 16.40 |

| Family and role | Games | Positive / negative | Exact sum | Mean delta |
|---|---:|---:|---:|---:|
| Bargaining, Alice (`player_1`) | 5 | 4 / 1 | **+9.05** | **+1.810** |
| Bargaining, Bob (`player_2`) | 3 | 1 / 2 | **-3.19** | **-1.063** |
| Negotiation, buyer | 23 | 15 / 8 | **+9.13** | **+0.397** |
| Negotiation, seller | 20 | 11 / 9 | **+1.17** | **+0.059** |

V25 provides a second positive sample for the repaired Alice policy: four of five Alice games were positive, while Bob remained the bargaining weakness. The unchanged V23 negotiation code was positive in both roles and in 26 of 43 games, but its +10.30 gain was much smaller than V23's earlier +177.77 over 50. It rose 26.70 points to its session peak before returning 16.40, demonstrating substantial nonstationarity despite identical decision rules. The drawdown controller preserved positive net gains in both families. There were zero live action fallbacks and zero telemetry diagnostics.

### V26 three-family adaptive evaluation

V26 repaired Bob, adapted negotiation to the contexts that reversed in V25, and retained V24's terminal-only persuasion seller. All three families finished above their own authoritative starting snapshots before stopping on trailing drawdown.

| Family | Games | Initial rating | Final rating | Exact change | Peak rating | Peak drawdown |
|---|---:|---:|---:|---:|---:|---:|
| Bargaining | 11 | 1298.82 | 1308.92 | **+10.10** | 1320.46 | 11.54 |
| Negotiation | 46 | 1571.86 | 1619.27 | **+47.41** | 1634.30 | 15.03 |
| Persuasion | 16 | 1787.33 | 1801.89 | **+14.56** | 1812.19 | 10.30 |

The persuasion start is 0.94 below the documented V25 endpoint, indicating an intervening dashboard movement or decay; its V26 change is measured from its own authoritative start.

| Family and role | Games | Positive / negative | Exact sum | Mean delta |
|---|---:|---:|---:|---:|
| Bargaining, Alice (`player_1`) | 5 | 2 / 3 | **+0.66** | **+0.132** |
| Bargaining, Bob (`player_2`) | 6 | 3 / 3 | **+9.44** | **+1.573** |
| Negotiation, buyer | 15 | 9 / 6 | **+12.41** | **+0.827** |
| Negotiation, seller | 31 | 20 / 11 | **+35.00** | **+1.129** |
| Persuasion, buyer | 9 | 6 / 3 | **+21.83** | **+2.426** |
| Persuasion, seller | 7 | 2 / 5 | **-7.27** | **-1.039** |

The Bob-specific repair reversed the negative V24/V25 Bob aggregates while Alice remained slightly positive, and both adapted negotiation roles gained. Persuasion gained overall because its buyer result outweighed a renewed seller-side loss; terminal-only pooling is therefore not stable enough to treat as a solved branch. V26 recorded 73 live, assignment-linked rating outcomes, zero action fallbacks, and zero telemetry diagnostics. These adaptively stopped, sequential samples support the portfolio descriptively but do not establish causal superiority.

### V33 evidence-locked 150-each evaluation

V33 locked each role to the strongest preceding branch suggested by V23--V30 evidence and attempted 150 authoritative completions per family with concurrency one. Bargaining reached its target; persuasion and negotiation stopped on their family trailing-drawdown guards.

| Family | Games | Initial rating | Final rating | Exact change | Peak rating | Peak drawdown | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---|
| Bargaining | 150 | 1344.98 | 1535.92 | **+190.94** | 1537.53 | 1.61 | Target reached |
| Persuasion | 78 | 1770.17 | 1825.84 | **+55.67** | 1849.03 | 23.19 | Family trailing drawdown |
| Negotiation | 20 | 1695.03 | 1661.30 | **-33.73** | 1695.03 | 33.73 | Family trailing drawdown |

| Family and role | Games | Positive / negative / zero | Exact sum | Mean delta |
|---|---:|---:|---:|---:|
| Bargaining, Alice (`player_1`) | 64 | 33 / 30 / 1 | **+80.15** | **+1.252** |
| Bargaining, Bob (`player_2`) | 86 | 43 / 43 / 0 | **+110.79** | **+1.288** |
| Persuasion, buyer | 37 | 22 / 15 / 0 | **+34.77** | **+0.940** |
| Persuasion, seller | 41 | 16 / 25 / 0 | **+20.90** | **+0.510** |
| Negotiation, buyer | 11 | 4 / 7 / 0 | **-20.33** | **-1.848** |
| Negotiation, seller | 9 | 3 / 6 / 0 | **-13.40** | **-1.489** |

V33's persuasion seller uses a receiver cutoff and a static low-quality pooling benchmark. For $0<p<1$, $0<c<1$, $Pr(+\mid H)=1$, and a marginal low-quality positive-signal frequency $q$, static obedience after a positive signal requires

$$
\frac{p}{p+(1-p)q}\ge c
\quad\Longrightarrow\quad
q\le q_{\max}=\min\!\left(1,\frac{p(1-c)}{c(1-p)}\right).
$$

V33 targets $q=0.88q_{\max}$ before the terminal round and $q=\min(0.94q_{\max},0.92)$ on it, then paces positive low-quality signals using

$$
a_n=\lfloor(n+1)q\rfloor-\lfloor nq\rfloor,
$$

For fixed $q$, every prefix differs from $nq$ by less than one signal. V33 recomputes $q$ and relaxes it terminally, so this guarantee and the posterior inequality are static design benchmarks, not round-by-round obedience guarantees against a buyer who can infer the pacing phase. The positive persuasion-seller sign is observational because no contemporaneous branch ablation was run. The 248 live outcomes had zero action fallbacks and overshoots. All 500 telemetry rows were caught HTTP 422 reward-harvest failures from six stale non-UUID component-test IDs. V33 overwrote the V28--V30 synthetic flags, while the V31 IDs never matched the prefix classifier; harvesting therefore retried all six. Because `new_telemetry` was measured before harvesting, the guard missed the errors. They did not alter actions or ratings but reveal classification and monitoring-order bugs.

## Agent implementation

The evidence-backed deployment portfolio is family-specific: [`notebooks/04_history_calibrated_equilibrium_cycle_escape_trend_projection.ipynb`](notebooks/04_history_calibrated_equilibrium_cycle_escape_trend_projection.ipynb) for bargaining, [`notebooks/05_role_calibrated_concession_forecasting_sequential_trust_ledger.ipynb`](notebooks/05_role_calibrated_concession_forecasting_sequential_trust_ledger.ipynb) for negotiation, and V3 for persuasion. [`notebooks/06_configuration_safe_purchased_only_trust_credibility_budgeting_contract_validation.ipynb`](notebooks/06_configuration_safe_purchased_only_trust_credibility_budgeting_contract_validation.ipynb) adds stronger validation and configuration-safe memory, but its live persuasion policy is rejected after the negative 35-game batch.

[`notebooks/07_conservative_portfolio_qre_bounded_exploration_confidence_promotion.ipynb`](notebooks/07_conservative_portfolio_qre_bounded_exploration_confidence_promotion.ipynb) packages those three protected policies into one conservative portfolio. It assigns one arm for the entire game, limits under-sampled challenger exploration to 12%, records completed-game payoff when the installed SDK exposes it, and permits promotion only from role- and configuration-local evidence. Its challengers are a quantal-response bargaining calibration, a bounded buyer-only negotiation residual, and separate empirical-seller/lower-confidence buyer persuasion policies. Its first live bargaining batch gained 9.89 points over 40 games with 40/40 agreements, but Alice averaged -0.37 and the overall per-game gain was weaker than V4's earlier batch. Continue to evaluate one family at a time with concurrency 1.

[`notebooks/08_role_gated_checkpoint_learning_stop_loss_persistent_evidence.ipynb`](notebooks/08_role_gated_checkpoint_learning_stop_loss_persistent_evidence.ipynb) tightens exploration to the weak roles only, freezes the V5 negotiation core and V3 persuasion buyer, persists terminal evidence, evaluates in checkpoints, and separates gameplay fallbacks from telemetry. Its first negotiation run gained **50.96** points over 44 games; buyer and seller means were both positive, and all 44 rewards were harvested with zero action fallbacks or telemetry errors. V8 remains the strongest larger-sample negotiation record, while the family policy references remain V4 bargaining, V5 negotiation, and V3 persuasion.

[`notebooks/10_rating_aligned_one_completion_attribution_conservative_optimization.ipynb`](notebooks/10_rating_aligned_one_completion_attribution_conservative_optimization.ipynb) introduced the one-completion attribution guard, but it is no longer the recommended runner. Its first supplied run gained **3.03** negotiation points over two buyer games with zero fallbacks or telemetry errors; the two-game completion after a one-game request demonstrated that `client.run()` did not provide hard exposure control.

[`notebooks/11_champion_batch_runner_multigame_accounting.ipynb`](notebooks/11_champion_batch_runner_multigame_accounting.ipynb) is retained as a documented negative operational result, not a recommended runner. Its unchanged negotiation core lost **44.84** points over 53 games after a request for 24 at concurrency 4. The run had zero policy fallbacks and telemetry errors, but its inability to interrupt the oversized batch exposed the agent to 29 excess completions. V13's low-level one-queue controller supersedes this runner.

[`notebooks/13_controlled_champion_one_queue_append_only_evidence.ipynb`](notebooks/13_controlled_champion_one_queue_append_only_evidence.ipynb) is the current controlled Kaggle runner. It retains the V4/V5/V3 economic policies, uses strict validation and JSONL evidence, and drives the SDK through a low-level one-queue controller that leaves matchmaking as soon as an assignment is observed. Its optional NF4-quantized Qwen3 4B layer runs locally on a 15 GB Kaggle GPU and is restricted to message rewriting; shadow mode is the default and all numeric decisions remain deterministic.

[`notebooks/Glee_competition_23/23_adaptive_defender_peak_drawdown_reservation_protection.ipynb`](notebooks/Glee_competition_23/23_adaptive_defender_peak_drawdown_reservation_protection.ipynb) is the evaluated source of the retained negotiation heuristic. It keeps actions fully rule-based, adds role-aware bargaining and defensive negotiation, freezes the prior persuasion policy, and performs authoritative count/rating checks after every completion. Its V23 evidence supports the negotiation policy only; the Alice bargaining and persuasion-seller branches were replaced in V24. The complete rendered artifacts are preserved in [`notebooks/Glee_competition_23/`](notebooks/Glee_competition_23/).

[`notebooks/Glee_competition_24/24_bargaining_persuasion_repair_surplus_protection_terminal_pooling.ipynb`](notebooks/Glee_competition_24/24_bargaining_persuasion_repair_surplus_protection_terminal_pooling.ipynb) is the evaluated bargaining/persuasion repair. Its persuasion policy gained 4.15 points over ten games with positive buyer and seller aggregates. Its Alice repair was positive, but the complete bargaining batch lost 8.13 because Bob was negative. Preserve V23 negotiation, retain V24 persuasion as the current candidate, and do not resume broad bargaining exposure without a Bob-specific revision. The rendered artifacts are in [`notebooks/Glee_competition_24/`](notebooks/Glee_competition_24/).

[`notebooks/Glee_competition_25/25_role_aware_bargaining_defensive_negotiation_drawdown_control.ipynb`](notebooks/Glee_competition_25/25_role_aware_bargaining_defensive_negotiation_drawdown_control.ipynb) is the evaluated V26 precursor. Bargaining gained 5.86 over eight games and negotiation gained 10.30 over 43, with both stopped by trailing drawdown and no execution errors. Alice and both negotiation roles were positive; Bob remained negative. The rendered artifacts are in [`notebooks/Glee_competition_25/`](notebooks/Glee_competition_25/).

[`notebooks/Glee_competition_26/26_three_family_adaptive_role_calibration_contextual_concession.ipynb`](notebooks/Glee_competition_26/26_three_family_adaptive_role_calibration_contextual_concession.ipynb) is the evaluated V27 precursor. It gained 10.10 in bargaining, 47.41 in negotiation, and 14.56 in persuasion across 73 live games. Repaired Bob and both negotiation roles were positive; persuasion seller remained negative despite a positive family total. The complete rendered artifacts are in [`notebooks/Glee_competition_26/`](notebooks/Glee_competition_26/).

[`notebooks/Glee_competition_27/27_evidence_guided_context_repair_configuration_gated_pooling.ipynb`](notebooks/Glee_competition_27/27_evidence_guided_context_repair_configuration_gated_pooling.ipynb) is the prior evaluated deterministic runner. Its 100-per-family targets were all stopped early by trailing drawdown. Bargaining gained 7.81 over 41 games, negotiation gained 30.97 over 68, and persuasion lost 11.73 over 30. Alice and negotiation sellers were strongly positive; Bob, negotiation buyers, and persuasion sellers were negative. The 139 live outcomes had zero action fallbacks and zero telemetry diagnostics. Complete artifacts are in [`notebooks/Glee_competition_27/`](notebooks/Glee_competition_27/).

[`notebooks/glee_competition_33/33_evidence_locked_role_portfolio_frequency_paced_bayesian_pooling.ipynb`](notebooks/glee_competition_33/33_evidence_locked_role_portfolio_frequency_paced_bayesian_pooling.ipynb) is the latest evaluated deterministic runner. It preserves the positive V27 Alice branch, uses V29's Bob delay recovery, rolls negotiation buyers back to V23, retains the V27 negotiation seller, and introduces static-bound, frequency-paced persuasion pooling. It gained 190.94 bargaining points over 150 games and 55.67 persuasion points over 78, while negotiation lost 33.73 over 20 and stopped on drawdown. The notebook, exact session report, rating outcomes, policy state, and append-only evidence are preserved together in [`notebooks/glee_competition_33/`](notebooks/glee_competition_33/).

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
