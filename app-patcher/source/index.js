import { spawnSync } from 'child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'fs';
import { join } from 'path';
import { applyPatches, createPatches } from './patcher.js';

const BASE_PATH = join(import.meta.dirname, '..');

const DATA_PATH = join(BASE_PATH, 'data');
const FORMAT_CONFIG_PATH = join(BASE_PATH, '.prettierrc');
const PATCHES_PATH = join(BASE_PATH, 'patches.json');
const SOURCE_APP_PATH = join(BASE_PATH, 'flameeye.apk');
const TOOLS_PATH = join(BASE_PATH, 'tools');

const APKSIGNER_PATH = join(TOOLS_PATH, 'apksigner.jar');
const APKTOOL_PATH = join(TOOLS_PATH, 'apktool.jar');

const DISASSEMBLED_PATH = join(DATA_PATH, 'disassembled');
const KEYSTORE_PATH = join(DATA_PATH, 'keystore.jks');
const PATCHED_APP_PATH = join(DATA_PATH, 'flameeye-patched.apk');
const PATCHED_PATH = join(DATA_PATH, 'patched');
const SIGNED_APP_PATH = join(DATA_PATH, 'flameeye-signed.apk');

const KEYSTORE_PASSWORD = 'hunter2';
const KEY_ALIAS = 'key';

function executeCommand(command, ...args) {
	const output = spawnSync(
		'"' + command + '"',
		args.map((arg) => '"' + arg + '"'),
		{ encoding: 'utf-8', shell: true }
	);

	if (output.status) {
		throw new Error('Command returned non-zero exit code: ' + output.status);
	}

	return output;
}

function executeJava(...args) {
	return executeCommand('java', ...args);
}

function executeJar(...args) {
	return executeJava('-jar', ...args);
}

function exit(error) {
	console.error(error);
	process.exit(1);
}

if (!existsSync(DATA_PATH)) {
	try {
		console.log('Creating data directory...');
		mkdirSync(DATA_PATH);

		console.log('Disassembling app...');
		executeJar(APKTOOL_PATH, 'd', SOURCE_APP_PATH, '-o', DISASSEMBLED_PATH, '-s');

		console.log('Loading patches...');
		const patches = JSON.parse(readFileSync(PATCHES_PATH));

		console.log('Loading formatter configuration...');
		const formatConfig = JSON.parse(readFileSync(FORMAT_CONFIG_PATH));

		console.log('Applying patches...');
		await applyPatches(patches, formatConfig, DISASSEMBLED_PATH, PATCHED_PATH);

		console.log('Locating Java...');
		const output = executeJava('-XshowSettings:properties', '-version');
		const javaHome = output.stderr.match(/java\.home = (.*)/)[1];

		console.log('Generating signing keys...');
		executeCommand(
			join(javaHome, 'bin', 'keytool'),
			'-genkeypair',
			'-alias',
			KEY_ALIAS,
			'-dname',
			'CN=Torch Bearer Tools',
			'-keyalg',
			'RSA',
			'-keysize',
			2048,
			'-keystore',
			KEYSTORE_PATH,
			'-storepass',
			KEYSTORE_PASSWORD,
			'-validity',
			365 * 10
		);
	} catch (error) {
		rmSync(DATA_PATH, { recursive: true });
		exit(error);
	}
}

const action = process.argv[2];

try {
	if (action === 'assemble') {
		console.log('Assembling app...');
		executeJar(APKTOOL_PATH, 'b', PATCHED_PATH, '-o', PATCHED_APP_PATH);

		console.log('Signing app...');
		executeJar(
			APKSIGNER_PATH,
			'sign',
			'--ks',
			KEYSTORE_PATH,
			'--ks-key-alias',
			KEY_ALIAS,
			'--ks-pass',
			'pass:' + KEYSTORE_PASSWORD,
			'--out',
			SIGNED_APP_PATH,
			'--v4-signing-enabled',
			false,
			PATCHED_APP_PATH
		);
	} else if (action === 'create-patches') {
		console.log('Creating patches...');
		const patches = await createPatches(DISASSEMBLED_PATH, PATCHED_PATH);

		console.log('Saving patches...');
		writeFileSync(PATCHES_PATH, JSON.stringify(patches, null, '\t'));
	} else {
		exit('Unknown action: ' + action);
	}
} catch (error) {
	exit(error);
}

console.log('Done.');
