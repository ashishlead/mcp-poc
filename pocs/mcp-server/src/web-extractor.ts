import * as cheerio from 'cheerio';

export async function extractWebContent(url: string): Promise<string> {
  try {
    if (!url.match(/^(https?:\/\/)/i)) {
      throw new Error('Invalid URL');
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error('Failed to fetch content');
    }

    const html = await response.text();
    const $ = cheerio.load(html);
    const title = $('title').text().trim();

    $('script, style, nav, header, footer, iframe, noscript').remove();

    let mainContent = $('main, article, [role="main"], .content, #content');
    if (mainContent.length === 0) {
      mainContent = $('body');
    }

    const text = mainContent.text();

    return `Title: ${title}\n\n${text}`;
  } catch (error) {
    throw new Error('Failed to extract');
  }
}