import { useState, useEffect } from 'react'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import './App.css'
import { API_URL, PROMPTS_URL, REQUEST_TIMEOUT_MS, DEFAULT_PROMPT } from './constants'
import { toSections } from './utils/formatting'

function App() {
  const [company, setCompany] = useState('')
  const [promptName, setPromptName] = useState(DEFAULT_PROMPT)
  const [availablePrompts, setAvailablePrompts] = useState([])
  const [sections, setSections] = useState([])
  const [meta, setMeta] = useState({})
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Fetch available prompts on component mount
  useEffect(() => {
    const fetchPrompts = async () => {
      try {
        const response = await fetch(PROMPTS_URL)
        if (response.ok) {
          const data = await response.json()
          setAvailablePrompts(data.prompts || [])
          // Set default prompt if available
          if (data.default && !promptName) {
            setPromptName(data.default)
          }
        }
      } catch (err) {
        // If fetching prompts fails, use hardcoded defaults
        console.warn('Failed to fetch prompts, using defaults:', err)
        setAvailablePrompts([DEFAULT_PROMPT, 'warren-buffet'])
      }
    }
    fetchPrompts()
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!company.trim()) {
      setError('Please enter a company name')
      return
    }

    setIsLoading(true)
    setError('')
    setSections([])
    setMeta({})

    try {
      // Create an AbortController for timeout handling
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
      
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: company.trim(),
          prompt_name: promptName,
        }),
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || 'Analysis failed')
      }

      const data = await response.json()
      setSections(toSections(data?.analysis || data))
      if (data && typeof data === 'object') {
        const { analysis, ...rest } = data
        setMeta(rest)
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out. The analysis is taking longer than expected. Please try again or check the backend logs.')
      } else if (err.message.includes('Failed to fetch') || err.message.includes('network')) {
        setError('Network error: Could not connect to backend. Make sure the backend is running.')
      } else {
        setError(err.message || 'Something went wrong')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="app">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h1>Finvarta Analysis</h1>
            <p className="description">
              Submit a company name to run the fundamental analysis pipeline.
            </p>
          </div>
          <div className="badge">FastAPI · React</div>
        </div>

        <form className="form" onSubmit={handleSubmit}>
          <label htmlFor="prompt">Analysis Style</label>
          <select
            id="prompt"
            value={promptName}
            onChange={(event) => setPromptName(event.target.value)}
            disabled={isLoading}
          >
            {availablePrompts.length > 0 ? (
              availablePrompts.map((prompt) => (
                <option key={prompt} value={prompt}>
                  {prompt.replace(/-/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())}
                </option>
              ))
            ) : (
              <option value={DEFAULT_PROMPT}>
                {DEFAULT_PROMPT.replace(/-/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())}
              </option>
            )}
          </select>

          <label htmlFor="company">Company name</label>
          <div className="input-row">
            <input
              id="company"
              type="text"
              placeholder="Acme Corp"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading || !company.trim()}>
              {isLoading ? 'Fetching…' : 'Submit'}
            </button>
          </div>
        </form>
        {error && <p className="status error">{error}</p>}

        <section className="analysis-block">
          <header>
            <h2>Analysis Overview</h2>
            {meta?.model && <span className="badge subtle">Model: {meta.model}</span>}
          </header>

          {sections.length > 0 ? (
            <div className="reader">
              {sections.map((section, index) => (
                <article key={`${section.title ?? 'section'}-${index}`}>
                  {section.title && <h3>{section.title}</h3>}
                  <div
                    className="markdown"
                    dangerouslySetInnerHTML={{
                      __html: DOMPurify.sanitize(
                        marked.parse(section.content || '', { breaks: true }),
                      ),
                    }}
                  />
                </article>
              ))}
            </div>
          ) : (
            <div className="placeholder card">
              <p>Results will appear here after you submit a request.</p>
              <small>Tip: make sure the FastAPI server is running on port 8000.</small>
            </div>
          )}
        </section>
      </section>
    </main>
  )
}

export default App
