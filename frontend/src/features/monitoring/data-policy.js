const CACHE_KEY = 'sportfusion.monitoring.snapshot.v1'

export const isUsableSnapshot = (value) => Boolean(
  value?.metrics?.length
  && ['real', 'cached', 'demo'].includes(value?.provenance?.mode),
)

export function resolveSnapshot({ remote, cached, demo }) {
  if (isUsableSnapshot(remote)) return remote
  if (isUsableSnapshot(cached)) {
    return {
      ...cached,
      provenance: { ...cached.provenance, mode: 'cached' },
    }
  }
  return demo
}

export function readCachedSnapshot(storage = localStorage) {
  try {
    return JSON.parse(storage.getItem(CACHE_KEY) || 'null')
  } catch {
    return null
  }
}

export function writeCachedSnapshot(snapshot, storage = localStorage) {
  if (snapshot?.provenance?.mode === 'real' && isUsableSnapshot(snapshot)) {
    storage.setItem(CACHE_KEY, JSON.stringify(snapshot))
  }
}
