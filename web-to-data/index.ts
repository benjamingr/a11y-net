import { getParsedContent, dump } from './read-data';
import { shuffle, uniq } from 'lodash';
import * as path from 'path';
import { promises } from 'fs';

const { appendFile, unlink, readFile, writeFile } = promises;

(async () => {
  let i = 0;
  await unlink('./dump/features.json').catch(() => { })

  for await (const page of getParsedContent(path.join(__dirname, './10k_results.json'), x => x.toLowerCase().includes('role="button"'))) {
    const roleButtons = Array.from(page.dom.querySelectorAll('[role=button]'));
    const others = shuffle(Array.from(page.dom.querySelectorAll('body > * > * > :not([role=button]')));

    for (const positive of roleButtons) {
      if (!positive) {
        break;
      }
      const positiveFeatures = getFeatures(positive);
      if (positiveFeatures) {
        await appendFeatures(positiveFeatures, page.url, 1);
      }
    }
    for(const negative of others) {
      const negativeFeatures = getFeatures(negative);
      if (negativeFeatures) {
        await appendFeatures(negativeFeatures, page.url, 0);
      }
    }
  }
  // now, let's read the whole file, shuffle it and split it into test and train

  const buffer = await readFile('./dump/features.json');
  const shuffled = shuffle(buffer.toString().split('\n'));

  const trainingSize = Math.floor((shuffled.length) * (8 / 10));
  await writeFile('./dump/features-training.json', shuffled.slice(0, trainingSize).join('\n'));
  await writeFile('./dump/features-validation.json', shuffled.slice(trainingSize + 1).join('\n'));
})();

async function appendFeatures(features: ReturnType<typeof getFeatures>, url: string, label: 0 | 1) {
  await appendFile('./dump/features.json', JSON.stringify({
    features: features,
    label,
    url
  }) + '\n');

}
function getFeatures(element: Element) {
  const attributes = Array.from(element.attributes).map(x => x.name).filter(attribute =>
    attribute !== 'id' &&
    attribute !== 'name' &&
    attribute !== 'role' &&
    attribute !== 'class' &&
    attribute !== 'title' &&
    attribute !== 'aria-label'
  );

  if (Array.from(element.textContent!, x => x.charCodeAt(0)).some(x => x > 127)) {
    return;
  }


  function isMostTextLinks() {
    if (element.tagName === 'A') { // the element is a link, obviously all its content is in a link
      return true;
    }
    // we ignore the case the element's parent is a link here.
    const elementTextLength = (element.textContent || "").length;
    const elementLinkTextLength = Array.from(element.querySelectorAll('a'), x => x.textContent).join('').length; 
    return ((elementTextLength - elementLinkTextLength) / elementTextLength) > 0.5;
  }
  function areThereButtonsInside() {
    return element.querySelectorAll('button').length > 0;
  }
  function containsHandCursor() {
    return element.ownerDocument!.defaultView!.getComputedStyle(element).cursor === 'pointer';
  }
  
  return {
    tagName: element.tagName.toUpperCase(), // jsdom has a bug where sometimes tagnames are not returned as uppercase per spec
    parentTagName: element.parentElement!.tagName.toUpperCase(),
    text: element.textContent!.split(/\s+/g).slice(0, 10).join(' '),
    attributes: attributes.join(' '),
    title: element.getAttribute('title'),
    alt: element.getAttribute('alt'),
    // ariaLabel: element.getAttribute('aria-label'),
    // isModal: element.getAttribute('aria-modal') === 'true',
    name: element.getAttribute('name'),
    hasDataset: attributes.some(x => x.startsWith('data-')),
    isMostTextLinks: isMostTextLinks(),
    containsHandCursor: containsHandCursor(),
    areThereButtonsInside: areThereButtonsInside (),
    id: element.id,
    classList: Array.from(element.classList).join(' '),
    descendentsClassList: uniq(Array.from(element.querySelectorAll('*'), x => x.classList).flat().map(x => x.value.split(' ')).flat()).join(' '),
    tagNamesWithin: Array.from(new Set(Array.from(element.querySelectorAll('*'), x => x.tagName.toUpperCase()))).slice(0, 10).join(' '),
  };
}

function getTree(elementToMark: Element, element: Element) {
  let text = `(${element.tagName} `;

  if (element === elementToMark) {
    text += ' MARK ' 
  }
  if (element.children.length > 0) {
    text += `(${Array.from(element.children, getTree.bind(null, elementToMark))})`;
  }
  return text + `)`;
}
