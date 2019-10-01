import { getParsedContent, dump } from './read-data';
import { shuffle, zip } from 'lodash';
import * as path from 'path';
import { promises } from 'fs';

const { appendFile } = promises;

(async () => {
  let i = 0;
  for await(const page of getParsedContent(path.join(__dirname, './10k_results.json'), x => x.toLowerCase().includes('role="button"'))) {
    const roleButtons = Array.from(page.dom.querySelectorAll('[role=button]'));
    const others = shuffle(Array.from(page.dom.querySelectorAll('body > * > :not([role=button]')));

    for(const [positive, negative] of zip(roleButtons, others)) {
      if (!positive || !negative) {
        break;
      }
      const positiveFeatures = getFeatures(positive);
      const negativeFeatures = getFeatures(negative);
      await Promise.all([
        appendFeatures(positiveFeatures, page.url, 1),
        appendFeatures(negativeFeatures, page.url, 0)
      ]);
    }
  }
})();

async function appendFeatures(features: ReturnType<typeof getFeatures>, url: string, label: 0 | 1) {
  await appendFile('./dump/features.json', JSON.stringify({
    features: features,
    label,
    url
  }) + '\n');

}
function getFeatures(element: Element) {
  const attributes = Array.from(element.attributes).map(x => x.name);

  if (Array.from(element.textContent!, x => x.charCodeAt(0)).some(x => x > 127)) {
    return;
  }
  return {
    tagName: element.tagName,
    parentTagName: element.parentElement!.tagName,
    text: element.textContent!.trim().substring(0, 100),
    attributes,
    title: element.getAttribute('title'),
    alt: element.getAttribute('alt'),
    ariaLabel: element.getAttribute('aria-label'),
    isModal: element.getAttribute('aria-modal') === 'true',
    name: element.getAttribute('name'),
    hasDataset: attributes.some(x => x.startsWith('data-')),
    id: element.id,
    tagNamesWithin: Array.from(new Set(Array.from(element.querySelectorAll('*'), x => x.tagName))).slice(0, 10),
  };
}
