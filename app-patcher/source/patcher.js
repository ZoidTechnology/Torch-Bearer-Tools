import { applyPatch, structuredPatch } from 'diff';
import { cp, readdir, readFile, writeFile } from 'fs/promises';
import { extname, join, relative } from 'path';
import { format, getSupportInfo } from 'prettier';

export async function applyPatches(patches, formatConfig, sourceBasePath, destinationBasePath) {
	await cp(sourceBasePath, destinationBasePath, { recursive: true });

	for (const patch of patches) {
		let data;

		if (Array.isArray(patch.data)) {
			const sourceFilePath = join(sourceBasePath, patch.path);
			const sourceFile = await readFile(sourceFilePath, 'utf-8');
			const formattedFile = await format(sourceFile, { ...formatConfig, filepath: patch.path });
			data = applyPatch(formattedFile, { hunks: patch.data });

			if (data === false) {
				throw new Error('Failed to patch file: ' + patch.path);
			}

			await writeFile(sourceFilePath, formattedFile);
		} else {
			data = Buffer.from(patch.data, 'base64');
		}

		await writeFile(join(destinationBasePath, patch.path), data);
	}
}

export async function createPatches(sourceBasePath, destinationBasePath) {
	const entries = await readdir(sourceBasePath, { recursive: true, withFileTypes: true });
	const textFileExtensions = (await getSupportInfo()).languages.map((language) => language.extensions).flat();
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

		let data;

		if (textFileExtensions.includes(extname(relativeFilePath))) {
			data = structuredPatch(
				undefined,
				undefined,
				sourceFile.toString('utf-8'),
				destinationFile.toString('utf-8'),
				undefined,
				undefined,
				{ stripTrailingCr: true }
			).hunks;

			if (data.length === 0) {
				continue;
			}
		} else {
			data = destinationFile.toString('base64');
		}

		patches.push({ path: relativeFilePath.replaceAll('\\', '/'), data });
	}

	return patches.sort((first, second) => first.path.localeCompare(second.path));
}
