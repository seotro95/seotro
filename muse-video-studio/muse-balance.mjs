// Parse an explicitly labelled balance, never a model context size or chat text.
export function parseMuseBalance(text, hint = '') {
  const label = String(text).replace(/\s+/g, ' ').trim();
  const context = `${label} ${hint}`;
  if (!label || label.length > 180 || !/balance|remaining|left|available|số dư|còn lại|khả dụng/i.test(context)) return null;
  const tokens = /\btokens?\b/i.test(context);
  const credits = /\bcredits?\b|tín dụng/i.test(context);
  if (tokens === credits) return null;
  const numbers = label.match(/\d[\d,.\s]*(?:[kKmM](?![a-z]))?/g);
  if (!numbers || numbers.length !== 1 || /\d\s*\/\s*\d/.test(label)) return null;
  const valueText = numbers[0].trim();
  if (valueText.length > 30) return null;
  const shape = label.replace(numbers[0], '#');
  const labelled = /^(?:(?:remaining|available|balance|số dư|còn lại|your)\s*)?(?:tokens?|credits?|tín dụng)\s*(?:remaining|left|available|balance|còn lại|khả dụng)?\s*[:：]?\s*#\s*(?:remaining|left|available|còn lại)?$/i.test(shape)
    || /^#\s*(?:tokens?|credits?|tín dụng)\s*(?:remaining|left|available|còn lại)?$/i.test(shape)
    || /^(?:balance|số dư|remaining|available)\s*[:：]?\s*#\s*(?:tokens?|credits?)$/i.test(shape)
    || label === valueText;
  if (!labelled) return null;
  return { valueText, unit: tokens ? 'token' : 'credit', label, source: 'muse-ui' };
}

export async function readMuseBalance(page, selector = process.env.MUSE_BALANCE_SELECTOR) {
  const candidates = await page.evaluate(custom => {
    const query = custom || '[data-testid*="balance" i], [data-testid*="remaining" i], [aria-label*="balance" i], [aria-label*="remaining" i], header, aside, [role="navigation"]';
    let elements;
    try { elements = Array.from(document.querySelectorAll(query)); } catch { return []; }
    return elements.filter(el => !el.closest('[data-message-item], [data-hatch-composer-root]') && !el.querySelector('[data-message-item], [data-hatch-composer-root]') && el.getClientRects().length)
      .map(el => ({ text: el.innerText || '', hint: `${el.getAttribute('data-testid') || ''} ${el.getAttribute('aria-label') || ''} ${el.getAttribute('title') || ''}` }))
      .filter(item => item.text.trim().length <= 180).slice(0, 30);
  }, selector || null).catch(() => []);
  for (const item of candidates) {
    const parsed = parseMuseBalance(item.text, item.hint);
    if (parsed) return { ...parsed, observedAt: new Date().toISOString() };
  }
  return null;
}
