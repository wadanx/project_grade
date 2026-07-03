from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class Regulation:
    grades_map: dict[float, tuple[str, str]]
    
    @classmethod
    def default(cls):
        return cls({
            3.7: ("A+", "ممتاز"),
            3.0: ("B", "جيد جدا"),
            2.4: ("C", "جيد"),
            2.0: ("D", "مقبول"),
        })

    def points_to_grade(self, points: float):
        for threshold, grade in sorted(self.grades_map.items(), reverse=True):
            if points >= threshold:
                return grade
        return ("F", "ضعيف")

    def save(self, filename: str = "reg.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=4)

    @classmethod
    def load(cls, filename: str = "reg.json"):
        with open(filename, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        data["grades_map"] = {
            float(k): tuple(v)
            for k, v in data["grades_map"].items()
        }

        return cls(**data)

    @classmethod
    def load_or_create(cls, filename: str = "reg.json"):
        path = Path(filename)

        if path.exists():
            print('loadinng existing reg')
            return cls.load(filename)

        print('creating default reg')
        reg = cls.default()
        reg.save(filename)
        return reg