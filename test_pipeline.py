import os
os.environ['KIVA_PIPELINES_DIR'] = '.kiva/pipelines'
from kiva_cli.core.pipeline_loader import load_pipeline
p = load_pipeline('.kiva/pipelines/build.yaml')
print(f'Pipeline: {p.name}')
print(f'Steps: {len(p.steps)}')
print(f'Parallel groups: {p.parallel_groups}')
for s in p.steps:
    print(f'  {s.name}: depends_on={s.depends_on}, on_failure={s.on_failure}, when="{s.when}"')