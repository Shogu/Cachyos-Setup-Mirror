'use strict';

const BADGE_MS = 2000;
const BADGE_OK = '#2ec27e';
const BADGE_ERROR = '#c01c28';

// Le menu « Ouvrir avec Grabber » remet l'URL au système par le schéma
// de l'application : c'est le seul chemin qui puisse la réveiller quand elle est
// fermée, et le seul endroit du code où son nom apparaît.
const SCHEME = 'grabber://add';
const TAB_CLOSE_DELAY_MS = 1500;
const MAX_URLS_PER_CALL = 12;
const MAX_URI_LENGTH = 1800;

// Ordre d'affichage : portées croissantes, Copier et Ouvrir appariés.
const MENUS = [
  { id: 'open-action', title: 'Ouvrir cet onglet avec Grabber', contexts: ['action'] },
  { id: 'open-link', title: 'Ouvrir ce lien avec Grabber', contexts: ['link'] },
  { id: 'copy-current', title: 'Copier l’URL de cet onglet', contexts: ['page', 'frame', 'tab'] },
  { id: 'open-current', title: 'Ouvrir cet onglet avec Grabber', contexts: ['page', 'frame', 'tab'] },
  { id: 'separator-scopes', type: 'separator', contexts: ['page', 'frame', 'tab'] },
  { id: 'copy-highlighted', title: 'Copier les URL des onglets sélectionnés', contexts: ['tab'] },
  { id: 'open-highlighted', title: 'Ouvrir les URL des onglets sélectionnés avec Grabber', contexts: ['tab'] },
  { id: 'copy-window', title: 'Copier les URL de cette fenêtre', contexts: ['page', 'frame', 'tab'] },
  { id: 'open-window', title: 'Ouvrir les URL de cette fenêtre avec Grabber', contexts: ['page', 'frame', 'tab'] },
  { id: 'open-image', title: 'Ouvrir cette image avec Grabber', contexts: ['image'] },
  { id: 'open-video', title: 'Ouvrir cette vidéo avec Grabber', contexts: ['video'] },
  { id: 'open-audio', title: 'Ouvrir cet audio avec Grabber', contexts: ['audio'] },
  { id: 'copy-selection', title: 'Copier l’URL de cette sélection', contexts: ['selection'] },
];

function ensureMenus() {
  chrome.contextMenus.removeAll(() => {
    let created = 0;
    for (const menu of MENUS) {
      chrome.contextMenus.create(menu);
      if (chrome.runtime.lastError) {
        console.error(`menu « ${menu.id} » non créé : ${chrome.runtime.lastError.message}`);
      } else {
        created += 1;
      }
    }
    console.log(`menus : ${created}/${MENUS.length} entrées enregistrées`);
  });
}

chrome.runtime.onInstalled.addListener(ensureMenus);
chrome.runtime.onStartup.addListener(ensureMenus);

chrome.action.onClicked.addListener((tab) => copyUrls([tab?.url], 'onglet'));

chrome.contextMenus.onClicked.addListener((info, tab) => {
  switch (info.menuItemId) {
    case 'copy-current':
      copyUrls([tab?.url], 'onglet');
      break;
    case 'copy-selection':
      copyUrls(extractUrls(info.selectionText), 'sélection');
      break;
    case 'copy-highlighted':
      tabsIn({ highlighted: true, currentWindow: true }, (urls) => copyUrls(urls, 'onglets sélectionnés'));
      break;
    case 'copy-window':
      tabsIn({ currentWindow: true }, (urls) => copyUrls(urls, 'fenêtre'));
      break;
    case 'open-link':
      openWithGrabber([info.linkUrl], 'lien');
      break;
    case 'open-current':
    case 'open-action':
      openWithGrabber([tab?.url], 'onglet');
      break;
    case 'open-highlighted':
      tabsIn({ highlighted: true, currentWindow: true }, (urls) => openWithGrabber(urls, 'onglets sélectionnés'));
      break;
    case 'open-window':
      tabsIn({ currentWindow: true }, (urls) => openWithGrabber(urls, 'fenêtre'));
      break;
    case 'open-image':
    case 'open-video':
    case 'open-audio':
      openWithGrabber([info.srcUrl], 'média');
      break;
  }
});

