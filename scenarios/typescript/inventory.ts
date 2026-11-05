type Item = { sku: string; available: number };

export function availableFor(items: readonly Item[], sku: string): number {
  const item = items.find(entry => entry.sku === sku);
  return item?.quantity ?? 0;
}
