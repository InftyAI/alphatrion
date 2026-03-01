import { diffLines } from "diff";

export type DiffLine = {
    type: 'same' | 'removed' | 'added';
    content: string;
    oldLineNum: number | null;
    newLineNum: number | null;
};

export type SplitLine = {
    type: 'same' | 'removed' | 'added' | 'empty';
    content: string;
    lineNum: number | null;
};

export type FileDiff = {
    filename: string;
    unified: DiffLine[];
    left: SplitLine[];
    right: SplitLine[];
    additions: number;
    removals: number;
};

export type FileEntry = { filename: string; code: string };

export function parseMultiFileContent(contentText: string): FileEntry[] {
    const headerRegex = /^## (.+)$/gm;
    const headers: { index: number; filename: string }[] = [];
    let match;
    while ((match = headerRegex.exec(contentText)) !== null) {
        headers.push({ index: match.index, filename: match[1].trim() });
    }

    if (headers.length === 0) {
        return [{ filename: '', code: contentText }];
    }

    return headers.map((header, i) => {
        const start = header.index + contentText.slice(header.index).indexOf('\n') + 1;
        const end = i + 1 < headers.length ? headers[i + 1].index : contentText.length;
        let code = contentText.slice(start, end).trim();
        // Strip wrapping ```lang ... ``` fences
        const fenceMatch = code.match(/^```[^\n]*\n([\s\S]*?)```\s*$/);
        if (fenceMatch) {
            code = fenceMatch[1];
        }
        // Remove trailing newline for cleaner diff
        if (code.endsWith('\n')) {
            code = code.slice(0, -1);
        }
        return { filename: header.filename, code };
    });
}

export function computeFileDiff(filename: string, code1: string, code2: string): FileDiff {
    const changes = diffLines(code1, code2);

    const unified: DiffLine[] = [];
    let oldLineNum = 1;
    let newLineNum = 1;

    const left: SplitLine[] = [];
    const right: SplitLine[] = [];
    let leftLineNum = 1;
    let rightLineNum = 1;

    let additions = 0;
    let removals = 0;

    for (const change of changes) {
        const lines = change.value.replace(/\n$/, '').split('\n');
        for (const line of lines) {
            if (change.removed) {
                removals++;
                unified.push({ type: 'removed', content: line, oldLineNum: oldLineNum++, newLineNum: null });
                left.push({ type: 'removed', content: line, lineNum: leftLineNum++ });
                right.push({ type: 'empty', content: '', lineNum: null });
            } else if (change.added) {
                additions++;
                unified.push({ type: 'added', content: line, oldLineNum: null, newLineNum: newLineNum++ });
                left.push({ type: 'empty', content: '', lineNum: null });
                right.push({ type: 'added', content: line, lineNum: rightLineNum++ });
            } else {
                unified.push({ type: 'same', content: line, oldLineNum: oldLineNum++, newLineNum: newLineNum++ });
                left.push({ type: 'same', content: line, lineNum: leftLineNum++ });
                right.push({ type: 'same', content: line, lineNum: rightLineNum++ });
            }
        }
    }

    return { filename, unified, left, right, additions, removals };
}

export function computeAllFileDiffs(text1: string, text2: string): FileDiff[] {
    const files1 = parseMultiFileContent(text1);
    const files2 = parseMultiFileContent(text2);

    const isMultiFile = files1.length > 1 || files2.length > 1
        || (files1.length === 1 && files1[0].filename !== '')
        || (files2.length === 1 && files2[0].filename !== '');

    // Single-file: use the whole text as-is (no file headers)
    if (!isMultiFile) {
        return [computeFileDiff('', text1, text2)];
    }

    // Build maps for lookup
    const map1 = new Map<string, string>();
    for (const f of files1) map1.set(f.filename, f.code);
    const map2 = new Map<string, string>();
    for (const f of files2) map2.set(f.filename, f.code);

    // Union of filenames preserving order
    const seen = new Set<string>();
    const allFilenames: string[] = [];
    for (const f of files1) {
        if (!seen.has(f.filename)) { allFilenames.push(f.filename); seen.add(f.filename); }
    }
    for (const f of files2) {
        if (!seen.has(f.filename)) { allFilenames.push(f.filename); seen.add(f.filename); }
    }

    return allFilenames.map(filename =>
        computeFileDiff(filename, map1.get(filename) ?? '', map2.get(filename) ?? '')
    );
}
