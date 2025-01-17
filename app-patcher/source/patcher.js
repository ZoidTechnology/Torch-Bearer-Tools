import { applyPatch, structuredPatch } from 'diff';
import { cp, readdir, readFile, writeFile } from 'fs/promises';
import { join, relative } from 'path';
import { format } from 'prettier';

export async function applyPatches(patches, formatConfig, sourceBasePath, destinationBasePath) {
	await cp(sourceBasePath, destinationBasePath, { recursive: true });

	for (const patch of patches) {
		const sourceFilePath = join(sourceBasePath, patch.path);
		const sourceFile = await readFile(sourceFilePath, 'utf-8');
		const formattedFile = await format(sourceFile, { ...formatConfig, filepath: patch.path });
		const patchedFile = applyPatch(formattedFile, patch);

		if (patchedFile === false) {
			throw new Error('Failed to patch file: ' + patch.path);
		}

		await writeFile(sourceFilePath, formattedFile);
		await writeFile(join(destinationBasePath, patch.path), patchedFile);
	}
}

export async function createPatches(sourceBasePath, destinationBasePath) {
	const entries = await readdir(sourceBasePath, { recursive: true, withFileTypes: true });
	const patches = [];

	for (const entry of entries) {
		if (!entry.isFile()) {
			continue;
		}

		const sourceFilePath = join(entry.parentPath, entry.name);
		const relativeFilePath = relative(sourceBasePath, sourceFilePath);
		const destinationFilePath = join(destinationBasePath, relativeFilePath);

		const sourceFile = await readFile(sourceFilePath);
		const destinationFile = await readFile(destinationFilePath);

		if (sourceFile.equals(destinationFile)) {
			continue;
		}

		const hunks = structuredPatch(
			undefined,
			undefined,
			sourceFile.toString('utf-8'),
			destinationFile.toString('utf-8'),
			undefined,
			undefined,
			{ stripTrailingCr: true }
		).hunks;

		if (hunks.length) {
			patches.push({ path: relativeFilePath.replaceAll('\\', '/'), hunks });
		}
	}

	return patches.sort((first, second) => first.path.localeCompare(second.path));
}
