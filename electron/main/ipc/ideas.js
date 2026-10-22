// "이성규의 아이디어 창고": 옵시디언처럼 아이디어를 하나씩 마크다운 파일로
// 저장하고, 카테고리별로 묶어서 보여준다. 깃허브에 그대로 올라가도 되는
// 업무 아이디어 메모라, 레포 루트의 ideas/ 폴더에 평범한 .md 파일로
// 저장한다(설정 저장소인 electron-store가 아니라 깃이 추적하는 실제
// 파일로 남겨야 커밋/이력 관리가 된다).
//
// 각 파일은 아주 단순한 프론트매터(key: value, 첫 줄 "---"~"---") +
// 본문 구조다. 외부 yaml 라이브러리 없이 직접 파싱/생성한다.

const fs = require('fs');
const path = require('path');

const IDEAS_DIR = path.join(__dirname, '..', '..', '..', 'ideas');
const UNCATEGORIZED = '미분류';

function ensureIdeasDir() {
  fs.mkdirSync(IDEAS_DIR, { recursive: true });
}

// 파일명/폴더명에 못 쓰는 문자를 치환한다 (카테고리명을 그대로 폴더명으로 쓰므로).
function safeSegment(text) {
  return (text || '').trim().replace(/[\\/:*?"<>|]/g, '_') || UNCATEGORIZED;
}

function timestampTag(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return (
    `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}-` +
    `${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
  );
}

function frontmatterValue(lines, key) {
  const prefix = `${key}:`;
  const line = lines.find((l) => l.startsWith(prefix));
  return line ? line.slice(prefix.length).trim() : '';
}

function parseIdeaFile(relativePath, raw) {
  const lines = raw.split('\n');
  if (lines[0] !== '---') {
    // 프론트매터가 없는(외부에서 직접 추가한) .md 파일도 제목만이라도 보여준다.
    return {
      id: relativePath,
      title: path.basename(relativePath, '.md'),
      category: UNCATEGORIZED,
      tags: [],
      createdAt: '',
      body: raw.trim(),
    };
  }

  const endIndex = lines.indexOf('---', 1);
  const frontmatterLines = endIndex === -1 ? [] : lines.slice(1, endIndex);
  const body = endIndex === -1 ? '' : lines.slice(endIndex + 1).join('\n').trim();

  const tagsRaw = frontmatterValue(frontmatterLines, 'tags');

  return {
    id: relativePath,
    title: frontmatterValue(frontmatterLines, 'title') || path.basename(relativePath, '.md'),
    category: frontmatterValue(frontmatterLines, 'category') || UNCATEGORIZED,
    tags: tagsRaw ? tagsRaw.split(',').map((t) => t.trim()).filter(Boolean) : [],
    createdAt: frontmatterValue(frontmatterLines, 'createdAt'),
    body,
  };
}

function walkMarkdownFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkMarkdownFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      results.push(fullPath);
    }
  }
  return results;
}

function listIdeas() {
  ensureIdeasDir();
  const files = walkMarkdownFiles(IDEAS_DIR);

  const ideas = files.map((filePath) => {
    const relativePath = path.relative(IDEAS_DIR, filePath);
    const raw = fs.readFileSync(filePath, 'utf-8');
    return parseIdeaFile(relativePath, raw);
  });

  ideas.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  return ideas;
}

function createIdea({ title, category, tags, body }) {
  ensureIdeasDir();

  const safeCategory = safeSegment(category);
  const categoryDir = path.join(IDEAS_DIR, safeCategory);
  fs.mkdirSync(categoryDir, { recursive: true });

  const now = new Date();
  const safeTitle = safeSegment(title) || '아이디어';
  const filename = `${timestampTag(now)}-${safeTitle}.md`.slice(0, 200);
  const filePath = path.join(categoryDir, filename);

  const tagsLine = Array.isArray(tags) ? tags.filter(Boolean).join(', ') : '';
  const createdAt = now.toISOString();

  const content = [
    '---',
    `title: ${title || safeTitle}`,
    `category: ${category || UNCATEGORIZED}`,
    `tags: ${tagsLine}`,
    `createdAt: ${createdAt}`,
    '---',
    '',
    body || '',
    '',
  ].join('\n');

  fs.writeFileSync(filePath, content, 'utf-8');

  return parseIdeaFile(path.relative(IDEAS_DIR, filePath), content);
}

function deleteIdea(id) {
  const filePath = path.join(IDEAS_DIR, id);
  // IDEAS_DIR 바깥 경로(../ 등으로 레포 다른 곳을 가리키는 id)는 절대 지우지 않는다.
  if (!filePath.startsWith(IDEAS_DIR)) {
    return { success: false, error: '잘못된 경로입니다.' };
  }
  if (!fs.existsSync(filePath)) {
    return { success: false, error: '이미 삭제된 아이디어입니다.' };
  }
  fs.unlinkSync(filePath);
  return { success: true };
}

module.exports = { listIdeas, createIdea, deleteIdea, IDEAS_DIR };
