export function consumeSseChunk(buffer, chunk) {
  const parts = `${buffer}${chunk}`.split('\n\n')
  const remainder = parts.pop() || ''
  const events = parts.flatMap((part) => {
    const line = part.split('\n').find((value) => value.startsWith('data: '))
    if (!line) return []
    try {
      return [JSON.parse(line.slice(6))]
    } catch {
      return []
    }
  })
  return { events, remainder }
}
