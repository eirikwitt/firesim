import dataclasses
from enum import Enum
from datetime import datetime

class Stage(Enum):
    COMPILE = "RTL Generation"
    SYNTHESIS = "Synthesis"
    LINK = "Linking"
    BRAM = "Async BRAM Patching"
    IMPLEMENTATION = "Implementation"
    BITSTREAM = "Bitstream Generation"
    OTHER = "Other"
    TOTAL = "Total build time"


@dataclasses.dataclass
class StageDuration:
    stage: Stage
    start: datetime = None
    duration: float = 0.0
    durations: list = dataclasses.field(default_factory=list)
    failed_durations: list = dataclasses.field(default_factory=list)
    start_regex: list[str] = dataclasses.field(default_factory=list)
    end_regex: str = ""

    def avg(self):
        if self.durations:
            return sum(self.durations) / len(self.durations)
        return 0.0

    def last(self):
        if self.durations:
            return self.durations[-1]
        return 0.0

@dataclasses.dataclass(frozen=True)
class VxConfig:
    clusters: int
    sockets: int
    cores: int = 1
    L2: int = 1024
    L3: int = 2048

    def config_str(self):
        l2_str = f"{self.L2}L2" if self.L2 != 1024 else ""
        l3_str = f"{self.L3}L3" if self.L3 != 2048 else ""
        return f"V{self.sockets}S{self.clusters}C{l3_str}{l2_str}"

    def table_str(self):
        l2_str = "" if self.L2 == 1024 else "No L2" if self.L2 == 0 else f"{self.L2}KB L2"
        l3_str = "" if self.L3 == 2048 else "No L3" if self.L3 == 0 else f"{self.L3}KB L3"
        return f"{self.clusters}Cl-{self.sockets}Co {l3_str} {l2_str}"

    def figure_str(self, times: dict['VxConfig', dict[Stage, StageDuration]]):
        duration = times[self][Stage.TOTAL]
        if duration.durations == duration.failed_durations:
            return f"{self.sockets}Co {self.clusters}Cl*"
        return f"{self.sockets}Co {self.clusters}Cl"

    
    @staticmethod
    def all_configs(sockets=6, clusters=2, max_size=5, l2s=[1024], l3s=[2048]):
        return [VxConfig(2**c, 2**s, 1, l2, l3) for l2 in l2s for l3 in l3s for c in range(clusters) for s in range(sockets) if s+c <= max_size]