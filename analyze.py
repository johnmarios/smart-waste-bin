import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

from pathlib import Path


sns.set_theme(style="whitegrid")

CHARTS_DIR = "data/charts"

os.makedirs(CHARTS_DIR, exist_ok=True)


# -----------------------------------
# Load Events Function
# -----------------------------------

def load_events(filepath):

    records = []

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            try:

                record = json.loads(line)

                records.append(record)

            except json.JSONDecodeError:
                continue

    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Keep latest 100 events
    df = df.tail(100)

    # Timestamp
    if "resultTime" in df.columns:

        df["timestamp"] = pd.to_datetime(
            df["resultTime"]
        )

    elif "event_time" in df.columns:

        df["timestamp"] = pd.to_datetime(
            df["event_time"]
        )

    # Latency
    if "latency_seconds" in df.columns:

        df["latency_ms"] = (
            df["latency_seconds"] * 1000
        )

    # Time Features
    if "timestamp" in df.columns:

        df["hour"] = (
            df["timestamp"]
            .dt.hour
        )

        df["day_of_week"] = (
            df["timestamp"]
            .dt.day_name()
        )

        df["date"] = (
            df["timestamp"]
            .dt.date
        )

        df["minute"] = (
            df["timestamp"]
            .dt.minute
        )

    return df


# -----------------------------------
# Events Per Hour
# -----------------------------------

def plot_events_per_hour(df, suffix):

    if "hour" not in df.columns:
        return

    hourly = (
        df.groupby("hour")
        .size()
        .reset_index(name="event_count")
    )

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    sns.barplot(
        data=hourly,
        x="hour",
        y="event_count",
        color="blue",
        ax=ax
    )

    ax.set_xlabel(
        "Hour of Day"
    )

    ax.set_ylabel(
        "Number of Events"
    )

    ax.set_title(
        f"Motion Events by Hour ({suffix})"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            CHARTS_DIR,
            f"events_per_hour_{suffix}.png"
        ),
        dpi=150
    )

    plt.close(fig)


# -----------------------------------
# Latency Distribution
# -----------------------------------

def plot_latency_distribution(df, suffix):

    if "latency_ms" not in df.columns:
        return

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    sns.histplot(
        data=df,
        x="latency_ms",
        kde=True,
        color="green",
        ax=ax
    )

    ax.set_xlabel(
        "Latency (ms)"
    )

    ax.set_ylabel(
        "Frequency"
    )

    ax.set_title(
        f"Latency Distribution ({suffix})"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            CHARTS_DIR,
            f"latency_distribution_{suffix}.png"
        ),
        dpi=150
    )

    plt.close(fig)


# -----------------------------------
# Events Over Time
# -----------------------------------

def plot_events_over_time(df, suffix):

    if "date" not in df.columns:
        return

    daily = (
        df.groupby("date")
        .size()
        .reset_index(name="event_count")
    )

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    sns.lineplot(
        data=daily,
        x="date",
        y="event_count",
        marker="o",
        color="orangered",
        ax=ax
    )

    ax.set_xlabel("Date")

    ax.set_ylabel(
        "Number of Events"
    )

    ax.set_title(
        f"Events Over Time ({suffix})"
    )

    plt.xticks(
        rotation=45
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            CHARTS_DIR,
            f"events_over_time_{suffix}.png"
        ),
        dpi=150
    )

    plt.close(fig)


# -----------------------------------
# Heatmap
# -----------------------------------

def plot_heatmap(df, suffix):

    if (
        "hour" not in df.columns
        or
        "day_of_week" not in df.columns
    ):
        return

    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    pivot = (
        df.groupby(
            ["day_of_week", "hour"]
        )
        .size()
        .reset_index(name="count")
    )

    pivot = pivot.pivot(
        index="day_of_week",
        columns="hour",
        values="count"
    )

    pivot = pivot.fillna(0)

    pivot = pivot.reindex(
        day_order
    )

    fig, ax = plt.subplots(
        figsize=(12, 5)
    )

    sns.heatmap(
        pivot,
        cmap="YlOrRd",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        ax=ax
    )

    ax.set_xlabel(
        "Hour of Day"
    )

    ax.set_ylabel("")

    ax.set_title(
        f"Heatmap ({suffix})"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            CHARTS_DIR,
            f"heatmap_hour_day_{suffix}.png"
        ),
        dpi=150
    )

    plt.close(fig)


# -----------------------------------
# Latency Over Time
# -----------------------------------

def plot_latency_over_time(df, suffix):

    if (
        "latency_ms" not in df.columns
        or
        "timestamp" not in df.columns
    ):
        return

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    sns.scatterplot(
        data=df,
        x="timestamp",
        y="latency_ms",
        alpha=0.5,
        s=15,
        color="purple",
        ax=ax
    )

    ax.set_xlabel(
        "Time"
    )

    ax.set_ylabel(
        "Latency (ms)"
    )

    ax.set_title(
        f"Latency Over Time ({suffix})"
    )

    plt.xticks(
        rotation=45
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            CHARTS_DIR,
            f"latency_over_time_{suffix}.png"
        ),
        dpi=150
    )

    plt.close(fig)


# -----------------------------------
# Generate All Charts
# -----------------------------------

def generate_charts(df, suffix):

    plot_events_per_hour(
        df,
        suffix
    )

    plot_latency_distribution(
        df,
        suffix
    )

    plot_events_over_time(
        df,
        suffix
    )

    plot_heatmap(
        df,
        suffix
    )

    plot_latency_over_time(
        df,
        suffix
    )


# -----------------------------------
# All Bins Combined
# -----------------------------------

def plots_for_all_events():

    filepath = (
        "data/consumer/events.jsonl"
    )

    if not os.path.exists(
        filepath
    ):
        return

    print(
        f"Processing {filepath}"
    )

    df = load_events(
        filepath
    )

    if df.empty:
        return

    generate_charts(
        df,
        "all"
    )


# -----------------------------------
# Single Bin
# -----------------------------------

def plots_for_file(filepath):

    print(
        f"Processing {filepath}"
    )

    df = load_events(
        filepath
    )

    if df.empty:
        return

    suffix = (
        Path(filepath)
        .stem
        .replace(
            "events_",
            ""
        )
    )

    generate_charts(
        df,
        suffix
    )


# -----------------------------------
# All Individual Bins
# -----------------------------------

def plot_for_bins():

    logs_dir = Path(
        "data/nodered/logs"
    )

    if not logs_dir.exists():

        print(
            f"{logs_dir} not found"
        )

        return

    files = sorted(
        logs_dir.glob(
            "events_wastebin*.jsonl"
        )
    )

    for file in files:

        plots_for_file(
            str(file)
        )


# -----------------------------------
# Main
# -----------------------------------

if __name__ == "__main__":

    plots_for_all_events()

    plot_for_bins()

    print(
        f"\nAll charts saved in "
        f"{CHARTS_DIR}"
    )