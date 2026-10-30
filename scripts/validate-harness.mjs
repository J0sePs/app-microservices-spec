#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SUBSYSTEMS = ['Instructions', 'State', 'Verification', 'Scope', 'Lifecycle'];

const checks = [];
let failures = 0;

function absolute(relativePath) {
  return join(ROOT, relativePath);
}

function read(relativePath) {
  const path = absolute(relativePath);
  if (!existsSync(path)) {
    throw new Error(`missing ${relativePath}`);
  }
  return readFileSync(path, 'utf8');
}

function requireText(relativePath, minLength = 1) {
  const text = read(relativePath);
  if (text.trim().length < minLength) {
    throw new Error(`${relativePath} is empty or too short`);
  }
  return text;
}

function requireExecutable(relativePath) {
  const path = absolute(relativePath);
  if (!existsSync(path)) {
    throw new Error(`missing ${relativePath}`);
  }
  if (process.platform !== 'win32' && (statSync(path).mode & 0o111) === 0) {
    throw new Error(`${relativePath} is not executable`);
  }
  return relativePath;
}

function expectIncludes(text, needles, label) {
  const missing = needles.filter((needle) => !text.includes(needle));
  if (missing.length > 0) {
    throw new Error(`${label} is missing: ${missing.join(', ')}`);
  }
}

function check(subsystem, label, fn) {
  try {
    const detail = fn();
    checks.push({ subsystem, label, status: 'PASS', detail: detail || '' });
  } catch (error) {
    failures += 1;
    checks.push({ subsystem, label, status: 'FAIL', detail: error.message });
  }
}

function loadFeatureList() {
  const raw = requireText('feature_list.json', 2);
  let data;

  try {
    data = JSON.parse(raw);
  } catch (error) {
    throw new Error(`invalid JSON: ${error.message}`);
  }

  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('expected a JSON object');
  }

  return data;
}

function validateFeatureList(data) {
  if (data.schema_version !== 1) {
    throw new Error('schema_version must be 1');
  }

  if (typeof data.project !== 'string' || data.project.trim() === '') {
    throw new Error('project must be a non-empty string');
  }

  if (!data.rules || typeof data.rules !== 'object') {
    throw new Error('rules must be an object');
  }

  for (const rule of ['single_active_feature', 'passing_requires_evidence', 'do_not_skip_verification']) {
    if (data.rules[rule] !== true) {
      throw new Error(`rules.${rule} must be true`);
    }
  }

  if (!data.status_legend || typeof data.status_legend !== 'object') {
    throw new Error('status_legend must be an object');
  }

  const allowedStatuses = new Set(Object.keys(data.status_legend));
  if (!Array.isArray(data.features)) {
    throw new Error('features must be an array');
  }
  if (data.features.length === 0) {
    throw new Error('features must contain at least one entry');
  }

  const ids = new Set();
  let inProgress = 0;

  for (const [index, feature] of data.features.entries()) {
    const where = `features[${index}]`;

    if (!feature || typeof feature !== 'object' || Array.isArray(feature)) {
      throw new Error(`${where} must be an object`);
    }

    for (const field of ['id', 'title', 'area', 'user_visible_behavior', 'status']) {
      if (typeof feature[field] !== 'string' || feature[field].trim() === '') {
        throw new Error(`${where}.${field} must be a non-empty string`);
      }
    }

    if (ids.has(feature.id)) {
      throw new Error(`duplicate feature id: ${feature.id}`);
    }
    ids.add(feature.id);

    if (typeof feature.priority !== 'number' || !Number.isFinite(feature.priority)) {
      throw new Error(`${where}.priority must be a number`);
    }

    if (!allowedStatuses.has(feature.status)) {
      throw new Error(`${where}.status "${feature.status}" is not in status_legend`);
    }

    if (feature.change !== null && typeof feature.change !== 'string') {
      throw new Error(`${where}.change must be a string or null`);
    }

    if (!Array.isArray(feature.verification) || feature.verification.length === 0) {
      throw new Error(`${where}.verification must contain at least one step`);
    }

    if (!Array.isArray(feature.evidence)) {
      throw new Error(`${where}.evidence must be an array`);
    }

    if (typeof feature.notes !== 'string') {
      throw new Error(`${where}.notes must be a string`);
    }

    if (feature.status === 'in_progress') {
      inProgress += 1;
      if (typeof feature.change !== 'string' || feature.change.trim() === '') {
        throw new Error(`${where} is in_progress but has no change name`);
      }
    }

    if (feature.status === 'passing' && feature.evidence.length === 0) {
      throw new Error(`${where} is passing but has no evidence`);
    }
  }

  if (inProgress > 1) {
    throw new Error(`found ${inProgress} in_progress features; only one is allowed`);
  }

  return `${data.features.length} feature(s), ${inProgress} in progress`;
}

