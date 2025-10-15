import os
import re
from datetime import datetime

from rich.console import Console
from rich.table import Table
from vortex_configs import *
import matplotlib.pyplot as plt
import numpy as np
import matplot2tikz

script_dir = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(script_dir, "logs")  # Adjust path if needed

MAX_SIZE = 5





def get_build_times(vxconfig: VxConfig):
    build_stages: dict[Stage, StageDuration] = {
        # BuildStage(
        #     "compile",
        #     "RTL Generation",
        #     start_regex=[
        #         r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] mkdir -p /cluster/home/eirikwit/vortex-gpgpu/chipyard/sims/firesim/sim/generated-src/alveo/FireSim-FireSim.+-BaseF1Config1Mem_F25MHz$",
        #     ],
        #     end_regex=[
        #         r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] make\[1\]: Leaving directory '/cluster/home/eirikwit/vortex-gpgpu/chipyard/sims/firesim/sim/midas/src/main/cc'$",
        #     ],
        # ),
        Stage.SYNTHESIS: StageDuration(
            Stage.SYNTHESIS,
            start_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] cd /cluster/home/eirikwit/vortex-gpgpu/chipyard/sims/firesim/sim/generated-src/alveo/FireSim-FireSim.+-BaseF1Config1Mem_F25MHz/u250 && vivado -mode batch -source \./scripts/main\.tcl$",
            ],
            end_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Synth Design complete, checksum: .+$",
            ],
        ),
        # BuildStage("Link", "Linking", durations=[0.0]),
        Stage.BRAM: StageDuration(
            Stage.BRAM,
            start_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] source /cluster/home/eirikwit/vortex-gpgpu/vortex-ntnu/hw/syn/xilinx/firesim/pre_opt_async_bram_patch\.tcl$",
            ],
            end_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Starting Logic Optimization Task$",
            ],
        ),
        Stage.IMPLEMENTATION: StageDuration(
            Stage.IMPLEMENTATION,
            start_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Starting Logic Optimization Task$",
            ],
            end_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Routing Is Done.$",
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] ERROR: first normal implementation failed$",
            ],
        ),
        # BuildStage(
        #     "bitstream",
        #     "Bitstream Generation",
        #     start_regex=[
        #         r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Command: write_bitstream -force design_1_wrapper\.bit$",
        #     ],
        # ),
        Stage.TOTAL: StageDuration(
            Stage.TOTAL,
            start_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] cd /cluster/home/eirikwit/vortex-gpgpu/chipyard/sims/firesim/sim/generated-src/alveo/FireSim-FireSim.+-BaseF1Config1Mem_F25MHz/u250 && vivado -mode batch -source \./scripts/main\.tcl$",
            ],
            end_regex=[
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] # puts \"Done!\"$",
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] ERROR: first normal implementation failed$",
            ],
        ),
    }

    config: str = vxconfig.config_str()
    config_dir = os.path.join(logs_dir, f"build_{config}")
    if not os.path.isdir(config_dir):
        print(f"\033[91mWarning: No logs found for config {config}\033[0m")
        return None

    for log_file in os.listdir(config_dir):
        log_path = os.path.join(config_dir, log_file)
        if not os.path.isfile(log_path):
            continue

        with open(log_path, "r") as f:
            lines = f.readlines()

        build_successful = False
        implementation_failed = False

        for line in lines:
            for stage in build_stages.values():
                for start_regex in stage.start_regex:
                    if start_match := re.match(start_regex, line):
                        if stage.start is not None:
                            print(
                                f"\033[93mWarning: Overwriting start time in {stage.stage.value} stage for {config}/{log_file}\033[0m"
                            )
                        stage.start = extract_timestamp(start_match.group(1))
                for end_regex in stage.end_regex:
                    if end_match := re.match(end_regex, line):
                        if stage.start is None:
                            print(
                                f"\033[91mWarning: Found end time without start time in {stage.stage.value} stage for {config}/{log_file}\033[0m"
                            )
                        else:
                            end_time = extract_timestamp(end_match.group(1))
                            stage.duration += (end_time - stage.start).total_seconds()
                            stage.start = None
            if re.match(
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] # puts \"Done!\"", line
            ):
                build_successful = True
            if re.match(
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] ERROR: first normal implementation failed$",
                line,
            ):
                implementation_failed = True

        for stage in build_stages.values():
            if build_successful:
                stage.durations.append(stage.duration)
            if implementation_failed:
                stage.failed_durations.append(stage.duration)
            stage.duration = 0
            stage.start = None

    if all(not stage.durations for stage in build_stages.values()):
        for stage in build_stages.values():
            stage.durations = stage.failed_durations
            

    build_stages[Stage.OTHER] = StageDuration(
        Stage.OTHER,
        durations=[
            build_stages[Stage.TOTAL].durations[i]
            - sum(
                build_stages[stage].durations[i]
                for stage in [
                    Stage.SYNTHESIS,
                    Stage.BRAM,
                    Stage.IMPLEMENTATION,
                ]
            )
            for i in range(len(build_stages[Stage.TOTAL].durations))
        ],
    )

    return build_stages


