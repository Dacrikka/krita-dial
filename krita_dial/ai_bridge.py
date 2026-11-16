"""Hook into the Krita AI Diffusion plugin (ai_diffusion).

Everything used here is AI Diffusion's internal API (tested on 1.53.0), so every access is defensive:
if the plugin is missing or its structure changes, methods log and do nothing instead of raising.
Notes on the API: docs/spike-ai-diffusion.md.

Must be called from the Qt main thread only.
"""

from __future__ import annotations

from types import SimpleNamespace

from krita import Krita

from .log import log

STRENGTH_MIN = 0.01
STRENGTH_MAX = 1.0


class AIBridge:
    def __init__(self):
        self._ai: SimpleNamespace | None | bool = None  # False = import failed
        self._seeds: dict[int, tuple[list[int], int]] = {}  # id(model) -> (seed history, index)

    # --- access ---

    def _modules(self) -> SimpleNamespace | None:
        if self._ai is None:
            try:
                from ai_diffusion import __version__
                from ai_diffusion.model.jobs import JobKind, JobQueue, JobState
                from ai_diffusion.model.root import root

                self._ai = SimpleNamespace(
                    version=__version__, root=root, JobKind=JobKind, JobQueue=JobQueue, JobState=JobState
                )
                log.info(f"AI Diffusion {__version__} found")
            except Exception as e:
                log.warning(f"AI Diffusion not available: {e!r}")
                self._ai = False
        return self._ai or None

    def reset(self):
        """Retry the import on next access (e.g. AI Diffusion enabled after startup)."""
        self._ai = None

    @property
    def available(self) -> bool:
        return self._modules() is not None

    @property
    def version(self) -> str | None:
        ai = self._modules()
        return ai.version if ai else None

    def model(self):
        ai = self._modules()
        if ai is None or Krita.instance().activeDocument() is None:
            return None
        try:
            return ai.root.model_for_active_document()
        except Exception as e:
            log.warning(f"model_for_active_document failed: {e!r}")
            return None

    def workspace(self) -> str | None:
        m = self.model()
        try:
            return m.workspace.name if m else None
        except AttributeError:
            return None

    @staticmethod
    def trigger(action_name: str) -> bool:
        action = Krita.instance().action(action_name)
        if action is None:
            log.warning(f"Krita action '{action_name}' not found")
            return False
        action.trigger()
        return True

    # --- buttons ---

    def generate(self):
        self.trigger("ai_diffusion_generate")

    def cancel(self):
        self.trigger("ai_diffusion_cancel")

    def apply(self):
        m = self.model()
        if m is None:
            return
        if self.workspace() == "live":
            if m.live.result is None:
                log.info("apply: no live result yet")
                return
            m.live.apply_result()
        elif self.workspace() == "generation":
            selection = list(m.jobs.selection)
            if not selection or m.jobs.find(selection[0].job) is None:
                log.info("apply: nothing selected")
                return
            m.apply_generated_result(*selection[0])

    def new_seed(self):
        if m := self.model():
            m.generate_seed()
            self._seeds.pop(id(m), None)  # restart seed history from the new seed

    def toggle_live(self):
        m = self.model()
        if m is None:
            return
        if self.workspace() != "live":
            m.workspace = type(m.workspace)["live"]
            m.live.is_active = True
        else:
            m.live.is_active = not m.live.is_active

    # --- strength ---

    @staticmethod
    def _strength_target(m):
        ws = m.workspace.name
        if ws == "live":
            return m.live
        if ws == "upscaling":
            return m.upscale
        return m

    def strength(self) -> float | None:
        m = self.model()
        return self._strength_target(m).strength if m else None

    def set_strength(self, value: float):
        if m := self.model():
            value = round(min(STRENGTH_MAX, max(STRENGTH_MIN, value)), 2)
            self._strength_target(m).strength = value

    def add_strength(self, delta: float):
        current = self.strength()
        if current is not None:
            self.set_strength(current + delta)

    # --- jog ---

    def _history_items(self, m) -> list:
        ai = self._modules()
        items = []
        for job in m.jobs:
            if job.kind is ai.JobKind.diffusion and job.state is ai.JobState.finished:
                items += [ai.JobQueue.Item(job.id, i) for i in range(len(job.results))]
        return items

    def history_position(self) -> tuple[int, int] | None:
        """(1-based index of the selected result, total), index 0 if nothing selected."""
        m = self.model()
        if m is None:
            return None
        items = self._history_items(m)
        selection = list(m.jobs.selection)
        index = items.index(selection[0]) + 1 if selection and selection[0] in items else 0
        return index, len(items)

    def history_step(self, delta: int):
        """Move the result selection: positive = newer. Nothing selected: start from the newest."""
        m = self.model()
        if m is None:
            return
        items = self._history_items(m)
        if not items:
            return
        selection = list(m.jobs.selection)
        if selection and selection[0] in items:
            index = max(0, min(len(items) - 1, items.index(selection[0]) + delta))
        else:
            index = len(items) - 1
        m.jobs.selection = [items[index]]

    def seed_scroll(self, delta: int):
        """Walk through seeds: forward past the end makes a new seed, backward revisits old ones."""
        m = self.model()
        if m is None:
            return
        seeds, index = self._seeds.get(id(m), ([m.seed], 0))
        if not seeds or seeds[index] != m.seed:  # seed changed elsewhere: restart history from it
            seeds, index = [m.seed], 0
        for _ in range(abs(delta)):
            if delta > 0:
                index += 1
                if index == len(seeds):
                    m.generate_seed()
                    seeds.append(m.seed)
            elif index > 0:
                index -= 1
        m.seed = seeds[index]
        self._seeds[id(m)] = (seeds, index)

    # --- status ---

    def state(self) -> dict:
        m = self.model()
        if m is None:
            return {"available": self.available, "version": self.version}
        try:
            return {
                "available": True,
                "version": self.version,
                "workspace": self.workspace(),
                "strength": self.strength(),
                "seed": m.seed,
                "live_active": m.live.is_active,
                "history": self.history_position(),
            }
        except Exception as e:
            log.warning(f"state failed: {e!r}")
            return {"available": True, "version": self.version, "error": repr(e)}
