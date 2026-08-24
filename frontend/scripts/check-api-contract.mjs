/* global console, process */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import openapiTS from 'openapi-typescript';
import prettier from 'prettier';
import ts from 'typescript';

const root = resolve(import.meta.dirname, '..');
const python = resolve(root, '../backend/.venv/bin/python');
const code =
  'import json; from app.main import app; print(json.dumps(app.openapi(), sort_keys=True, indent=2))';
const live = `${execFileSync(python, ['-c', code], { cwd: resolve(root, '../backend'), encoding: 'utf8' }).trim()}\n`;
const snapshotPath = resolve(root, 'src/types/openapi.json');
let snapshot;
try {
  snapshot = readFileSync(snapshotPath, 'utf8');
} catch {
  console.error('Missing generated OpenAPI snapshot. Run npm run api:generate.');
  process.exit(1);
}
if (live !== snapshot) {
  console.error(
    'Phase 6 OpenAPI drift detected. Run npm run api:generate and review the typed client.',
  );
  process.exit(1);
}
const schema = JSON.parse(snapshot);
const generatedPath = resolve(root, 'src/types/generated.ts');
let generated;
try {
  generated = readFileSync(generatedPath, 'utf8');
} catch {
  console.error('Missing generated TypeScript contract. Run npm run api:generate.');
  process.exit(1);
}
const generatedAst = await openapiTS(schema, {
  alphabetize: true,
  exportType: 'named',
});
const sourceFile = ts.createSourceFile(
  'generated.ts',
  '',
  ts.ScriptTarget.Latest,
  false,
  ts.ScriptKind.TS,
);
const printer = ts.createPrinter({ newLine: ts.NewLineKind.LineFeed });
const expectedBody = generatedAst
  .map((node) => printer.printNode(ts.EmitHint.Unspecified, node, sourceFile))
  .join('\n\n');
const expected = await prettier.format(
  `/** Generated from src/types/openapi.json. Do not edit manually. */\n${expectedBody}`,
  {
    filepath: generatedPath,
    printWidth: 88,
    singleQuote: true,
    trailingComma: 'all',
  },
);
if (generated !== expected) {
  console.error('Generated TypeScript contract is stale. Run npm run api:generate.');
  process.exit(1);
}
const consumedOperations = [
  ['/api/v1/batches', 'post', 'createBatch'],
  ['/api/v1/batches/{batch_id}', 'get', 'getBatch'],
  ['/api/v1/batches/{batch_id}/sources/{source_kind}', 'put', 'putBatchSource'],
  ['/api/v1/batches/{batch_id}/reconciliation-runs', 'post', 'runReconciliation'],
  ['/api/v1/batches/{batch_id}/result', 'get', 'getReconciliationResult'],
  ['/api/v1/batches/{batch_id}/close-readiness', 'get', 'getCloseReadiness'],
  ['/api/v1/batches/{batch_id}/settlements', 'get', 'listSettlements'],
  ['/api/v1/batches/{batch_id}/settlements/{settlement_id}', 'get', 'getSettlement'],
  ['/api/v1/batches/{batch_id}/exceptions', 'get', 'listExceptions'],
  ['/api/v1/batches/{batch_id}/audit-events', 'get', 'listAuditEvents'],
  [
    '/api/v1/batches/{batch_id}/exports/reconciliation-result',
    'get',
    'exportReconciliationResult',
  ],
  ['/api/v1/batches/{batch_id}/exports/exceptions', 'get', 'exportExceptions'],
  ['/api/v1/batches/{batch_id}/exports/audit-events', 'get', 'exportAuditEvents'],
  [
    '/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations',
    'post',
    'runInvestigation',
  ],
  [
    '/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations',
    'get',
    'listSettlementInvestigations',
  ],
  ['/api/v1/batches/{batch_id}/investigations', 'get', 'listBatchInvestigations'],
  [
    '/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations/eligibility',
    'get',
    'getInvestigationEligibility',
  ],
  [
    '/api/v1/batches/{batch_id}/settlements/{settlement_id}/effective-review',
    'get',
    'getEffectiveReview',
  ],
  ['/api/v1/batches/{batch_id}/effective-review', 'get', 'listEffectiveReviews'],
  ['/api/v1/batches/{batch_id}/exports/investigations', 'get', 'exportInvestigations'],
];
for (const [path, method, operationId] of consumedOperations) {
  const operation = schema.paths?.[path]?.[method];
  if (!operation || operation.operationId !== operationId) {
    console.error(
      `Consumed API operation missing or changed: ${method.toUpperCase()} ${path} (${operationId})`,
    );
    process.exit(1);
  }
  if (!operation.responses?.['200'] && !operation.responses?.['201']) {
    console.error(`Consumed API operation has no success response: ${operationId}`);
    process.exit(1);
  }
  if (
    !Object.values(operation.responses).some((response) =>
      response?.content?.['application/json']?.schema?.$ref?.endsWith('/ErrorEnvelope'),
    )
  ) {
    console.error(
      `Consumed API operation has no ErrorEnvelope response: ${operationId}`,
    );
    process.exit(1);
  }
}
const consumedSchemas = new Set();
const visitSchema = (name) => {
  if (consumedSchemas.has(name)) return;
  consumedSchemas.add(name);
  collectSchemaRefs(schema.components?.schemas?.[name]);
};
const collectSchemaRefs = (value) => {
  if (!value || typeof value !== 'object') return;
  if ('$ref' in value && typeof value.$ref === 'string') {
    const match = value.$ref.match(/^#\/components\/schemas\/([^/]+)$/);
    if (match) visitSchema(match[1]);
  }
  for (const child of Object.values(value)) collectSchemaRefs(child);
};
for (const [path, method] of consumedOperations)
  collectSchemaRefs(schema.paths[path][method]);
const apiTypes = readFileSync(resolve(root, 'src/types/api.ts'), 'utf8');
for (const [, name] of apiTypes.matchAll(/components\["schemas"\]\["([^"]+)"\]/g))
  visitSchema(name);
for (const name of consumedSchemas)
  if (!schema.components?.schemas?.[name]) {
    console.error(`Consumed API schema missing: ${name}`);
    process.exit(1);
  }
console.log(
  `API contract OK: ${consumedOperations.length} operations and ${consumedSchemas.size} consumed schemas checked`,
);
