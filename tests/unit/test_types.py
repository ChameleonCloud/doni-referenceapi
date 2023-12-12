from pydantic import BaseModel

from doni_referenceapi.common.types.si_frequency import SiFrequency


class MyModel(BaseModel):
    freq: SiFrequency


def test_si_frequency():
    assert MyModel(freq="543 MHz").freq == 543 * 10**6
    assert MyModel(freq="3.6 gHZ").freq == 3.6 * 10**9