function activeChangeNames() {
  const changesDir = absolute('openspec/changes');
  if (!existsSync(changesDir)) {
    throw new Error('missing openspec/changes/');
  }

  return readdirSync(changesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name !== 'archive' && !entry.name.startsWith('.'))
    .map((entry) => entry.name)
    .sort();
}

check('Instructions', 'AGENTS.md routes startup, scope, done, and handoff', () => {
  const text = requireText('AGENTS.md', 400);
  expectIncludes(
    text,
    [
      '## Startup',
      '## Select work',
      '## Definition of done',
      '## End of session',
      'docs/harness.md',
      'docs/workflow.md',
      'feature_list.json',
      'progress.md',
      './init.sh',
    ],
    'AGENTS.md',
  );
  return 'startup, scope, done, and handoff rules present';
});

check('Instructions', 'OpenSpec config declares the spec-driven workflow', () => {
  const text = requireText('openspec/config.yaml', 50);
  expectIncludes(text, ['schema: spec-driven', 'context:', 'rules:'], 'openspec/config.yaml');
  return 'spec-driven schema, project context, and artifact rules present';
});

check('Instructions', 'OpenCode OpenSpec entry points are installed', () => {
  if (!existsSync(absolute('.opencode'))) {
    return 'skipped (no .opencode directory)';
  }
  for (const command of ['opsx-propose.md', 'opsx-apply.md', 'opsx-verify.md', 'opsx-archive.md']) {
    requireText(join('.opencode/commands', command), 10);
  }
  for (const skill of ['openspec-propose/SKILL.md', 'openspec-apply-change/SKILL.md']) {
    requireText(join('.opencode/skills', skill), 10);
  }
  return 'propose, apply, verify, and archive entry points present';
});

check('State', 'feature_list.json is valid and coherent', () => {
  return validateFeatureList(loadFeatureList());
});

check('State', 'progress.md records verified state and sessions', () => {
  const text = requireText('progress.md', 200);
  expectIncludes(
    text,
    ['## Current Verified State', '## Session Log', '### Session', 'Next best step'],
    'progress.md',
  );
  return 'current state, session log, and next step present';
});

check('State', 'OpenSpec roots exist', () => {
  for (const path of ['openspec/specs', 'openspec/changes', 'openspec/changes/archive']) {
    if (!existsSync(absolute(path))) {
      throw new Error(`missing ${path}/`);
    }
  }
  return 'specs/, changes/, and changes/archive/ present';
});

check('Verification', 'init.sh is executable', () => {
  return requireExecutable('init.sh');
});

check('Verification', 'scripts/verify.sh is executable', () => {
  return requireExecutable('scripts/verify.sh');
});

check('Verification', 'verification gate runs the harness and OpenSpec checks', () => {
  const text = requireText('scripts/verify.sh', 200);
  expectIncludes(text, ['openspec validate', 'validate-harness.mjs'], 'scripts/verify.sh');
  return 'harness validator and OpenSpec validation are wired in';
});

