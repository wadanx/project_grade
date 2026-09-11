from dataclasses import dataclass, field, asdict
import json
from pathlib import Path


@dataclass
class GradeThreshold:
    min_points: float
    letter: str
    label: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GradeThreshold":
        return cls(
            min_points=float(data["min_points"]),
            letter=str(data["letter"]),
            label=str(data["label"]),
        )


@dataclass
class Regulation:
    name: str = "Untitled Regulation"
    thresholds: list[GradeThreshold] = field(default_factory=list)

    @classmethod
    def default(cls) -> "Regulation":
        return cls(
            name="Default",
            thresholds=[
                GradeThreshold(3.7, "A", "ممتاز"),
                GradeThreshold(3.0, "B", "جيد جدا"),
                GradeThreshold(2.4, "C", "جيد"),
                GradeThreshold(2.0, "D", "مقبول"),
            ],
        )

    def sorted_thresholds(self) -> list[GradeThreshold]:
        return sorted(self.thresholds, key=lambda t: t.min_points, reverse=True)

    def points_to_grade(self, points: float) -> tuple[str, str]:
        for threshold in self.sorted_thresholds():
            if points >= threshold.min_points:
                return threshold.letter, threshold.label
        return "F", "ضعيف"

    # ---------- serialization ----------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "thresholds": [t.to_dict() for t in self.sorted_thresholds()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Regulation":
        if "grades_map" in data:
            # Legacy format: {"grades_map": {"3.7": ["A+", "..."], ...}}
            thresholds = [
                GradeThreshold(min_points=float(k), letter=v[0], label=v[1])
                for k, v in data["grades_map"].items()
            ]
            return cls(name=data.get("name", "Untitled Regulation"), thresholds=thresholds)

        thresholds = [GradeThreshold.from_dict(t) for t in data.get("thresholds", [])]
        return cls(name=data.get("name", "Untitled Regulation"), thresholds=thresholds)

    def save(self, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)

    @classmethod
    def load(cls, filename: str) -> "Regulation":
        with open(filename, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def load_or_create(cls, filename: str = "reg.json") -> "Regulation":
        path = Path(filename)

        if path.exists():
            print("loadinng existing reg")
            return cls.load(filename)

        print("creating default reg")
        reg = cls.default()
        reg.save(filename)
        return reg
