export interface ProductLinkInput {
  platform: 'jd' | 'taobao';
  title?: string | null;
}

function encodeKeyword(title?: string | null): string {
  return encodeURIComponent(title || '');
}

export function buildProductAppUrl(product: ProductLinkInput): string {
  if (product.platform === 'jd') {
    const params = encodeURIComponent(
      JSON.stringify({
        category: 'jump',
        des: 'search',
        keyword: product.title || '',
      })
    );
    return `openApp.jdMobile://virtual?params=${params}`;
  }

  return `taobao://s.taobao.com/search?q=${encodeKeyword(product.title)}`;
}
