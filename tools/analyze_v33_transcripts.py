"""Audit V33 rating outcomes and the exported human-readable transcripts.

The transcript export has no game IDs and contains fewer games than the rating
CSV.  Consequently, this script deliberately analyzes the two sources in
parallel and never performs a positional row join between them.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.parent.name == "paper":
    PAPER_ROOT = SCRIPT_DIR.parent
    ROOT = PAPER_ROOT.parent
else:
    ROOT = SCRIPT_DIR.parent
    PAPER_ROOT = ROOT / "paper"
PAPER_DATA = PAPER_ROOT / "data"
PAPER_FIGURES = PAPER_ROOT / "figures"
PAPER_TABLES = PAPER_ROOT / "tables"
TRANSCRIPT_PATH = (
    PAPER_DATA / "all_game_transcripts_v33.txt"
    if (PAPER_DATA / "all_game_transcripts_v33.txt").exists()
    else ROOT / "all_game_transcripts_v33.txt"
)
RATING_PATH = (
    PAPER_DATA / "v33_rating_outcomes.csv"
    if (PAPER_DATA / "v33_rating_outcomes.csv").exists()
    else ROOT / "notebooks" / "glee_competition_33" / "glee_v33_rating_outcomes.csv"
)

FAMILY_ORDER = ("bargaining", "persuasion", "negotiation")
TARGETS = {family: 150 for family in FAMILY_ORDER}
FAMILY_STOP_LOSS = {"bargaining": 30.0, "negotiation": 40.0, "persuasion": 28.0}
FAMILY_MAX_DRAWDOWN = {"bargaining": 24.0, "negotiation": 30.0, "persuasion": 22.0}
ROLE_STOP_LOSS = {"bargaining": 24.0, "negotiation": 28.0, "persuasion": 20.0}
ROLE_MAX_DRAWDOWN = {"bargaining": 18.0, "negotiation": 22.0, "persuasion": 16.0}
MIN_FAMILY_GAMES = 20
MIN_ROLE_GAMES = 10


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def parse_money(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"-?\$?([0-9][0-9,]*(?:\.[0-9]+)?)", value)
    return float(match.group(1).replace(",", "")) if match else None


def next_nonempty(lines: list[str], index: int) -> str | None:
    for line in lines[index + 1 :]:
        if line.strip():
            return line.strip()
    return None


def parse_setup(block: str) -> dict[str, str]:
    setup_match = re.search(r"(?ms)^Game setup\s*$\n(.*?)(?=^Round \d+\s*$)", block)
    if not setup_match:
        return {}
    lines = setup_match.group(1).splitlines()
    setup: dict[str, str] = {}
    for index, line in enumerate(lines):
        if re.fullmatch(r"[^:]{2,50}:", line.strip()):
            value = next_nonempty(lines, index)
            if value is not None:
                setup[line.strip()[:-1].lower().replace(" ", "_")] = value
    return setup


def canonical_role(family: str, raw_role: str | None) -> str:
    if not raw_role:
        return "unknown"
    role = raw_role.lower()
    if family == "bargaining":
        return "alice" if role == "alice" else "bob"
    return role


def signal_polarity(value: str) -> bool | None:
    text = value.strip().lower().replace("_", " ")
    text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()
    negatives = (
        "do not buy", "don't buy", "should not buy", "shouldn't buy",
        "do not recommend", "don't recommend", "recommend against",
        "not worth", "not a good", "not high quality", "low quality",
        "bad product", "buying would be foolish",
    )
    positives = (
        "buy this", "recommend buying", "recommend this", "worth it",
        "high quality", "great product", "good product", "positive",
    )
    if text in {"no", "false", "negative", "not recommended"}:
        return False
    words = set(text.split())
    if any(phrase in text for phrase in negatives) or words & {"pass", "skip", "avoid"}:
        return False
    if text in {"yes", "true", "recommended"}:
        return True
    if text == "buy" or any(phrase in text for phrase in positives):
        return True
    return None


def parse_transcripts() -> list[dict[str, object]]:
    text = TRANSCRIPT_PATH.read_text(encoding="utf-8-sig")
    starts = list(re.finditer(r"(?m)^(Bargaining|Persuasion|Negotiation)\s*$\n^Game transcript\s*$", text))
    records: list[dict[str, object]] = []
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(starts):
        primary = text[match.start() : starts[index + 1].start() if index + 1 < len(starts) else len(text)]
        family = match.group(1).lower()
        # Two export records lost their repeated family/transcript header but
        # retained a second Game setup and Final result. Split on every setup
        # marker so those records are counted rather than silently merged.
        setup_starts = [item.start() for item in re.finditer(r"(?m)^Game setup\s*$", primary)]
        for subindex, setup_start in enumerate(setup_starts):
            start = 0 if subindex == 0 else setup_start
            end = setup_starts[subindex + 1] if subindex + 1 < len(setup_starts) else len(primary)
            blocks.append((family, primary[start:end]))

    for index, (family, block) in enumerate(blocks):
        setup = parse_setup(block)
        timestamp_match = re.search(r"Game transcript\s*\n([^\n]+)", block)
        role_match = re.search(r"(?m)^You \((Alice|Bob|Seller|Buyer)\)\s*$", block)
        raw_role = role_match.group(1) if role_match else None
        if raw_role is None:
            # When the opponent makes the only proposal, the export omits the
            # user's parenthetical role and prints only the opponent label.
            actor_match = re.search(r"(?m)^(Alice|Bob|Seller|Buyer)\s*$", block)
            if actor_match:
                actor = actor_match.group(1)
                raw_role = {"Alice": "Bob", "Bob": "Alice", "Seller": "Buyer", "Buyer": "Seller"}[actor]
        final_match = re.search(r"(?m)^Final result\s+[—-]\s*(.+?)\s*$", block)
        rounds = [int(item) for item in re.findall(r"(?m)^Round (\d+)\s*$", block)]
        payoff_match = re.search(r"(?ms)^Your payoff\s*$\n\s*([^\n]+)", block)
        opponent_match = re.search(r"(?ms)^Opponent\s*$\n\s*([^\n]+)", block)

        outcome_text = clean(final_match.group(1)) if final_match else "unknown"
        outcome_key = {
            "You reached a deal": "agreement",
            "One side left the table": "walkaway",
            "No deal was reached": "no_deal",
            "All rounds played": "all_rounds",
        }.get(outcome_text, outcome_text.lower().replace(" ", "_"))

        purchases = re.findall(r"Buyer:\s*(Bought|Passed)\s*(high quality|low quality)?", block, re.I)
        purchase_counts: Counter[str] = Counter()
        for decision, quality in purchases:
            key = decision.lower()
            purchase_counts[key] += 1
            if quality:
                purchase_counts[f"{key}_{quality.lower().replace(' ', '_')}"] += 1
                purchase_counts[f"observed_{quality.lower().replace(' ', '_')}"] += 1

        signal_counts: Counter[str] = Counter()
        if family == "persuasion":
            round_blocks = re.findall(
                r"(?ms)^Round \d+\s*$\n(.*?)(?=^Round \d+\s*$|^Final result)", block
            )
            for round_block in round_blocks:
                seller_match = re.search(r"(?m)^Seller:\s*[“\"]?(.*?)[”\"]?\s*$", round_block)
                buyer_match = re.search(r"Buyer:\s*(Bought|Passed)\s*(high quality|low quality)?", round_block, re.I)
                polarity = signal_polarity(seller_match.group(1)) if seller_match else None
                signal = "positive" if polarity is True else "negative" if polarity is False else "unknown"
                signal_counts[signal] += 1
                if buyer_match:
                    decision = buyer_match.group(1).lower()
                    quality = buyer_match.group(2).lower().replace(" ", "_") if buyer_match.group(2) else "unobserved"
                    signal_counts[f"{signal}_{decision}"] += 1
                    signal_counts[f"{signal}_{quality}"] += 1

        record: dict[str, object] = {
            "transcript_index": index + 1,
            "family_index": 1 + sum(1 for prior in records if prior["family"] == family),
            "family": family,
            "timestamp": clean(timestamp_match.group(1)) if timestamp_match else "",
            "role": canonical_role(family, raw_role),
            "outcome": outcome_key,
            "rounds_observed": len(set(rounds)),
            "last_round_number": max(rounds) if rounds else 0,
            "your_payoff": parse_money(payoff_match.group(1) if payoff_match else None),
            "opponent_payoff": parse_money(opponent_match.group(1) if opponent_match else None),
            "information": setup.get("information", "not_shown").lower(),
            "messages": setup.get("messages", "not_applicable").lower(),
            "max_rounds": setup.get("max_rounds", setup.get("rounds", "unknown")),
            "amount_or_price": parse_money(setup.get("amount_to_divide", setup.get("price"))),
            "your_valuation": parse_money(setup.get("your_valuation")),
            "opponent_valuation": parse_money(setup.get("opponent_valuation")),
            "high_quality_chance": parse_money(setup.get("chance_of_high_quality")),
            "high_quality_value": parse_money(setup.get("high_quality_value")),
            "low_quality_value": parse_money(setup.get("low_quality_value")),
            "bought": purchase_counts["bought"],
            "passed": purchase_counts["passed"],
            "bought_high": purchase_counts["bought_high_quality"],
            "bought_low": purchase_counts["bought_low_quality"],
            "passed_high": purchase_counts["passed_high_quality"],
            "passed_low": purchase_counts["passed_low_quality"],
            "observed_high": purchase_counts["observed_high_quality"],
            "observed_low": purchase_counts["observed_low_quality"],
            "positive_signal": signal_counts["positive"],
            "negative_signal": signal_counts["negative"],
            "unknown_signal": signal_counts["unknown"],
            "positive_bought": signal_counts["positive_bought"],
            "negative_bought": signal_counts["negative_bought"],
            "positive_high": signal_counts["positive_high_quality"],
            "positive_low": signal_counts["positive_low_quality"],
            "negative_high": signal_counts["negative_high_quality"],
            "negative_low": signal_counts["negative_low_quality"],
        }
        records.append(record)
    return records


def load_ratings() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with RATING_PATH.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            if raw["game_id"] == "rating-credit-live-like":
                continue
            context = json.loads(raw["context"])
            family = raw["family"]
            row: dict[str, object] = {
                **raw,
                "rating_delta": float(raw["rating_delta"]),
                "context_tuple": context,
                "information": "",
                "horizon_bucket": "",
                "mode": "",
                "values_known": "",
                "prior_bucket": "",
                "cutoff_bucket": "",
                "discount_bucket": "",
            }
            if family == "bargaining":
                row.update(information=context[1], horizon_bucket=context[2], discount_bucket=context[3])
            elif family == "negotiation":
                row.update(information=context[1], horizon_bucket=context[2])
            else:
                row.update(
                    mode=context[1], values_known=context[2], horizon_bucket=context[3],
                    prior_bucket=context[4], cutoff_bucket=context[5]
                )
            rows.append(row)
    return rows


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def exact_sign_p(positive: int, negative: int) -> float:
    n = positive + negative
    if n == 0:
        return 1.0
    k = min(positive, negative)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def lag1(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    left, right = values[:-1], values[1:]
    left_mean, right_mean = statistics.mean(left), statistics.mean(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    denominator = math.sqrt(
        sum((a - left_mean) ** 2 for a in left) * sum((b - right_mean) ** 2 for b in right)
    )
    return numerator / denominator if denominator else None


def distribution(values: list[float]) -> dict[str, float | int | None]:
    n = len(values)
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    positive = sum(value > 0 for value in values)
    negative = sum(value < 0 for value in values)
    zero = n - positive - negative
    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    losing_streak = 0
    max_losing_streak = 0
    for value in values:
        running += value
        peak = max(peak, running)
        max_drawdown = max(max_drawdown, peak - running)
        losing_streak = losing_streak + 1 if value < 0 else 0
        max_losing_streak = max(max_losing_streak, losing_streak)
    sem = sd / math.sqrt(n) if n else 0.0
    return {
        "n": n,
        "sum": sum(values),
        "mean": mean,
        "sd": sd,
        "median": statistics.median(values),
        "q10": quantile(values, 0.10),
        "q25": quantile(values, 0.25),
        "q75": quantile(values, 0.75),
        "q90": quantile(values, 0.90),
        "iqr": quantile(values, 0.75) - quantile(values, 0.25),
        "mad": statistics.median([abs(value - statistics.median(values)) for value in values]),
        "minimum": min(values),
        "maximum": max(values),
        "positive": positive,
        "zero": zero,
        "negative": negative,
        "positive_rate": positive / n,
        "sign_test_p": exact_sign_p(positive, negative),
        "naive_ci_low": mean - 1.96 * sem,
        "naive_ci_high": mean + 1.96 * sem,
        "lag1_autocorrelation": lag1(values),
        "max_drawdown": max_drawdown,
        "ending_drawdown": peak - running,
        "max_losing_streak": max_losing_streak,
    }


def grouped_statistics(rows: list[dict[str, object]], keys: tuple[str, ...]) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[float]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(float(row["rating_delta"]))
    output = []
    def group_order(item: tuple[tuple[object, ...], list[float]]) -> tuple[object, ...]:
        group = item[0]
        family_rank = FAMILY_ORDER.index(str(group[0])) if str(group[0]) in FAMILY_ORDER else len(FAMILY_ORDER)
        return (family_rank, *(str(value) for value in group[1:]))

    for group, values in sorted(groups.items(), key=group_order):
        output.append({**dict(zip(keys, group)), **distribution(values)})
    return output


def transcript_configuration_statistics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    keys = ("family", "role", "information", "messages", "max_rounds", "amount_or_price")
    groups: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output: list[dict[str, object]] = []
    for group, items in sorted(groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        outcomes = Counter(str(item["outcome"]) for item in items)
        payoffs = [float(item["your_payoff"]) for item in items if item["your_payoff"] is not None]
        output.append({
            **dict(zip(keys, group)),
            "n": len(items),
            "agreements": outcomes["agreement"],
            "walkaways": outcomes["walkaway"],
            "no_deals": outcomes["no_deal"],
            "all_rounds": outcomes["all_rounds"],
            "agreement_rate": outcomes["agreement"] / len(items),
            "median_rounds_observed": statistics.median(int(item["rounds_observed"]) for item in items),
            "mean_your_payoff": statistics.mean(payoffs) if payoffs else None,
            "buyer_purchase_rate": (
                sum(int(item["bought"]) for item in items)
                / max(1, sum(int(item["bought"]) + int(item["passed"]) for item in items))
            ),
        })
    return output


def first_stop(rows: list[dict[str, object]], scale: float = 1.0,
               min_family: int = MIN_FAMILY_GAMES, min_role: int = MIN_ROLE_GAMES) -> dict[str, object]:
    family = str(rows[0]["family"])
    cumulative = 0.0
    peak = 0.0
    role_values: dict[str, list[float]] = defaultdict(list)
    for index, row in enumerate(rows, start=1):
        delta = float(row["rating_delta"])
        cumulative += delta
        peak = max(peak, cumulative)
        role_values[str(row["role"])].append(delta)
        for role, values in role_values.items():
            if len(values) < min_role:
                continue
            role_cumulative = sum(values)
            role_running = 0.0
            role_peak = 0.0
            for value in values:
                role_running += value
                role_peak = max(role_peak, role_running)
            if role_cumulative <= -ROLE_STOP_LOSS[family] * scale:
                return {"stop_n": index, "reason": f"role_loss:{role}", "cumulative": cumulative}
            if role_peak - role_cumulative >= ROLE_MAX_DRAWDOWN[family] * scale:
                return {"stop_n": index, "reason": f"role_drawdown:{role}", "cumulative": cumulative}
        if index >= min_family:
            if cumulative <= -FAMILY_STOP_LOSS[family] * scale:
                return {"stop_n": index, "reason": "family_loss", "cumulative": cumulative}
            if peak - cumulative >= FAMILY_MAX_DRAWDOWN[family] * scale:
                return {"stop_n": index, "reason": "family_drawdown", "cumulative": cumulative}
        if index >= TARGETS[family]:
            return {"stop_n": index, "reason": "target", "cumulative": cumulative}
    return {"stop_n": len(rows), "reason": "observed_end", "cumulative": cumulative}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return "--"
    if isinstance(value, (float, int)):
        return f"{value:.{digits}f}"
    return str(value).replace("_", r"\_")


def num2(value: object) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def write_generated_tables(family_stats: list[dict[str, object]], role_stats: list[dict[str, object]],
                           rating_config_stats: list[dict[str, object]], transcript_rows: list[dict[str, object]],
                           sensitivity: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{table}[t]", r"\caption{Distribution of assignment-level displayed rating changes. The interval is an ordinary IID diagnostic only; sequential matchmaking and adaptive stopping invalidate confirmatory interpretation.}",
        r"\label{tab:v33-distribution}", r"\centering\scriptsize",
        r"\begin{tabular}{lrrrrrr}", r"\toprule",
        r"Family & $+ / 0 / -$ & Mean & Median & SD & IQR & Naive 95\% CI \\", r"\midrule",
    ]
    for row in family_stats:
        signs = f"{row['positive']}/{row['zero']}/{row['negative']}"
        interval = f"[{num2(row['naive_ci_low'])}, {num2(row['naive_ci_high'])}]"
        lines.append(f"{str(row['family']).title()} & {signs} & {num2(row['mean'])} & {num2(row['median'])} & {num2(row['sd'])} & {num2(row['iqr'])} & {interval} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    lines += [
        r"\begin{table}[t]", r"\caption{Coarse context splits from the policy's recorded context keys. Horizon bucket 0 is below five rounds and bucket 2 is 12--29 rounds; persuasion configurations additionally separate signal mode and whether receiver values were present.}",
        r"\label{tab:v33-context-distribution}", r"\centering\scriptsize", r"\begin{tabular}{llrrrr}", r"\toprule",
        r"Family & Context & $n$ & Sum & Mean & $+ / 0 / -$ \\", r"\midrule",
    ]
    for row in rating_config_stats:
        family = str(row["family"])
        if family == "bargaining":
            context = f"{row['information']}, h{row['horizon_bucket']}"
        elif family == "negotiation":
            context = f"{row['information']}, h{row['horizon_bucket']}"
        else:
            context = f"{row['mode']}, {row['values_known']}"
        signs = f"{row['positive']}/{row['zero']}/{row['negative']}"
        lines.append(f"{family.title()} & {fmt(context)} & {row['n']} & {num2(row['sum'])} & {num2(row['mean'])} & {signs} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    lines += [
        r"\begin{table}[t]", r"\caption{Role-stratified assignment-level rating changes.}", r"\label{tab:v33-role-distribution}",
        r"\centering\scriptsize", r"\begin{tabular}{llrrrrr}", r"\toprule",
        r"Family & Role & $n$ & Sum & Median & SD & $+ / 0 / -$ \\", r"\midrule",
    ]
    for row in role_stats:
        signs = f"{row['positive']}/{row['zero']}/{row['negative']}"
        role_name = {"player_1": "Alice", "player_2": "Bob"}.get(str(row["role"]), str(row["role"]).title())
        lines.append(f"{str(row['family']).title()} & {fmt(role_name)} & {row['n']} & {num2(row['sum'])} & {num2(row['median'])} & {num2(row['sd'])} & {signs} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    counts = Counter(str(row["family"]) for row in transcript_rows)
    role_outcomes: Counter[tuple[str, str, str]] = Counter(
        (str(row["family"]), str(row["role"]), str(row["outcome"])) for row in transcript_rows
    )
    lines += [
        r"\begin{table}[t]", rf"\caption{{Outcome counts in the transcript export. Coverage is {len(transcript_rows)} of 248 rated assignments, so these are available-case behavioral summaries and are not joined to rating rows.}}",
        r"\label{tab:v33-transcript-outcomes}", r"\centering\scriptsize", r"\begin{tabular}{llrrrr}", r"\toprule",
        r"Family & Role & $n$ & Agreement & Walkaway & No deal \\", r"\midrule",
    ]
    for family in FAMILY_ORDER:
        roles = sorted({str(row["role"]) for row in transcript_rows if row["family"] == family})
        for role in roles:
            n = sum(value for (fam, rol, _), value in role_outcomes.items() if fam == family and rol == role)
            lines.append(
                f"{family.title()} & {fmt(role)} & {n} & {role_outcomes[(family, role, 'agreement')]} & "
                f"{role_outcomes[(family, role, 'walkaway')]} & {role_outcomes[(family, role, 'no_deal')]} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    lines += [
        r"\begin{table}[t]", r"\caption{Stop-guard sensitivity when all four loss/drawdown thresholds are multiplied by a common factor. Entries are simulated stop game and reason from the observed family sequence.}",
        r"\label{tab:v33-stop-sensitivity}", r"\centering\scriptsize", r"\begin{tabular}{lrrrrr}", r"\toprule",
        r"Family & $0.50\times$ & $0.75\times$ & $1.00\times$ & $1.25\times$ & $1.50\times$ \\", r"\midrule",
    ]
    by_family_scale = {(str(row["family"]), float(row["threshold_scale"])): row for row in sensitivity if row["scenario"] == "threshold_scale"}
    for family in FAMILY_ORDER:
        cells = []
        for scale in (0.50, 0.75, 1.00, 1.25, 1.50):
            row = by_family_scale[(family, scale)]
            cells.append(f"{row['stop_n']} ({fmt(row['reason'])})")
        lines.append(f"{family.title()} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    (PAPER_TABLES / "v33_statistical_analysis.tex").write_text("\n".join(lines), encoding="utf-8")


def plot_sequences(rows: list[dict[str, object]]) -> None:
    PAPER_FIGURES.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 3, figsize=(10.5, 3.2), constrained_layout=True)
    for axis, family in zip(axes, FAMILY_ORDER):
        family_rows = [row for row in rows if row["family"] == family]
        cumulative = []
        peak = []
        running = 0.0
        running_peak = 0.0
        for row in family_rows:
            running += float(row["rating_delta"])
            running_peak = max(running_peak, running)
            cumulative.append(running)
            peak.append(running_peak)
        x = list(range(1, len(cumulative) + 1))
        drawdown_boundary = [value - FAMILY_MAX_DRAWDOWN[family] for value in peak]
        axis.plot(x, cumulative, color="#1f4e79", linewidth=1.8, label="Cumulative change")
        axis.plot(x, drawdown_boundary, color="#c44e52", linewidth=1.1, linestyle="--", label="Trailing boundary")
        axis.axhline(-FAMILY_STOP_LOSS[family], color="#8172b2", linewidth=1.0, linestyle=":", label="Baseline loss")
        axis.axvline(MIN_FAMILY_GAMES, color="#777777", linewidth=0.8, linestyle="--")
        axis.scatter([x[-1]], [cumulative[-1]], color="#1f4e79", s=18, zorder=4)
        axis.annotate(f"{cumulative[-1]:+.2f}", (x[-1], cumulative[-1]), xytext=(-3, 7), textcoords="offset points", ha="right", fontsize=8)
        axis.set_title(family.title())
        axis.set_xlabel("Assignment")
        axis.grid(axis="y", alpha=0.22, linewidth=0.6)
    axes[0].set_ylabel("Cumulative displayed rating change")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    figure.savefig(PAPER_FIGURES / "v33_sequential_ratings.pdf", bbox_inches="tight")
    figure.savefig(PAPER_FIGURES / "v33_sequential_ratings.png", dpi=220, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    transcript_rows = parse_transcripts()
    rating_rows = load_ratings()
    assert Counter(row["family"] for row in rating_rows) == Counter({"bargaining": 150, "persuasion": 78, "negotiation": 20})
    assert len(transcript_rows) == 220, f"unexpected transcript count: {len(transcript_rows)}"

    family_stats = grouped_statistics(rating_rows, ("family",))
    role_stats = grouped_statistics(rating_rows, ("family", "role"))
    context_stats = (
        grouped_statistics([row for row in rating_rows if row["family"] == "bargaining"], ("family", "role", "information", "horizon_bucket", "discount_bucket"))
        + grouped_statistics([row for row in rating_rows if row["family"] == "negotiation"], ("family", "role", "information", "horizon_bucket"))
        + grouped_statistics([row for row in rating_rows if row["family"] == "persuasion"], ("family", "role", "mode", "values_known", "horizon_bucket", "prior_bucket", "cutoff_bucket"))
    )
    rating_config_stats = (
        grouped_statistics([row for row in rating_rows if row["family"] == "bargaining"], ("family", "information", "horizon_bucket"))
        + grouped_statistics([row for row in rating_rows if row["family"] == "persuasion"], ("family", "mode", "values_known"))
        + grouped_statistics([row for row in rating_rows if row["family"] == "negotiation"], ("family", "information", "horizon_bucket"))
    )
    transcript_config_stats = transcript_configuration_statistics(transcript_rows)

    sensitivity: list[dict[str, object]] = []
    for family in FAMILY_ORDER:
        family_rows = [row for row in rating_rows if row["family"] == family]
        for scale in (0.50, 0.75, 1.00, 1.25, 1.50):
            sensitivity.append({"family": family, "scenario": "threshold_scale", "threshold_scale": scale,
                                "min_family": MIN_FAMILY_GAMES, "min_role": MIN_ROLE_GAMES, **first_stop(family_rows, scale=scale)})
        for min_family, min_role in ((10, 5), (20, 10), (30, 15)):
            sensitivity.append({"family": family, "scenario": "minimum_games", "threshold_scale": 1.0,
                                "min_family": min_family, "min_role": min_role,
                                **first_stop(family_rows, min_family=min_family, min_role=min_role)})

    write_csv(PAPER_DATA / "v33_transcript_games.csv", transcript_rows)
    write_csv(PAPER_DATA / "v33_rating_family_statistics.csv", family_stats)
    write_csv(PAPER_DATA / "v33_rating_role_statistics.csv", role_stats)
    write_csv(PAPER_DATA / "v33_rating_context_statistics.csv", context_stats)
    write_csv(PAPER_DATA / "v33_rating_configuration_statistics.csv", rating_config_stats)
    write_csv(PAPER_DATA / "v33_transcript_configuration_statistics.csv", transcript_config_stats)
    write_csv(PAPER_DATA / "v33_stop_sensitivity.csv", sensitivity)
    write_generated_tables(family_stats, role_stats, rating_config_stats, transcript_rows, sensitivity)
    plot_sequences(rating_rows)

    summary = {
        "rating_rows": len(rating_rows),
        "transcript_rows": len(transcript_rows),
        "transcript_coverage": len(transcript_rows) / len(rating_rows),
        "rating_family_counts": Counter(str(row["family"]) for row in rating_rows),
        "transcript_family_counts": Counter(str(row["family"]) for row in transcript_rows),
        "transcript_outcomes": Counter(f"{row['family']}:{row['outcome']}" for row in transcript_rows),
        "persuasion_round_decisions": {
            key: sum(int(row[key]) for row in transcript_rows if row["family"] == "persuasion")
            for key in ("bought", "passed", "bought_high", "bought_low", "passed_high", "passed_low")
        },
        "persuasion_signals": {
            key: sum(int(row[key]) for row in transcript_rows if row["family"] == "persuasion")
            for key in ("positive_signal", "negative_signal", "unknown_signal", "positive_bought",
                        "negative_bought", "positive_high", "positive_low", "negative_high", "negative_low")
        },
    }
    (PAPER_DATA / "v33_analysis_summary.json").write_text(json.dumps(summary, indent=2, default=dict), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=dict))


if __name__ == "__main__":
    main()
