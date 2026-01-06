import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

PRIMARY, GREEN, GRAY, DARK, WHITE, HEADER_BG = (
    "#3b82f6",
    "#22c55e",
    "#6b7280",
    "#111827",
    "#fff",
    "#1e293b",
)


def fmt(model: str, n: int = 20) -> str:
    if not model:
        return "-"
    name = model.split("/")[-1].replace("-instruct", "").replace("-chat", "")
    return name[: n - 3] + "..." if len(name) > n else name


def generate(data: dict, out: Path):
    runs = sorted(
        data.get("runs", []), key=lambda r: r["summary"].get("avg_score", 0), reverse=True
    )
    if not runs:
        return print("No runs")

    n, tests = len(runs), runs[0]["summary"].get("total_tests", 0)
    best = max(r["summary"].get("avg_score", 0) for r in runs)
    avg = sum(r["summary"].get("avg_score", 0) for r in runs) / n
    fast = min(r["summary"].get("avg_request_time", 0) for r in runs)

    fig = plt.figure(figsize=(12, max(5, 2.5 + n * 0.55)), facecolor=WHITE)
    fig.text(
        0.5,
        0.96,
        "Model Configuration Performance",
        ha="center",
        fontsize=18,
        fontweight="bold",
        color=DARK,
    )
    fig.text(
        0.5,
        0.92,
        f"{n} configs • {tests} tests • Best: {best:.1f} • Avg: {avg:.1f} • Fastest: {fast:.0f}s",
        ha="center",
        fontsize=10,
        color=GRAY,
    )

    ax = fig.add_axes((0.03, 0.06, 0.94, 0.82))
    ax.axis("off")

    cols = [0.07, 0.22, 0.22, 0.26, 0.11, 0.11]
    labels = ["#", "Fast Model", "Balanced Model", "Advanced Model", "Score", "Time"]
    col_x = [sum(cols[:i]) for i in range(len(cols))]

    for j, (lbl, x, w) in enumerate(zip(labels, col_x, cols)):
        ax.add_patch(
            plt.Rectangle((x, 0.89), w - 0.005, 0.07, facecolor=HEADER_BG, transform=ax.transAxes)
        )
        ax.text(
            x + w / 2,
            0.925,
            lbl,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=WHITE,
            transform=ax.transAxes,
        )

    row_h = 1 / (n + 2)
    for i, run in enumerate(runs):
        y = 0.83 - i * row_h
        cfg, s = run["model_config"], run["summary"]
        score, time = s.get("avg_score", 0), s.get("avg_request_time", 0)
        bg = "#f0fdf4" if i == 0 else ("#f8fafc" if i % 2 == 0 else WHITE)

        ax.add_patch(
            plt.Rectangle(
                (0, y - row_h + 0.01),
                0.995,
                row_h - 0.005,
                facecolor=bg,
                edgecolor="#e5e7eb",
                linewidth=0.5,
                transform=ax.transAxes,
            )
        )

        row = [
            (f"#{i+1}", "center", DARK, "normal"),
            (fmt(cfg.get("fast_model", ""), 20), "left", DARK, "normal"),
            (fmt(cfg.get("balanced_model", ""), 20), "left", DARK, "normal"),
            (fmt(cfg.get("advanced_model", ""), 24), "left", DARK, "medium"),
            (f"{score:.2f}", "center", GREEN if i == 0 else PRIMARY, "bold"),
            (f"{time:.0f}s", "center", GRAY, "normal"),
        ]
        for j, (txt, align, clr, wt) in enumerate(row):
            ax.text(
                col_x[j] + (cols[j] / 2 if align == "center" else 0.01),
                y - row_h / 2 + 0.01,
                txt,
                ha=align,
                va="center",
                fontsize=9,
                fontweight=wt,
                color=clr,
                transform=ax.transAxes,
            )

    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close()
    print(f"✓ Saved: {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", type=Path)
    args = p.parse_args()

    paths = [args.input] if args.input else []
    paths += [
        Path("tests/chat_server_tests/output/performance_history.json"),
        Path("output/performance_history.json"),
    ]
    for path in paths:
        if path and path.exists():
            print(f"Loading: {path}")
            data = json.loads(path.read_text())
            out = Path("docs/images/performance_summary.png")
            out.parent.mkdir(parents=True, exist_ok=True)
            generate(data, out)
            return
    print("Could not find performance_history.json")


if __name__ == "__main__":
    main()