def extract_timestamp(timestamp_str):
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")


def build_time_figure(build_times: dict[VxConfig, dict[Stage, StageDuration]]):
    fig, ax = plt.subplots()

    stages = [
        Stage.BRAM,
        Stage.IMPLEMENTATION,
        Stage.SYNTHESIS,
        Stage.OTHER,
    ]
    bottom = np.zeros(len(build_times))
    labels = [config.figure_str(build_times) for config in build_times.keys()]

    for stage in stages:
        ax.bar(
            labels,
            [build_times[config][stage].avg()/ 3600 for config in build_times.keys()],
            bottom=bottom,
            label=stage.value,
        )
        bottom += np.array(
            [build_times[config][stage].avg()/ 3600 for config in build_times.keys()]
        )

    ax.set_ylabel("Time (hours)")
    ax.set_title("Build Times by Stage and Configuration")
    ax.legend(loc="upper left")  # bbox_to_anchor=(1,1)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plt.savefig("build_times.svg")
    plt.savefig("build_times.png")
    matplot2tikz.save("build_times.tex")


def build_fraction_figure(build_times: dict[VxConfig, dict[Stage, StageDuration]]):
    fig, ax = plt.subplots()

    stages = [
        Stage.BRAM,
        Stage.IMPLEMENTATION,
        Stage.SYNTHESIS,
        Stage.OTHER,
    ]
    bottom = np.zeros(len(build_times))
    labels = [config.figure_str(build_times) for config in build_times.keys()]
    for stage in stages:
        ax.bar(
            labels,
            [
                build_time[stage].avg() / build_time[Stage.TOTAL].avg()
                for build_time in build_times.values()
            ],
            bottom=bottom,
            label=stage.value,
        )
        bottom += np.array(
            [
                build_time[stage].avg() / build_time[Stage.TOTAL].avg()
                for build_time in build_times.values()
            ]
        )

    ax.set_ylabel("Fraction of Total Time")
    ax.set_title("Build Time Fractions by Stage and Configuration")
    ax.legend(loc="lower right")  # bbox_to_anchor=(1,1)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plt.savefig("build_fraction.svg")


def clustered_build_time_figure(build_times: dict[VxConfig, dict[Stage, StageDuration]]):
    clusters = {
        "With L3": {
            config: times for config, times in build_times.items() if config.L3 > 0
        },
        "Without L3": {
            config: times for config, times in build_times.items() if config.L3 == 0
        },
    }
    fig, axs = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    stages = [Stage.BRAM, Stage.IMPLEMENTATION, Stage.SYNTHESIS, Stage.OTHER]
    for ax, (cluster_name, cluster_times) in zip(axs, clusters.items()):
        bottom = np.zeros(len(cluster_times))
        labels = [config.figure_str(cluster_times) for config in cluster_times.keys()]

        for stage in stages:
            ax.bar(
                labels,
                [
                    cluster_times[config][stage].avg() / 3600
                    for config in cluster_times.keys()
                ],
                bottom=bottom,
                label=stage.value,
            )
            bottom += np.array(
                [
                    cluster_times[config][stage].avg() / 3600
                    for config in cluster_times.keys()
                ]
            )

        ax.set_title(cluster_name)
        ax.tick_params(axis="x", rotation=45)
    axs[0].set_ylabel("Time (hours)")
    axs[1].legend(loc="upper left", bbox_to_anchor=(1, 1))  # bbox_to_anchor=(1,1)
    plt.tight_layout()
    plt.savefig("clustered_build_times.svg")


