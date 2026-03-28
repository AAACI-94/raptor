#!/usr/bin/env python3
"""Architectural lint for RAPTOR. Run: python scripts/arch_lint.py"""
import ast, os, re, sys

issues = []

for root, dirs, files in os.walk('app'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'): continue
        path = os.path.join(root, f)
        content = open(path).read()

        for i, line in enumerate(content.split('\n'), 1):
            stripped = line.strip()
            # Bare except
            if stripped == 'except Exception:' or stripped == 'except:':
                issues.append(f'{path}:{i} bare except without as e')

        # Missing return types on router functions
        if 'routers/' in path:
            for i, line in enumerate(content.split('\n'), 1):
                if re.match(r'(async )?def [a-z].*\):$', line.strip()):
                    if ' -> ' not in line and 'websocket' not in line.lower():
                        issues.append(f'{path}:{i} missing return type')

        # Anthropic SDK imports
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'anthropic':
                            issues.append(f'{path} imports anthropic SDK')
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] == 'anthropic':
                        issues.append(f'{path} from anthropic import')
        except:
            pass

if issues:
    print(f'ARCH LINT FAILED: {len(issues)} issues')
    for i in issues:
        print(f'  {i}')
    sys.exit(1)
else:
    print('ARCH LINT PASSED: 0 issues')
    sys.exit(0)
