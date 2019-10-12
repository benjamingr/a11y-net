import * as filenamify from 'filenamify';
import { createReadStream, promises } from 'fs';
import { JSDOM } from 'jsdom';
import * as readline from 'readline';

const { writeFile } = promises;

interface ISiteResult {
  accessibilityScore: string;
  pageUrl: string;
  lighthouseAudit: string;
  body: string;
}

async function* readContent(filePath: string) {
  const stream = createReadStream(filePath);
  const jsonStream = readline.createInterface({
    input: stream,
  });
  for await (const line of jsonStream) {
    try {
      yield JSON.parse(line) as ISiteResult;
    } catch (e) {
      console.error('Failed to parse line ', line);
    }
  }
}

interface ISiteData {
  dom: Document;
  url: string;
  accessibilityScore: number;
}
export async function dump(datum: ISiteData) {
  await writeFile('dump/' + filenamify(datum.url) + '.html', datum.dom.documentElement.outerHTML);
}

export async function* getParsedContent(
  filePath: string,
  bodyFilter: (body: string) => boolean,
): AsyncIterable<ISiteData> {
  for await (const item of readContent(filePath)) {
    if (!bodyFilter(item.body)) {
      continue;
    }
    yield {
      dom: new JSDOM(item.body).window.document,
      url: item.pageUrl,
      accessibilityScore: Number(item.accessibilityScore),
    };
  }
}
