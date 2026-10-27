'use strict';

const COPY_TIMEOUT_MS = 500;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'clipboard-write') return false;
  writeClipboard(String(message.text ?? ''))
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error) }));
  return true;
});

async function writeClipboard(text) {
  const viaApi = await withTimeout(writeWithClipboardApi(text), COPY_TIMEOUT_MS);
  if (viaApi === true) return { ok: true, method: 'clipboard' };
  if (copyWithSelection(text)) return { ok: true, method: 'execCommand' };
  return { ok: false, error: viaApi === null ? 'délai dépassé' : String(viaApi) };
}

async function writeWithClipboardApi(text) {
  await navigator.clipboard.writeText(text);
  return true;
}

function withTimeout(promise, ms) {
  return Promise.race([
    promise.then(() => true, (error) => String(error)),
    new Promise((resolve) => setTimeout(() => resolve(null), ms)),
  ]);
}

function copyWithSelection(text) {
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  field.style.position = 'fixed';
  field.style.top = '-1000px';
  document.body.appendChild(field);
  field.select();
  field.setSelectionRange(0, text.length);
  let copied = false;
  try {
    copied = document.execCommand('copy');
  } catch (_error) {
    copied = false;
  }
  field.remove();
  return copied;
}
