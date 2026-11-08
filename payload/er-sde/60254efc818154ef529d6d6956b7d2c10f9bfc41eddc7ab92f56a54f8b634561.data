# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import sd_samplers, sd_samplers_common
from modules.sd_samplers_kdiffusion import KDiffusionSampler
from er_sde_comfy.core import sample_er_sde
from er_sde_comfy import core, validation
from modules import script_callbacks
import torch

NAME = 'er sde (comfyui)'


class ComfyERSDESampler(KDiffusionSampler):
    def __init__(self, sd_model):
        super().__init__(self.sample_comfy, sd_model)

    def sample_comfy(self, model, x, sigmas, extra_args=None, callback=None, disable=None):
        # A Comfy KSampler seeds ONE device generator for the whole latent batch.
        # Forge batches may list different per-image seeds; the first seeds this batch's SDE.
        index = self.p.iteration * self.p.batch_size
        seed = int(self.p.all_seeds[index])
        args = dict(extra_args or {})
        args['seed'] = seed

        class ModelAdapter:
            inner_model = model.inner_model

            def __call__(self, latent, sigma, **kwargs):
                kwargs.pop('seed', None)
                return model(latent, sigma, **kwargs)

        folder = validation.directory()
        noise_sampler = None
        if folder is not None:
            torch.save(sigmas.detach().cpu(), folder / 'sigmas.pt')
            draw = core.default_noise_sampler(x, seed)
            draws = [0]
            def noise_sampler(a, b):
                noise = draw(a, b)
                if draws[0] in (0, 1, 15, 30):
                    torch.save(noise.detach().cpu(), folder / f'noise-{draws[0]:02}.pt')
                draws[0] += 1
                return noise
        result = sample_er_sde(ModelAdapter(), x, sigmas, extra_args=args,
                               callback=callback, disable=disable, noise_sampler=noise_sampler)
        if folder is not None:
            torch.save(result.detach().cpu(), folder / 'final.pt')
        return result


sd_samplers.add_sampler(sd_samplers_common.SamplerData(
    NAME, lambda model: ComfyERSDESampler(model), ['er_sde_comfyui'], {}))
print('[ER SDE ComfyUI] Registered: ' + NAME)
script_callbacks.on_cfg_denoiser(validation.before)
script_callbacks.on_cfg_after_cfg(validation.after)
