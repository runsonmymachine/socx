from dataclasses import dataclass
from socx import UIDMixin
from socx import console


@dataclass
class UIDTest(UIDMixin):
    iteration: int


def test():
    inst_ = UIDTest(0)
    for _ in range(1, 999):
        inst = UIDTest(_)
        console.print(inst)
        assert inst.iteration == inst.uid
        console.print(UIDTest.dref(inst.ref))

    console.print(UIDTest.dref(inst_.ref))
    inst_ = None
    console.print(UIDTest.dref(0))

if __name__ == "__main__":
    test()
