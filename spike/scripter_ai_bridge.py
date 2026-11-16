# Spike: verifica gli agganci ad AI Diffusion dallo Scripter di Krita.
# Uso: Strumenti > Script > Scripter, apri questo file, premi Esegui (con un documento aperto).
# I passi sono in sequenza con QTimer, per non bloccare la UI: Krita resta usabile.
# Il log va in %APPDATA%\krita\scripter_ai_bridge.log e nei messaggi sul canvas.
#
# Passi:
#   1. Live: attiva il Live, gira la strength su alcuni valori, misura i risultati, ripristina
#   2. Cronologia: scorre i risultati finiti (come farebbe la rotella jog), ripristina la selezione
#   3. Generate: workspace Generation, lancia l'azione ai_diffusion_generate, aspetta il risultato
# Alla fine ripristina workspace e strength originali.

import time
import traceback
from pathlib import Path

from krita import Krita
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

LIVE_STRENGTHS = [0.2, 0.35, 0.5, 0.65, 0.8]
LIVE_STEP_MS = 3000  # tempo per ogni valore di strength in Live
LIVE_WARMUP_TIMEOUT_S = 120  # attesa massima del primo risultato Live (modello a freddo)
JOG_STEP_MS = 800  # tempo per ogni risultato della cronologia
GENERATE_TIMEOUT_S = 120

# Nella cartella dati di Krita: nello Scripter __file__ non è affidabile
LOG_PATH = Path(Krita.instance().getAppDataLocation()) / "scripter_ai_bridge.log"

LOG_PATH.write_text("", encoding="utf-8")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        view = Krita.instance().activeWindow().activeView()
        view.showFloatingMessage(str(msg), QIcon(), 2000, 1)
    except Exception:
        pass


