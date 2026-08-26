from kiva_cli.core.pipeline_runner import run_pipeline
from kiva_cli.core.pipeline_loader import load_pipeline
import kiva_cli.core.pipeline_runner as runner

p = load_pipeline('.kiva/pipelines/ecosystem-orchestration-pipeline.yaml')

# Monkey-patch to see env
original_run_step = runner._run_step
def debug_run_step(step, pipeline_env=None, dry_run=False, verbose=False):
    if pipeline_env:
        has_output_dir = 'OUTPUT_DIR' in pipeline_env
        print(f'DEBUG: pipeline_env has OUTPUT_DIR: {has_output_dir}')
        if has_output_dir:
            print(f'DEBUG: OUTPUT_DIR = {pipeline_env["OUTPUT_DIR"]}')
    return original_run_step(step, pipeline_env=pipeline_env, dry_run=dry_run, verbose=verbose)

runner._run_step = debug_run_step

import asyncio
async def test():
    result = await runner.run_pipeline(p, dry_run=False, verbose=True)
    return result

asyncio.run(test())