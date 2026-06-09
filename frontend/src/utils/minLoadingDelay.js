/** Keep loading UI visible long enough to read (fast catalog/API responses). */
export async function minLoadingDelay(startedAt, minMs = 420) {
  const elapsed = Date.now() - startedAt;
  if (elapsed < minMs) {
    await new Promise((resolve) => {
      setTimeout(resolve, minMs - elapsed);
    });
  }
}
