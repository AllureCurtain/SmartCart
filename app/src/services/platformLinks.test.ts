import { buildProductAppUrl } from './platformLinks';

const jdAppUrl = buildProductAppUrl({
  platform: 'jd',
  title: '蓝牙耳机',
});

if (!jdAppUrl.startsWith('openApp.jdMobile://virtual?params=')) {
  throw new Error(`expected JD app deep link, got ${jdAppUrl}`);
}

const jdParamsRaw = jdAppUrl.slice('openApp.jdMobile://virtual?params='.length);
const jdParams = JSON.parse(decodeURIComponent(jdParamsRaw)) as {
  category: string;
  des: string;
  keyword: string;
};

if (jdParams.des !== 'search' || jdParams.keyword !== '蓝牙耳机') {
  throw new Error(`expected JD search payload, got ${JSON.stringify(jdParams)}`);
}

const taobaoAppUrl = buildProductAppUrl({ platform: 'taobao', title: '蓝牙耳机' });

if (taobaoAppUrl !== 'taobao://s.taobao.com/search?q=%E8%93%9D%E7%89%99%E8%80%B3%E6%9C%BA') {
  throw new Error(`expected Taobao app search URL, got ${taobaoAppUrl}`);
}
