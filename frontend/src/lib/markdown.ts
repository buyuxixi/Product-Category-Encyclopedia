/** Chat-oriented Markdown → HTML（标题 / 列表 / 表格 / 加粗 / 链接 / 代码块）。XSS 安全：先 escape 再插格式标签。 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return trimmed.split('|').map((c) => c.trim())
}

function isTableSeparator(line: string): boolean {
  const cells = splitTableRow(line)
  return cells.length > 0 && cells.every((c) => /^:?-{1,}:?$/.test(c))
}

function inlineFormat(text: string): string {
  let out = escapeHtml(text)
  out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label: string, url: string) => {
    const trimmed = url.trim()
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return `<a href="${trimmed}" target="_blank" rel="noreferrer noopener">${label}</a>`
    }
    return match
  })
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  out = out.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>')
  out = out.replace(/(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
  return out
}

export function renderMarkdown(md: string): string {
  if (!md) return ''
  const lines = md.replace(/\r\n/g, '\n').split('\n')
  const html: string[] = []
  let i = 0
  let inList: 'ul' | 'ol' | null = null
  let tableBuffer: string[] = []
  let inCode = false
  let codeLang = ''
  let codeLines: string[] = []

  function flushList() {
    if (inList) {
      html.push(`</${inList}>`)
      inList = null
    }
  }

  function flushTable() {
    if (tableBuffer.length >= 2) {
      const realSepIdx = tableBuffer.findIndex((l) => isTableSeparator(l))
      if (realSepIdx > 0) {
        const headerCells = splitTableRow(tableBuffer[0])
        const bodyRows = tableBuffer.slice(realSepIdx + 1)
        let t = '<table class="md-table"><thead><tr>'
        for (const cell of headerCells) t += `<th>${inlineFormat(cell)}</th>`
        t += '</tr></thead><tbody>'
        for (const row of bodyRows) {
          if (!row.trim() || isTableSeparator(row)) continue
          const cells = splitTableRow(row)
          t += '<tr>'
          for (const cell of cells) t += `<td>${inlineFormat(cell)}</td>`
          t += '</tr>'
        }
        t += '</tbody></table>'
        html.push(t)
      } else {
        for (const l of tableBuffer) html.push(`<p>${inlineFormat(l)}</p>`)
      }
    } else if (tableBuffer.length === 1) {
      html.push(`<p>${inlineFormat(tableBuffer[0])}</p>`)
    }
    tableBuffer = []
  }

  function flushCode() {
    if (!inCode) return
    const body = escapeHtml(codeLines.join('\n'))
    html.push(`<pre class="md-code"${codeLang ? ` data-lang="${escapeHtml(codeLang)}"` : ''}><code>${body}</code></pre>`)
    inCode = false
    codeLang = ''
    codeLines = []
  }

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed.startsWith('```')) {
      flushList()
      flushTable()
      if (inCode) {
        flushCode()
      } else {
        inCode = true
        codeLang = trimmed.slice(3).trim()
        codeLines = []
      }
      i++
      continue
    }

    if (inCode) {
      codeLines.push(line)
      i++
      continue
    }

    if (!trimmed) {
      flushList()
      flushTable()
      i++
      continue
    }

    if (trimmed.startsWith('|')) {
      flushList()
      tableBuffer.push(trimmed)
      i++
      continue
    }
    flushTable()

    if (/^#{1,6}\s/.test(trimmed)) {
      flushList()
      const match = trimmed.match(/^(#{1,6})\s+(.+)/)
      if (match) {
        const level = Math.min(match[1].length + 1, 6) // h2–h6 in bubble
        html.push(`<h${level}>${inlineFormat(match[2])}</h${level}>`)
      }
      i++
      continue
    }

    if (trimmed.startsWith('>')) {
      flushList()
      html.push(`<blockquote>${inlineFormat(trimmed.replace(/^>\s?/, ''))}</blockquote>`)
      i++
      continue
    }

    if (/^[-*+]\s/.test(trimmed)) {
      if (inList !== 'ul') {
        flushList()
        html.push('<ul>')
        inList = 'ul'
      }
      html.push(`<li>${inlineFormat(trimmed.replace(/^[-*+]\s+/, ''))}</li>`)
      i++
      continue
    }

    if (/^\d+\.\s/.test(trimmed)) {
      const match = trimmed.match(/^(\d+)\.\s+(.+)/)
      if (!match) {
        i++
        continue
      }
      if (inList !== 'ol') {
        flushList()
        html.push(`<ol start="${Number(match[1])}">`)
        inList = 'ol'
      }
      html.push(`<li>${inlineFormat(match[2])}</li>`)
      i++
      continue
    }

    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      flushList()
      html.push('<hr />')
      i++
      continue
    }

    flushList()
    html.push(`<p>${inlineFormat(trimmed)}</p>`)
    i++
  }

  flushList()
  flushTable()
  flushCode()
  return html.join('\n')
}