check('Verification', 'CI runs the same gate', () => {
  const text = requireText('.github/workflows/verify.yml', 100);
  expectIncludes(text, ['./init.sh'], '.github/workflows/verify.yml');
  return 'CI executes ./init.sh';
});

check('Scope', 'single-feature rule is enabled', () => {
  const data = loadFeatureList();
  if (!data.rules || data.rules.single_active_feature !== true) {
    throw new Error('rules.single_active_feature must be true');
  }
  return 'rules.single_active_feature is true';
});

check('Scope', 'active feature is backed by an active OpenSpec change', () => {
  const data = loadFeatureList();
  const active = data.features.filter((feature) => feature.status === 'in_progress');

  if (active.length === 0) {
    return 'no active feature';
  }

  const feature = active[0];
  if (typeof feature.change !== 'string' || feature.change.trim() === '') {
    throw new Error(`${feature.id} is in_progress but has no change name`);
  }

  const changeDir = absolute(join('openspec/changes', feature.change));

  if (!existsSync(changeDir)) {
    throw new Error(`${feature.id} points to missing openspec/changes/${feature.change}`);
  }

  if (!existsSync(join(changeDir, 'tasks.md'))) {
    throw new Error(`openspec/changes/${feature.change}/tasks.md is missing`);
  }

  return `${feature.id} -> ${feature.change}`;
});

check('Scope', 'at most one OpenSpec change is active', () => {
  const active = activeChangeNames();
  if (active.length > 1) {
    throw new Error(`found ${active.length} active changes: ${active.join(', ')}`);
  }
  return active.length === 0 ? 'no active change' : `active change: ${active[0]}`;
});

check('Lifecycle', 'session-handoff.md covers the next session', () => {
  const text = requireText('session-handoff.md', 150);
  expectIncludes(
    text,
    ['## Verified Now', '## Changed This Session', '## Broken Or Unverified', '## Next Best Step', '## Commands'],
    'session-handoff.md',
  );
  return 'verified, changed, unverified, next, and commands sections present';
});

check('Lifecycle', 'end-of-session routine is documented', () => {
  const text = requireText('AGENTS.md', 400);
  expectIncludes(
    text,
    ['## End of session', 'Update `progress.md`', 'Update `feature_list.json`', 'Commit'],
    'AGENTS.md',
  );
  return 'state update, verification, and commit steps present';
});

check('Lifecycle', 'repository is restartable from a clean checkout', () => {
  const text = requireText('init.sh', 200);
  expectIncludes(text, ['scripts/verify.sh'], 'init.sh');
  return 'init.sh delegates to the verification gate';
});

const bySubsystem = new Map(SUBSYSTEMS.map((subsystem) => [subsystem, []]));
for (const item of checks) {
  bySubsystem.get(item.subsystem).push(item);
}

console.log('Harness validation');
console.log('==================');
console.log('');

for (const subsystem of SUBSYSTEMS) {
  const items = bySubsystem.get(subsystem);
  const passed = items.every((item) => item.status === 'PASS');
  console.log(`${subsystem}: ${passed ? 'PASS' : 'FAIL'}`);
  for (const item of items) {
    const detail = item.detail ? ` — ${item.detail}` : '';
    console.log(`  ${item.status}  ${item.label}${detail}`);
  }
  console.log('');
}

const subsystemsPassed = SUBSYSTEMS.filter((subsystem) =>
  bySubsystem.get(subsystem).every((item) => item.status === 'PASS'),
).length;
const checksPassed = checks.filter((item) => item.status === 'PASS').length;

console.log(
  `Result: ${subsystemsPassed}/${SUBSYSTEMS.length} subsystems passed, ${checksPassed}/${checks.length} checks passed.`,
);

if (failures > 0) {
  console.log('');
  console.log('Failed checks:');
  for (const item of checks.filter((entry) => entry.status === 'FAIL')) {
    console.log(`  - ${item.subsystem}: ${item.label} (${item.detail})`);
  }
  process.exitCode = 1;
}
