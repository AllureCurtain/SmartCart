import { splitDisplayProducts } from './resultDisplay';

interface TestProduct {
  id: string;
  title: string;
  price: number;
  platform: string;
}

function product(id: string): TestProduct {
  return {
    id,
    title: `商品 ${id}`,
    price: Number(id),
    platform: 'jd',
  };
}

const products = ['1', '2', '3', '4', '5'].map(product);

const collapsed = splitDisplayProducts(products, false);

if (collapsed.visibleProducts.map((item) => item.id).join(',') !== '1,2,3') {
  throw new Error(`expected first three products by default, got ${collapsed.visibleProducts.map((item) => item.id).join(',')}`);
}

if (collapsed.hiddenCount !== 2 || !collapsed.hasHiddenProducts) {
  throw new Error(`expected two hidden products, got ${collapsed.hiddenCount}`);
}

const expanded = splitDisplayProducts(products, true);

if (expanded.visibleProducts.length !== 5 || expanded.hiddenCount !== 0 || expanded.hasHiddenProducts) {
  throw new Error('expected all products visible when expanded');
}

const short = splitDisplayProducts(products.slice(0, 2), false);

if (short.visibleProducts.length !== 2 || short.hiddenCount !== 0 || short.hasHiddenProducts) {
  throw new Error('expected no folded section for two products');
}