def clustered_build_fraction_figure(
    build_times: dict[VxConfig, dict[Stage, StageDuration]],
):
    clusters = {
        "With L3": {
            config: times for config, times in build_times.items() if config.L3 > 0
        },
        "Without L3": {
            config: times for config, times in build_times.items() if config.L3 == 0
        },
    }
    fig, axs = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    stages = [
        Stage.SYNTHESIS,
        Stage.BRAM,
        Stage.IMPLEMENTATION,
        Stage.OTHER,
    ]
    for ax, (cluster_name, cluster_times) in zip(axs, clusters.items()):
        bottom = np.zeros(len(cluster_times))
        labels = [config.figure_str(cluster_times) for config in cluster_times.keys()]

        for stage in stages:
            ax.bar(
                labels,
                [
                    build_time[stage].avg() / build_time[Stage.TOTAL].avg()
                    for build_time in cluster_times.values()
                ],
                bottom=bottom,
                label=stage.value,
            )
            bottom += np.array(
                [
                    build_time[stage].avg() / build_time[Stage.TOTAL].avg()
                    for build_time in cluster_times.values()
                ]
            )

        ax.set_title(cluster_name)
        ax.tick_params(axis="x", rotation=45)
    axs[0].set_ylabel("Fraction of Total Time")
    axs[1].legend(loc="lower right", bbox_to_anchor=(1, 1))
    plt.tight_layout()
    plt.savefig("clustered_fractions.svg")


def main():

    configs = VxConfig.all_configs(
        sockets=6, clusters=2, max_size=MAX_SIZE, l2s=[1024], l3s=[2048]
    )
    for config in configs:
        print(config.config_str(), config.table_str())
    build_times: dict[VxConfig, dict[Stage, StageDuration]] = {}
    for config in configs:
        build_times[config] = get_build_times(config)

    table = Table(title="Build Times Summary")
    table.add_column("Config", justify="Right", style="cyan", no_wrap=True)
    for stage in (Stage.SYNTHESIS, Stage.BRAM, Stage.IMPLEMENTATION, Stage.OTHER):
        table.add_column(f"{stage.value} (s)", justify="right", style="green")
        table.add_column("(%)", justify="right", style="blue")
        # table.add_column(f"{stage} Last (s)", justify="right", style="magenta")
        # table.add_column(f"{stage} Min (s)", justify="right", style="yellow")
        # table.add_column(f"{stage} Max (s)", justify="right", style="red")
    table.add_column(f"{Stage.TOTAL.value} (s)", justify="right", style="green")
    table.add_column(f"Min (s)", justify="right", style="yellow")
    table.add_column(f"Max (s)", justify="right", style="red")
    for config, times in build_times.items():
        row = [config.table_str()]

        for stage in (
            Stage.SYNTHESIS,
            Stage.BRAM,
            Stage.IMPLEMENTATION,
            Stage.OTHER,
            Stage.TOTAL,
        ):
            stage_d = times[stage]

            if stage_d.durations:
                # last = f"{durations[-1]:.2f}"
                avg = f"{stage_d.avg():,.0f}"
                fraction = f"{stage_d.avg()/(sum(times[Stage.TOTAL].durations)/len(times[Stage.TOTAL].durations)):.0%}"

                # min_dur = f"{min(durations):.2f}"
                # max_dur = f"{max(durations):.2f}"
            else:
                last = avg = min_dur = max_dur = fraction = "N/A"
            row.extend([avg, fraction])
        row.pop()  # Remove last fraction
        row.append(f"{min(times[Stage.TOTAL].durations):,.0f}")
        row.append(f"{max(times[Stage.TOTAL].durations):,.0f}")

        table.add_row(*row)

    console = Console()
    console.print(table)

    # clustered_build_fraction_figure(build_times)
    # clustered_build_time_figure(build_times)
    build_time_figure(build_times)
    build_fraction_figure(build_times)

    # for filename in os.listdir(logs_dir):
    #     file_path = os.path.join(logs_dir, filename)
    #     if os.path.isfile(file_path):
    #         get_build_times(file_path)


if __name__ == "__main__":
    main()
