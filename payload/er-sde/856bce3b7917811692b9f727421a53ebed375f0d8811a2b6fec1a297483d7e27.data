"""Opt-in local validation capture. No files are written without validation.json."""
import json
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[1]
_current_step = None


def directory():
    control = ROOT / 'validation.json'
    if not control.is_file():
        return None
    config = json.loads(control.read_text(encoding='utf-8'))
    if not config.get('enabled'):
        return None
    folder = Path(config['directory'])
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def before(params):
    global _current_step
    folder = directory()
    if folder is None:
        return
    p = params.denoiser.p
    phase = 'hires' if p.is_hr_pass else 'base'
    # UI sampling_step is updated AFTER the denoiser and lags one call.
    step = params.denoiser.step
    _current_step = (phase, step)
    if step in (0, 1, 15, 31):
        torch.save({'x': params.x.detach().cpu(), 'sigma': params.sigma.detach().cpu()}, folder / f'{phase}-step-{step:02}.pt')
    if step == 0:
        predictor = params.denoiser.inner_model.predictor
        engine = p.sd_model
        network = engine.forge_objects.unet.model.diffusion_model
        (folder / f'{phase}-settings.json').write_text(json.dumps({
            'sampler': p.sampler_name, 'seed': p.all_seeds, 'steps': p.steps,
            'cfg': p.cfg_scale, 'shift': getattr(predictor, 'shift', None),
            'prediction_type': predictor.prediction_type,
            'latent_dtype': str(params.x.dtype), 'sigma_dtype': str(params.sigma.dtype),
            'model_storage_dtype': str(getattr(network, 'storage_dtype', next(network.parameters()).dtype)),
            'model_computation_dtype': str(getattr(network, 'computation_dtype', None)),
            'torch': torch.__version__, 'cuda': torch.version.cuda,
        }, indent=2), encoding='utf-8')


def after(params):
    folder = directory()
    if folder is not None and _current_step is not None:
        phase, step = _current_step
        if step in (0, 1, 15, 31):
            prefix = 'hires-' if phase == 'hires' else ''
            torch.save(params.x.detach().cpu(), folder / f'{prefix}denoised-{step:02}.pt')
