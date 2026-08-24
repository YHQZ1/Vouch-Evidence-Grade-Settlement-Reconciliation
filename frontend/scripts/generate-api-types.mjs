/* global console */
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import openapiTS from 'openapi-typescript';
import prettier from 'prettier';
import ts from 'typescript';

const root = resolve(import.meta.dirname, '..');
const python = resolve(root, '../backend/.venv/bin/python');
const code =
  'import json; from app.main import app; print(json.dumps(app.openapi(), sort_keys=True, indent=2))';
const schema = execFileSync(python, ['-c', code], {
  cwd: resolve(root, '../backend'),
  encoding: 'utf8',
});
const destination = resolve(root, 'src/types/openapi.json');
mkdirSync(dirname(destination), { recursive: true });
writeFileSync(destination, `${schema.trim()}\n`);
const generatedAst = await openapiTS(JSON.parse(schema), {
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
const generated = generatedAst
  .map((node) => printer.printNode(ts.EmitHint.Unspecified, node, sourceFile))
  .join('\n\n');
const typesDestination = resolve(root, 'src/types/generated.ts');
writeFileSync(
  typesDestination,
  await prettier.format(
    `/** Generated from src/types/openapi.json. Do not edit manually. */\n${generated}`,
    {
      filepath: typesDestination,
      printWidth: 88,
      singleQuote: true,
      trailingComma: 'all',
    },
  ),
);
console.log(`Wrote ${destination}`);
console.log(`Wrote ${typesDestination}`);