chrome.commands.onCommand.addListener((command) => {
  if (command === 'copy-current') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => copyUrls([tabs[0]?.url], 'onglet'));
  } else if (command === 'copy-window') {
    tabsIn({ currentWindow: true }, (urls) => copyUrls(urls, 'fenêtre'));
  }
});

function tabsIn(query, action) {
  chrome.tabs.query(query, (tabs) => action(tabs.map((tab) => tab.url)));
}

function isHttpUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url);
}

function extractUrls(text) {
  if (!text) return [];
  const matches = text.match(/https?:\/\/[^\s<>"'`]+/gi) || [];
  return matches.map((url) => url.replace(/[.,;:!?)\]}]+$/, ''));
}

async function copyUrls(urls, label) {
  const unique = [...new Set((urls || []).filter(isHttpUrl))];
  if (!unique.length) {
    showBadge('0', BADGE_ERROR);
    return;
  }
  if (await copyToClipboard(unique.join('\n'))) {
    showBadge(String(unique.length), BADGE_OK);
    console.debug(`CopierURL : ${unique.length} URL copiée(s) (${label}).`);
    return;
  }
  showBadge('0', BADGE_ERROR);
  console.warn(`CopierURL : copie refusée (${label}).`);
}

async function copyToClipboard(text) {
  try {
    await ensureOffscreenDocument();
    const response = await chrome.runtime.sendMessage({ type: 'clipboard-write', text });
    if (response?.ok) return true;
    console.warn('CopierURL : écriture du presse-papiers refusée', response);
  } catch (error) {
    console.warn('CopierURL : presse-papiers indisponible', error);
  }
  return false;
}

let offscreenReady = null;
function ensureOffscreenDocument() {
  if (!offscreenReady) {
    offscreenReady = chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['CLIPBOARD'],
      justification: 'Écrire les URL copiées dans le presse-papiers.',
    }).catch((error) => {
      if (!String(error?.message || error).includes('offscreen')) {
        offscreenReady = null;
        throw error;
      }
    });
  }
  return offscreenReady;
}

function buildUri(urls) {
  return `${SCHEME}?${urls.map((url) => `url=${encodeURIComponent(url)}`).join('&')}`;
}

async function openProtocolTab(uri) {
  try {
    const tab = await chrome.tabs.create({ url: uri, active: false });
    if (tab?.id != null) {
      setTimeout(() => chrome.tabs.remove(tab.id).catch(() => {}), TAB_CLOSE_DELAY_MS);
    }
    return true;
  } catch (error) {
    console.warn('CopierURL : remise au protocole impossible', error);
    return false;
  }
}

async function openWithGrabber(urls, label) {
  const unique = [...new Set((urls || []).filter(isHttpUrl))];
  if (!unique.length) {
    showBadge('0', BADGE_ERROR);
    return;
  }
  let submitted = 0;
  for (const batch of splitBatches(unique)) {
    if (await openProtocolTab(buildUri(batch))) submitted += batch.length;
  }
  showBadge(String(submitted), submitted ? BADGE_OK : BADGE_ERROR);
  console.debug(`CopierURL : ${submitted} URL remise(s) au protocole (${label}).`);
}

function splitBatches(urls) {
  const batches = [];
  let current = [];
  let length = SCHEME.length + 1;
  for (const url of urls) {
    const cost = 4 + encodeURIComponent(url).length + 1;
    if (current.length && (current.length >= MAX_URLS_PER_CALL || length + cost > MAX_URI_LENGTH)) {
      batches.push(current);
      current = [];
      length = SCHEME.length + 1;
    }
    current.push(url);
    length += cost;
  }
  if (current.length) batches.push(current);
  return batches;
}

let badgeTimer;
function showBadge(text, color) {
  chrome.action.setBadgeBackgroundColor({ color });
  chrome.action.setBadgeText({ text });
  clearTimeout(badgeTimer);
  badgeTimer = setTimeout(() => chrome.action.setBadgeText({ text: '' }), BADGE_MS);
}
