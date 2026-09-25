import assert from 'node:assert/strict'
import test from 'node:test'

import { buildSimplifiedLecture, simplifyText } from '../src/services/simplifiedLanguage.js'

test('simplifies everyday phrasing without changing protected technical terms', () => {
  const result = simplifyText(
    'In order to utilize a neural network, we subsequently employ gradient descent.',
    ['neural network', 'gradient descent'],
  )

  assert.equal(result, 'To use a neural network, we then employ gradient descent.')
})

test('uses structured key points for a simpler lecture while retaining terms', () => {
  const content = buildSimplifiedLecture(
    [{ text: 'A neural network learns patterns from labelled training data.' }],
    {
      clean_text: 'A neural network learns patterns from labelled training data.',
      key_points: ['A neural network learns patterns from training data.'],
      technical_terms: ['neural network'],
      concepts: ['training data'],
    },
  )

  assert.equal(content.hasContent, true)
  assert.equal(content.text, 'A neural network learns patterns from labelled training data.')
  assert.deepEqual(content.keyPoints, ['A neural network learns patterns from training data.'])
  assert.deepEqual(content.technicalTerms, ['neural network', 'training data'])
})

test('does not invent simplified content when no lecture text exists', () => {
  const content = buildSimplifiedLecture([], null)

  assert.equal(content.hasContent, false)
  assert.equal(content.text, '')
  assert.deepEqual(content.keyPoints, [])
  assert.deepEqual(content.technicalTerms, [])
})
