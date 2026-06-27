import { describe, expect, it } from 'vitest'
import { readNdjson } from './client'

describe('readNdjson', () => {
  it('parses records split across stream chunks', async () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('{"event":"step","data":'))
        controller.enqueue(encoder.encode('{"step":1}}\n{"event":"result"}\n'))
        controller.close()
      }
    })
    const events = []
    for await (const event of readNdjson(new Response(stream))) events.push(event)
    expect(events).toEqual([
      { event: 'step', data: { step: 1 } },
      { event: 'result' }
    ])
  })
})
