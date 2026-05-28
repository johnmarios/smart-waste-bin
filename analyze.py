import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import sys


from datetime import datetime


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

    # Create DataFrame
    df = pd.DataFrame(records)

    # Keep only latest 100 events
    df = df.tail(100)

    # -----------------------------------
    # Timestamp Handling
    # -----------------------------------

    if "resultTime" in df.columns:

        df["timestamp"] = pd.to_datetime(
            df["resultTime"]
        )

    elif "event_time" in df.columns:

        df["timestamp"] = pd.to_datetime(
            df["event_time"]
        )

    # -----------------------------------
    # Latency Conversion
    # -----------------------------------

    if "latency_seconds" in df.columns:

        df["latency_ms"] = (
            df["latency_seconds"] * 1000
        )


    # -----------------------------------
    # Time Features
    # -----------------------------------

    if "timestamp" in df.columns:

        df["hour"] = df["timestamp"].dt.hour

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
# Plot Events Per Hour
# -----------------------------------

def plot_events_per_hour(df):

    # Group by hour and count events
    hourly = (
        df.groupby("hour")
        .size()
        .reset_index(name="event_count")
    )

    # Create figure
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    # Create bar chart
    sns.barplot(
        data=hourly,
        x="hour",
        y="event_count",
        color="blue",
        ax=ax
    )

    # Labels and title
    ax.set_xlabel("Hour of Day")

    ax.set_ylabel("Number of Events")

    ax.set_title(
        "Motion Events by Hour of Day"
    )

    # Adjust layout
    plt.tight_layout()

    # Save chart
    output_path = os.path.join(
        CHARTS_DIR,
        "events_per_hour.png"
    )

    plt.savefig(
        output_path,
        dpi=150
    )

    # Close figure
    plt.close(fig)

    print(
        "Saved: events_per_hour.png"
    )


# -----------------------------------
# Plot Latency Distribution
# -----------------------------------

def plot_latency_distribution(df):

    # Check if latency column exists
    if "latency_ms" not in df.columns:

        print(
            "Skipping latency chart: "
            "'latency_ms' column not found."
        )

        return

    # Create figure
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    # Create histogram with KDE
    sns.histplot(
        data=df,
        x="latency_ms",
        kde=True,
        color="green",
        ax=ax
    )

    # Labels and title
    ax.set_xlabel(
        "Latency (ms)"
    )

    ax.set_ylabel(
        "Frequency"
    )

    ax.set_title(
        "Distribution of Pipeline Latency"
    )

    # Adjust layout
    plt.tight_layout()

    # Save chart
    output_path = os.path.join(
        CHARTS_DIR,
        "latency_distribution.png"
    )

    plt.savefig(
        output_path,
        dpi=150
    )

    # Close figure
    plt.close(fig)

    print(
        "Saved: latency_distribution.png"
    )

# -----------------------------------
# Plot Events Over Time
# -----------------------------------

def plot_events_over_time(df):

    # Group by date and count events
    daily = (
        df.groupby("date")
        .size()
        .reset_index(name="event_count")
    )

    # Create figure
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    # Create line chart
    sns.lineplot(
        data=daily,
        x="date",
        y="event_count",
        marker="o",
        color="orangered",
        ax=ax
    )

    # Labels and title
    ax.set_xlabel("Date")

    ax.set_ylabel("Number of Events")

    ax.set_title(
        "Daily Motion Events Over Time"
    )

    # Rotate x-axis labels
    plt.xticks(rotation=45)

    # Adjust layout
    plt.tight_layout()

    # Save chart
    output_path = os.path.join(
        CHARTS_DIR,
        "events_over_time.png"
    )

    plt.savefig(
        output_path,
        dpi=150
    )

    # Close figure
    plt.close(fig)

    print(
        "Saved: events_over_time.png"
    )




# -----------------------------------
# Plot Heatmap
# -----------------------------------

def plot_heatmap(df):

    # Day order
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    # Group by day and hour
    pivot = (
        df.groupby(
            ["day_of_week", "hour"]
        )
        .size()
        .reset_index(name="count")
    )

    # Create pivot table
    pivot = pivot.pivot(
        index="day_of_week",
        columns="hour",
        values="count"
    )

    # Replace missing values
    pivot = pivot.fillna(0)

    # Reorder days
    pivot = pivot.reindex(day_order)

    # Create figure
    fig, ax = plt.subplots(
        figsize=(12, 5)
    )

    # Create heatmap
    sns.heatmap(
        pivot,
        cmap="YlOrRd",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        ax=ax
    )

    # Labels and title
    ax.set_xlabel(
        "Hour of Day"
    )

    ax.set_ylabel("")

    ax.set_title(
        "Motion Events: Hour × Day of Week"
    )

    # Adjust layout
    plt.tight_layout()

    # Save chart
    output_path = os.path.join(
        CHARTS_DIR,
        "heatmap_hour_day.png"
    )

    plt.savefig(
        output_path,
        dpi=150
    )

    # Close figure
    plt.close(fig)

    print(
        "Saved: heatmap_hour_day.png"
    )



# -----------------------------------
# Plot Latency Over Time
# -----------------------------------

def plot_latency_over_time(df):

    # Check required columns
    if (
        "latency_ms" not in df.columns
        or
        "timestamp" not in df.columns
    ):

        print(
            "Skipping latency-over-time chart: "
            "required columns not found."
        )

        return

    # Create figure
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    # Create scatter plot
    sns.scatterplot(
        data=df,
        x="timestamp",
        y="latency_ms",
        alpha=0.5,
        s=15,
        color="purple",
        ax=ax
    )

    # Labels and title
    ax.set_xlabel("Time")

    ax.set_ylabel(
        "Latency (ms)"
    )

    ax.set_title(
        "Latency Over Time"
    )

    # Rotate x-axis labels
    plt.xticks(rotation=45)

    # Adjust layout
    plt.tight_layout()

    # Save chart
    output_path = os.path.join(
        CHARTS_DIR,
        "latency_over_time.png"
    )

    plt.savefig(
        output_path,
        dpi=150
    )

    # Close figure
    plt.close(fig)

    print(
        "Saved: latency_over_time.png"
    )



if __name__ == "__main__":


    # Get filepath from command-line
    if len(sys.argv) > 1:

        filepath = sys.argv[1]

    else:

        filepath = "data/consumer/events.jsonl"

    print(
        f"Loading events from: {filepath}"
    )

    # Load events
    df = load_events(filepath)

    print(
        f"Loaded {len(df)} events"
    )

    # Check if DataFrame is empty
    if df.empty:

        print(
            "No data found. "
            "Run the pipeline first."
        )

        sys.exit(1)

    # Generate charts
    plot_events_per_hour(df)

    plot_latency_distribution(df)

    plot_events_over_time(df)

    plot_heatmap(df)

    plot_latency_over_time(df)

    print(
        f"All charts saved to: "
        f"{CHARTS_DIR}"
    )