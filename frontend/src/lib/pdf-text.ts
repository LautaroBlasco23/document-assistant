import { pdfjs } from 'react-pdf'

export async function extractPdfText(url: string): Promise<string> {
  const pdf = await pdfjs.getDocument(url).promise
  const textParts: string[] = []
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const content = await page.getTextContent()
    const pageText = content.items
      .map((item) => {
        if ('str' in item) return item.str
        return ''
      })
      .join(' ')
    textParts.push(pageText)
  }
  return textParts.join('\n\n')
}

export async function extractPdfPages(
  url: string,
  startPage: number,
  endPage: number,
): Promise<string> {
  const pdf = await pdfjs.getDocument(url).promise
  const clampedStart = Math.max(1, startPage)
  const clampedEnd = Math.min(pdf.numPages, endPage)
  const textParts: string[] = []
  for (let i = clampedStart; i <= clampedEnd; i++) {
    const page = await pdf.getPage(i)
    const content = await page.getTextContent()
    const pageText = content.items
      .map((item) => {
        if ('str' in item) return item.str
        return ''
      })
      .join(' ')
    textParts.push(pageText)
  }
  return textParts.join('\n\n')
}
