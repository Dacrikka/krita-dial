# Spike API Krita AI Diffusion (23/10/2026)

Versione letta: **1.53.0** (`%APPDATA%\krita\pykrita\ai_diffusion\__init__.py`), non 1.52.1 come scritto nell'handoff.
Tutto è API interna: va usato in modo difensivo (try/except, `getattr`, controllo versione).

## Due livelli di aggancio

### 1. Azioni Krita (stabili, consigliate per i tasti)
Registrate in `extension.py` con `window.createAction("ai_diffusion_<nome>")`.
Si invocano senza importare nulla del plugin:

```python
Krita.instance().action("ai_diffusion_generate").trigger()
```

| Azione | Effetto |
|---|---|
| `ai_diffusion_generate` | Genera nel workspace attivo (generation / upscaling / live / animation / custom) |
| `ai_diffusion_apply` | Applica risultato selezionato (generation) o risultato live |
| `ai_diffusion_apply_alternative` | Live: applica come layer |
| `ai_diffusion_cancel` / `_cancel_queued` / `_cancel_all` | Annulla job |
| `ai_diffusion_toggle_preview` | Mostra/nasconde anteprima selezionata |
| `ai_diffusion_switch_workspace_{generation,upscaling,live,graph}` | Cambia workspace |
| `ai_diffusion_toggle_workspace` | Workspace successivo (ciclico) |
| `ai_diffusion_toggle_edit_mode` | Edit mode |
| `ai_diffusion_create_region` | Nuova regione |

Se l'azione non esiste (`action()` ritorna `None`) → AI Diffusion assente → fallback Krita.

### 2. Modello Python (necessario per anello e rotella)
Import: `from ai_diffusion.model.root import root` (il package si chiama `ai_diffusion` in `pykrita`).
Modello del documento attivo: `root.model_for_active_document()` → `DocumentModel | None`.

Le proprietà sono `ObservableProperties` (`model/properties.py`): assegnare un valore emette
`<nome>_changed` e la UI si aggiorna da sola grazie al `bind()` bidirezionale. Nessun accesso ai widget.

| Cosa | Dove | Note |
|---|---|---|
| Strength generation | `model.strength` (float 0.01–1.0) | 1.0 = txt2img, <1.0 = refine |
| Strength live | `model.live.strength` (float, default 0.3) | Cambiarla cambia il `WorkflowInput`: il `LiveScheduler` rigenera da solo |
| Workspace | `model.workspace` (`Workspace` enum: generation=0, upscaling=1, live=2, animation=3, custom=4) | |
| Live on/off | `model.live.is_active = True/False` | Equivale al tasto play del docker |
| Seed | `model.seed`, `model.fixed_seed`, `model.generate_seed()` | Il seed conta solo se `fixed_seed` è True, o sempre in live |
| Strength upscale | `model.upscale.strength` | |
| Cronologia | `model.jobs` (`JobQueue`, iterabile) | Ogni `Job` ha `id`, `kind`, `state`, `results` (lista immagini), `params` |
| Selezione / anteprima | `model.jobs.selection = [JobQueue.Item(job_id, index)]` | Emette `selection_changed`: la lista nel docker si sincronizza e il canvas mostra l'anteprima |
| Applica selezione | `model.apply_generated_result(job_id, index)` | Uguale ad `actions.apply()` |

## Mapping proposto

- **Anello esterno** → `model.live.strength` in Live, `model.strength` in Generation.
  Valore assoluto (l'anello ha 15 posizioni, ±7): centro = valore base, estremi = 0.0x / 1.0. Clamp `[0.01, 1.0]`.
- **Rotella jog** → scorre i risultati: lista piatta di `(job.id, i)` per i job con
  `kind is JobKind.diffusion` e `state is JobState.finished`, poi `jobs.selection = [Item(...)]`.
- **Tasti** → azioni Krita (`generate`, `apply`, nuovo seed = `model.generate_seed()`, toggle live).

## Test nello Scripter (23/10, `spike/scripter_ai_bridge.py`)

- Import di `ai_diffusion`, `root.model_for_active_document()` e azione `ai_diffusion_generate`: funzionano.
- Generate da azione: OK, 8 step, 3.3 s a modello caldo (RTX 5070 Ti, SDXL).
- Live: il primo job a freddo ha richiesto 52 s (caricamento SDXL). Spegnere il Live non annulla il job in corso.
- Il workflow Live usa **4 step**: con la quantizzazione sotto, l'anello produce solo ~4 strength distinte.
- Secondo giro (modello caldo): tutti gli agganci OK. Ogni cambio di `live.strength` genera un job da solo;
  ComfyUI lo esegue in 2.0–2.6 s, risultato visibile ~2.5–3 s dopo il cambio. Scorrere la cronologia con
  `jobs.selection` aggiorna l'anteprima. Generate a caldo: 4.0 s totali.
- Latenza Live di 2–3 s: girando l'anello velocemente si vedono solo alcuni valori intermedi (lo scheduler
  tiene un job in volo). Per il video valutare canvas più piccolo / `resolution_multiplier` più basso.

## Insidie trovate

- La strength reale è quantizzata dagli step: `start_at_step = round(steps * (1 - strength))`
  (`backend/workflow.py: apply_strength`). In live con pochi step (LCM/turbo, ~6–8) molte posizioni
  dell'anello danno lo stesso risultato. Per il video conviene un modello live con più step, o mappare
  l'anello sui soli valori distinti.
- In live, ogni cambio di strength accoda una generazione, ma lo scheduler ne tiene una sola in volo
  (grace period 0.25 s se la generazione media supera 1.5 s). Girare l'anello velocemente è sicuro.
- `apply_generated_result` e `show_preview` fanno `assert` su job id validi: verificare sempre
  `model.jobs.find(id)` prima di usarli.
- Tutto va chiamato dal thread Qt principale: il reader HID deve emettere segnali, non toccare il modello.
- `root.model_for_active_document()` crea un modello se non esiste: chiamarlo solo con un documento aperto.
