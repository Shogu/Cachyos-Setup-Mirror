// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
const PREVIEW_LENGTH = 160;
const SKIPPED_LINE = /^(#|```|~~~|-{3,}$|\*{3,}$|_{3,}$|\||<!--)/;
const LIST_MARKER = /^([-*+]|\d+[.)])\s+(\[[ xX]\]\s+)?/;
const TIME = /(?:^|[^\d])([01]?\d|2[0-3])\s*(?:h|:)\s*([0-5]\d)?(?![\d])/i;

function withoutFrontMatter(lines) {
    if (lines[0].trim() !== '---')
        return lines;
    const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---');
    return end > 0 ? lines.slice(end + 1) : lines;
}

function plainInline(text) {
    return text
        .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
        .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
        .replace(/[*_~`]+/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

export function notePreview(text) {
    for (const raw of withoutFrontMatter(text.split('\n'))) {
        const line = raw.trim().replace(/^(>\s*)+/, '');
        if (!line || SKIPPED_LINE.test(line))
            continue;
        return plainInline(line.replace(LIST_MARKER, '')).slice(0, PREVIEW_LENGTH);
    }
    return '';
}

export function taskProgress(text) {
    const tasks = noteTasks(text);
    return tasks.length ? {done: tasks.filter(task => task.done).length, total: tasks.length} : null;
}

export function noteTasks(text) {
    const tasks = [];
    text.split('\n').forEach((line, index) => {
        const match = line.match(/^\s*[-*+]\s+\[([ xX])\]\s*(.*)$/);
        if (match)
            tasks.push({line: index, done: match[1] !== ' ', label: plainInline(match[2]) || '…'});
    });
    return tasks;
}

export function toggleTask(text, lineIndex) {
    const lines = text.split('\n');
    lines[lineIndex] = lines[lineIndex].replace(/\[([ xX])\]/, (_mark, state) => (state === ' ' ? '[x]' : '[ ]'));
    return lines.join('\n');
}

export function searchKey(text) {
    return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

export function eventTime(title) {
    const match = title.match(TIME);
    return match ? {hour: Number(match[1]), minute: Number(match[2] ?? 0)} : null;
}

export function bodyWithoutTitle(text, title) {
    const lines = text.split('\n');
    const first = lines.findIndex(line => line.trim());
    if (first >= 0 && /^#\s/.test(lines[first]) && plainInline(lines[first].slice(2)) === title)
        lines.splice(first, 1);
    return lines.join('\n').trim();
}
