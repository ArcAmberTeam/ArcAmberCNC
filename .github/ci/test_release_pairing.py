"""Exercise the publish workflow's pairing gate with isolated GitHub responses."""

import json
import subprocess
import textwrap
import unittest
from pathlib import Path


class ReleasePairingTests(unittest.TestCase):
    def test_only_traceable_same_version_unavailable_firmware_is_accepted(self):
        workflow = (Path(__file__).parents[1] / "workflows/release.yml").read_text()
        start = workflow.index("            async function verifyMesaRelease() {")
        end = workflow.index("            const paired = await verifyMesaRelease();", start)
        verifier = textwrap.dedent(workflow[start:end])
        fixture = r"""
const crypto = require('node:crypto');
const repo = {owner: 'ArcAmberTeam', repo: 'ArcAmberCNC'};
const mesa = {owner: 'ArcAmberTeam', repo: 'CNC-Mesa'};
const version = '26.10.26.1';
const tag = `v${version}`;
const sha = 'a'.repeat(40);
const mesaSha = 'b'.repeat(40);
const mode = process.argv[1];
const manifest = {
  schema_version: 1, version, tag_name: tag, compatible_app_version: version,
  board: 'zhulong-v2', variant: 'PIN_ZHULONG_V2_34', fpga: 'xc6slx9',
  package: 'tqg144', physical_constraints_verified: false, source_commit: mesaSha,
  firmware: {available: false, asset: null, sha256: null, size: null,
    origin: 'unavailable', verification: {implementation: false, timing: false, board_approved: false}},
  artifacts: Object.fromEntries(['source', 'integration'].map(kind => [kind,
    {asset: `cnc-mesa-${kind}-${version}.tar.gz`, sha256: 'c'.repeat(64), size_bytes: 123}]))
};
if (mode === 'extra-metadata') manifest.description = {future: 'metadata'};
if (mode === 'wrong-version') manifest.compatible_app_version = '26.10.26.2';
if (mode === 'wrong-board') manifest.board = 'other-board';
if (mode === 'wrong-schema') manifest.schema_version = 2;
if (mode === 'wrong-source') manifest.source_commit = 'd'.repeat(40);
if (mode === 'missing-unavailable-claim') delete manifest.firmware.available;
if (mode === 'advertises-bitstream') manifest.firmware.available = true;
if (mode === 'hardware-claim') manifest.firmware.verification.board_approved = true;
const bytes = Buffer.from(JSON.stringify(manifest));
const digest = crypto.createHash('sha256').update(bytes).digest('hex');
const url = `https://github.com/${mesa.owner}/${mesa.repo}/releases/download/${tag}/mesa-release.json`;
const assets = [{id: 101, name: 'mesa-release.json', size: bytes.length,
  state: 'uploaded', digest: `sha256:${digest}`, browser_download_url: url}];
for (const record of Object.values(manifest.artifacts)) {
  assets.push({name: record.asset, state: 'uploaded', size: record.size_bytes,
    digest: `sha256:${record.sha256}`});
}
if (mode === 'bad-manifest-digest') assets[0].digest = `sha256:${'0'.repeat(64)}`;
if (mode === 'bad-archive-digest') assets[1].digest = `sha256:${'0'.repeat(64)}`;
if (mode === 'duplicate-manifest') assets.push({...assets[0], id: 102});
if (mode === 'flash-payload') assets.push({name: 'factory.bit'});
const github = {
  paginate: async () => assets,
  rest: {
    repos: {
      getContent: async () => ({data: {content: Buffer.from(JSON.stringify({
        repository: 'https://github.com/ArcAmberTeam/CNC-Mesa', release: tag,
        commit: mesaSha, manifest_sha256: digest,
        archive: manifest.artifacts.integration.asset,
        sha256: mode === 'wrong-pinned-source' ? '0'.repeat(64) : manifest.artifacts.integration.sha256
      })).toString('base64')}}),
      getReleaseByTag: async () => {
        if (mode === 'missing-release') throw new Error('404');
        return {data: {id: 10, tag_name: tag, draft: false,
          prerelease: mode === 'prerelease', published_at: '2026-10-26T00:00:00Z'}};
      },
      listReleaseAssets: () => {},
      compareCommitsWithBasehead: async () => ({data: {status: mode === 'not-on-main' ? 'diverged' : 'ahead'}})
    },
    git: {getRef: async () => ({data: {object: {type: 'commit', sha: mesaSha}}})}
  }
};
const fetch = async () => ({ok: true, url, body: [bytes]});
"""
        finish = """
verifyMesaRelease().then(result => {
  const evidence = JSON.parse(result.evidence);
  if (!result.bytes.equals(bytes) || evidence.app.source_commit !== sha ||
      evidence.mesa.source_commit !== mesaSha || evidence.mesa.firmware_available !== false)
    throw new Error('Lost paired release provenance');
  console.log(JSON.stringify({accepted: true}));
}).catch(error => console.log(JSON.stringify({accepted: false, reason: error.message})));
"""
        accepted = {"valid", "extra-metadata"}
        rejected = {
            "missing-release", "prerelease", "wrong-version", "wrong-board",
            "wrong-schema", "wrong-source", "missing-unavailable-claim",
            "advertises-bitstream", "hardware-claim", "bad-manifest-digest",
            "bad-archive-digest", "duplicate-manifest", "flash-payload", "not-on-main",
            "wrong-pinned-source",
        }
        for mode in sorted(accepted | rejected):
            with self.subTest(response=mode):
                result = subprocess.run(
                    ["node", "-e", fixture + verifier + finish, mode],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                response = json.loads(result.stdout)
                self.assertEqual(response["accepted"], mode in accepted, response)


if __name__ == "__main__":
    unittest.main()
