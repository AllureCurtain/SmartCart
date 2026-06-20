export const DEFAULT_VISIBLE_PRODUCT_COUNT = 3;

export interface ProductDisplaySlice<T> {
  visibleProducts: T[];
  hiddenCount: number;
  hasHiddenProducts: boolean;
  canCollapse: boolean;
  limit: number;
}

export function splitDisplayProducts<T>(
  products: T[],
  expanded: boolean,
  limit = DEFAULT_VISIBLE_PRODUCT_COUNT
): ProductDisplaySlice<T> {
  if (expanded) {
    return {
      visibleProducts: products,
      hiddenCount: 0,
      hasHiddenProducts: false,
      canCollapse: products.length > limit,
      limit,
    };
  }

  const hiddenCount = Math.max(products.length - limit, 0);

  return {
    visibleProducts: products.slice(0, limit),
    hiddenCount,
    hasHiddenProducts: hiddenCount > 0,
    canCollapse: false,
    limit,
  };
}
