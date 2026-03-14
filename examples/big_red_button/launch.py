"""Launch module — the code omniray will trace."""

import time

from omniray import trace


class MissileLauncher:
    def authenticate(self, key: str) -> bool:
        time.sleep(0.05)
        return key == "LAUNCH-CODE-7740"

    def arm_warhead(self) -> str:
        time.sleep(0.12)
        return "ARMED"

    @trace(log_input=True)
    def select_target(self, coordinates: str) -> str:
        time.sleep(0.03)
        return f"TARGET LOCKED: {coordinates}"

    @trace(log_output=True)
    def fire(self) -> dict:
        time.sleep(0.2)
        return {"status": "BOOM!", "impact": True, "debris_radius_km": 4.2}


class BigRedButton:
    def __init__(self) -> None:
        self.launcher = MissileLauncher()

    def press(self) -> dict:
        self.pre_launch_check()
        return self.launch_sequence()

    def pre_launch_check(self) -> None:
        self.launcher.authenticate("LAUNCH-CODE-7740")

    def launch_sequence(self) -> dict:
        self.launcher.arm_warhead()
        self.launcher.select_target("51.5074° N, 0.1278° W")
        return self.launcher.fire()
