from typing import List


class EntityKind:
    THERMO = "thermostat"
    LIGHT = "light"
    ON_OFF = "on_off"

    __all__ = [THERMO, LIGHT, ON_OFF]


class Days:
    MON: str = "mon"
    TUE: str = "tue"
    WED: str = "wed"
    THU: str = "thu"
    FRI: str = "fri"
    SAT: str = "sat"
    SUN: str = "sun"

    __all__: List[str] = (MON, TUE, WED, THU, FRI, SAT, SUN)

    @classmethod
    def to_int(cls, day):
        """Get the day of week as int. Monday is 0 and Sunday 6."""
        return cls.__all__.index(day)

    @staticmethod
    def from_int(cls, day):
        """Get textual name of given day. Monday is 0 and Sunday 6."""
        return cls.__all__[day]