class Spike:
    def __init__(self):
        from ai_diffusion import __version__
        from ai_diffusion.model.jobs import JobKind, JobQueue, JobState
        from ai_diffusion.model.model import Workspace
        from ai_diffusion.model.root import root

        self.JobKind, self.JobQueue, self.JobState, self.Workspace = (
            JobKind, JobQueue, JobState, Workspace,
        )
        log(f"AI Diffusion {__version__}")

        self.model = root.model_for_active_document()
        if self.model is None:
            raise RuntimeError("Nessun documento attivo: apri o crea un documento e riprova")

        m = self.model
        self.orig_workspace = m.workspace
        self.orig_live_strength = m.live.strength
        self.orig_selection = list(m.jobs.selection)
        self.live_results = 0
        self.steps = []
        log(
            f"Stato iniziale: workspace={m.workspace.name} strength={m.strength} "
            f"live.strength={m.live.strength} seed={m.seed} fixed_seed={m.fixed_seed} "
            f"jobs={len(m.jobs)}"
        )

        action = Krita.instance().action("ai_diffusion_generate")
        log(f"Azione ai_diffusion_generate: {'trovata' if action else 'MANCANTE'}")
        self.generate_action = action

    # --- sequenza ---

    def run(self):
        self.steps = [self.live_start, self.live_wait_first]
        for s in LIVE_STRENGTHS:
            self.steps.append(lambda s=s: self.live_set(s))
        self.steps += [self.live_stop, self.jog_start]
        self.next(0)

    def next(self, delay_ms):
        if not self.steps:
            return
        step = self.steps.pop(0)

        def call():
            try:
                step()
            except Exception:
                log("ERRORE:\n" + traceback.format_exc())
                self.restore()

        QTimer.singleShot(delay_ms, call)

    # --- 1. Live ---

    def live_start(self):
        m = self.model
        m.workspace = self.Workspace.live
        m.live.result_available.connect(self.on_live_result)
        m.live.is_active = True
        log(f"Live attivo: workspace={m.workspace.name} is_active={m.live.is_active}")
        self.live_t0 = time.monotonic()
        self.next(500)

    def live_wait_first(self):
        # Il primo risultato può richiedere molto: ComfyUI carica il modello a freddo
        elapsed = time.monotonic() - self.live_t0
        if self.live_results > 0:
            log(f"Primo risultato Live dopo {elapsed:.1f}s (warm-up)")
            self.live_results = 0
            self.next(500)
        elif elapsed > LIVE_WARMUP_TIMEOUT_S:
            log(f"Nessun risultato Live dopo {elapsed:.0f}s, error={self.model.error}")
            self.next(0)
        else:
            self.steps.insert(0, self.live_wait_first)
            self.next(500)

    def on_live_result(self, _image):
        self.live_results += 1
        log(f"  risultato Live #{self.live_results} (strength={self.model.live.strength})")

    def live_set(self, value):
        before = self.live_results
        self.model.live.strength = value
        log(f"live.strength -> {self.model.live.strength} (risultati finora: {before})")
        self.next(LIVE_STEP_MS)

    def live_stop(self):
        m = self.model
        m.live.is_active = False
        m.live.result_available.disconnect(self.on_live_result)
        m.live.strength = self.orig_live_strength
        log(
            f"Live fermo. Risultati ricevuti: {self.live_results} su {len(LIVE_STRENGTHS)} valori. "
            f"live.strength ripristinata a {m.live.strength}"
        )
        self.next(500)

    # --- 2. Cronologia (rotella jog) ---

    def jog_items(self):
        items = []
        for job in self.model.jobs:
            if job.kind is self.JobKind.diffusion and job.state is self.JobState.finished:
                items += [self.JobQueue.Item(job.id, i) for i in range(len(job.results))]
        return items

    def jog_start(self):
        self.model.workspace = self.Workspace.generation
        items = self.jog_items()
        log(f"Cronologia: {len(items)} risultati")
        for item in items:
            self.steps.append(lambda item=item: self.jog_select(item))
        self.steps.append(self.jog_stop)
        self.next(JOG_STEP_MS)

    def jog_select(self, item):
        jobs = self.model.jobs
        if jobs.find(item.job) is None:
            log(f"Job {item.job} sparito, salto")
        else:
            jobs.selection = [item]
            log(f"Selezionato {item.job[:8]}…#{item.image} -> selection={len(jobs.selection)}")
        self.next(JOG_STEP_MS)

    def jog_stop(self):
        jobs = self.model.jobs
        jobs.selection = [i for i in self.orig_selection if jobs.find(i.job) is not None]
        log("Selezione ripristinata")
        self.steps.append(self.generate_start)
        self.next(500)

    # --- 3. Generate ---

    def generate_start(self):
        if self.generate_action is None:
            log("Generate saltato: azione mancante")
            self.restore()
            return
        m = self.model
        m.workspace = self.Workspace.generation
        self.jobs_before = {j.id for j in m.jobs}
        self.generate_t0 = time.monotonic()
        self.generate_action.trigger()
        log(f"Generate lanciato (strength={m.strength})")
        self.steps.append(self.generate_wait)
        self.next(1000)

    def generate_wait(self):
        new = [j for j in self.model.jobs if j.id not in self.jobs_before]
        elapsed = time.monotonic() - self.generate_t0
        done = [j for j in new if j.state is self.JobState.finished]
        if done:
            j = done[0]
            log(f"Generate finito in {elapsed:.1f}s: {len(j.results)} immagini, seed={j.params.seed}")
            self.restore()
        elif elapsed > GENERATE_TIMEOUT_S:
            states = [j.state.name for j in new]
            log(f"Generate timeout dopo {elapsed:.0f}s. Job nuovi: {states}")
            self.restore()
        else:
            self.steps.append(self.generate_wait)
            self.next(1000)

    # --- fine ---

    def restore(self):
        m = self.model
        self.steps = []
        m.live.is_active = False
        m.live.strength = self.orig_live_strength
        m.workspace = self.orig_workspace
        log(f"FINE. Ripristinato workspace={m.workspace.name}. Log: {LOG_PATH}")


try:
    # Riferimento globale: senza, il garbage collector elimina l'oggetto e i timer non partono
    import builtins

    builtins._dial_spike = Spike()
    builtins._dial_spike.run()
except Exception:
    log("ERRORE:\n" + traceback.format_exc())
