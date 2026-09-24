import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

import { findSignRepresentation, SIGN_PHRASES } from '../src/services/signLanguage.js'

const EXPECTED_PHRASES = [
  'Good morning',
  'Open your book',
  'Pay attention',
  'Any questions?',
  'Thank you',
]

test('maps every MVP phrase to local animation and fallback assets', () => {
  assert.deepEqual(SIGN_PHRASES.map((item) => item.phrase), EXPECTED_PHRASES)
  for (const item of SIGN_PHRASES) {
    assert.match(item.asset, /^\/signs\/[a-z-]+\.svg$/)
    assert.match(item.fallbackAsset, /^\/signs\/[a-z-]+\.svg$/)
    assert.match(item.animationAsset, /^\/signs\/animations\/[a-z-]+\.animation\.svg$/)
    for (const assetPath of [item.asset, item.fallbackAsset, item.animationAsset]) {
      const assetUrl = new URL(`../public${assetPath}`, import.meta.url)
      assert.equal(existsSync(fileURLToPath(assetUrl)), true)
    }
    assert.equal(findSignRepresentation(item.phrase).id, item.id)
  }
})

test('normalizes case, whitespace, and punctuation only', () => {
  assert.equal(findSignRepresentation('  GOOD   MORNING! ').id, 'good-morning')
  assert.equal(findSignRepresentation('any questions').phrase, 'Any questions?')
})

test('does not represent unsupported or longer unrestricted sentences', () => {
  assert.equal(findSignRepresentation('Welcome to the class'), null)
  assert.equal(findSignRepresentation('Please open your books now'), null)
  assert.equal(findSignRepresentation('Good morning everyone'), null)
  assert.equal(findSignRepresentation(null), null)
})
