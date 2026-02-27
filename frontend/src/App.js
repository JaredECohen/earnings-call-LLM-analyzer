import React, { useState } from 'react';
import './App.css';

function App() {
  const [symbol, setSymbol] = useState('');
  const [quarter, setQuarter] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const renderItem = (item) => {
    if (item == null) return null;
    if (typeof item === 'string' || typeof item === 'number') {
      const text = String(item);
      return text.replace(/^\s*\d+\s+/, '');
    }
    if (Array.isArray(item)) return item.map((v) => renderItem(v)).filter(Boolean).join(', ');
    if (typeof item === 'object') {
      if (item.risk && item.details) return `${item.risk}: ${item.details}`;
      if (item.category && item.risk) return `${item.category}: ${item.risk}`;
      if (item.category && item.details) return `${item.category}: ${item.details}`;
      if (item.description || item.details || item.summary) {
        return item.description || item.details || item.summary;
      }
      if (item.category && item.description) return item.description;
      if (item.category && item.details) return item.details;
      if (item.category && item.summary) return item.summary;
      const preferred = [
        item.current_mention,
        item.prior_mention,
        item.trend,
        item.resolution,
        item.prior_risk,
        item.status,
      ]
        .map((v) => renderItem(v))
        .filter(Boolean);
      if (preferred.length) return preferred.join(' ');
      return Object.values(item)
        .map((v) => renderItem(v))
        .filter(Boolean)
        .join(' ');
    }
    return String(item);
  };

  const asArray = (value) => (Array.isArray(value) ? value : value ? [value] : []);

  const renderGuidanceText = (value) => {
    if (value == null) return null;
    if (typeof value === 'string' || typeof value === 'number') return String(value);
    if (Array.isArray(value)) {
      return value
        .map((v) => renderGuidanceText(v))
        .filter((v) => v && v.trim().toLowerCase() !== 'not provided')
        .join(' ');
    }
    if (typeof value === 'object') {
      const parts = [];
      for (const v of Object.values(value)) {
        if (v == null) continue;
        if (typeof v === 'string' || typeof v === 'number') {
          const text = String(v);
          if (text.trim().toLowerCase() !== 'not provided') {
            parts.push(text);
          }
        } else if (Array.isArray(v)) {
          const inner = v
            .map((x) => renderGuidanceText(x))
            .filter((x) => x && x.trim().toLowerCase() !== 'not provided')
            .join(' ');
          if (inner) parts.push(inner);
        } else if (typeof v === 'object') {
          const inner = Object.values(v)
            .map((x) => renderGuidanceText(x))
            .filter((x) => x && x.trim().toLowerCase() !== 'not provided')
            .join(' ');
          if (inner) parts.push(inner);
        }
      }
      const deduped = [];
      for (const part of parts) {
        if (!part) continue;
        if (deduped.length === 0 || deduped[deduped.length - 1] !== part) {
          deduped.push(part);
        }
      }
      return deduped.join(' | ');
    }
    return String(value);
  };

  const renderGuidanceBlock = (value) => {
    if (value == null) return null;
    if (typeof value === 'string' || typeof value === 'number') {
      const text = renderGuidanceText(value);
      const segmentPrefix = /^segment changes:\s*/i;
      if (segmentPrefix.test(text) && text.includes('|')) {
        const cleaned = text.replace(segmentPrefix, '');
        const parts = cleaned.split('|').map((p) => p.trim()).filter(Boolean);
        const labels = [
          'Intelligent Cloud',
          'More Personal Computing',
          'Productivity and Business Processes',
        ];
        return (
          <div>
            {parts.map((part, i) => (
              <p key={i}>
                <strong>{labels[i] || `Segment ${i + 1}`}:</strong> {part}
              </p>
            ))}
          </div>
        );
      }
      return <p>{text}</p>;
    }
    if (Array.isArray(value)) {
      return (
        <div>
          {value
            .map((v, i) => {
              const text = renderGuidanceText(v);
              if (!text) return null;
              return <p key={i}>{text}</p>;
            })
            .filter(Boolean)}
        </div>
      );
    }
    if (typeof value === 'object') {
      return (
        <div>
          {Object.entries(value).map(([key, v]) => {
            const text = renderGuidanceText(v);
            if (!text) return null;
            const label = key.replace(/_/g, ' ');
            return (
              <p key={key}>
                <strong>{label}:</strong> {text}
              </p>
            );
          })}
        </div>
      );
    }
    return <p>{String(value)}</p>;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol, quarter: quarter || undefined }),
      });

      const rawText = await response.text();
      if (!rawText) {
        throw new Error(`Empty response from server (status ${response.status} ${response.statusText})`);
      }
      let data;
      try {
        data = JSON.parse(rawText);
      } catch (parseErr) {
        throw new Error(`Non-JSON response: ${rawText.slice(0, 200)}`);
      }

      if (!response.ok) {
        throw new Error(data.error || 'Analysis failed');
      }

      if (data.error) {
        const detail = data.raw_response
          ? `${data.error}\n\n${data.raw_response}`
          : data.error;
        throw new Error(detail);
      }

      setResult(data);
    } catch (err) {
      console.error('Fetch error:', err);
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>📊 Stock Earnings Calls Analyzer</h1>
        <p>AI-Powered Earnings Call Intelligence Platform</p>
      </header>

      <main className="container">
        <form onSubmit={handleSubmit} className="analysis-form">
          <div className="form-group">
            <label htmlFor="symbol">Company Symbol:</label>
            <input
              type="text"
              id="symbol"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g., MSFT, AAPL"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="quarter">Quarter (optional):</label>
            <input
              type="text"
              id="quarter"
              value={quarter}
              onChange={(e) => setQuarter(e.target.value)}
              placeholder="e.g., 2024Q1"
            />
          </div>

          <button type="submit" disabled={loading}>
            {loading ? '🔄 Analyzing...' : '🔍 Analyze'}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {result && (
          <div className="results">
            <h2>Analysis Results</h2>

            <section className="result-section">
              <h3>📈 Performance Summary</h3>
              <div className="subsection">
                <h4>Current Quarter</h4>
                <p>{renderItem(result.performance_summary?.current_quarter)}</p>
              </div>
              <div className="subsection">
                <h4>Prior Quarter</h4>
                <p>{renderItem(result.performance_summary?.prior_quarter)}</p>
              </div>
              <div className="subsection">
                <h4>Key Changes</h4>
                <p>{renderItem(result.performance_summary?.key_changes)}</p>
              </div>
            </section>

            <section className="result-section">
              <h3>🎭 Management Tone</h3>
              <div className="subsection">
                <h4>Current Quarter Tone</h4>
                <p>{renderItem(result.management_tone?.current_quarter_tone)}</p>
              </div>
              <div className="subsection">
                <h4>Prior Quarter Tone</h4>
                <p>{renderItem(result.management_tone?.prior_quarter_tone)}</p>
              </div>
              <div className="subsection">
                <h4>Tone Shift</h4>
                <p>{renderItem(result.management_tone?.tone_shift)}</p>
              </div>
            </section>

            <section className="result-section">
              <h3>📊 Bullish/Bearish Statements</h3>
              {result.bullish_bearish_statements?.current_quarter ? (
                <>
                  <div className="subsection">
                    <h4>Current Quarter Bullish Statements</h4>
                    <ul>
                      {asArray(result.bullish_bearish_statements.current_quarter.bullish_statements).map(
                        (stmt, i) => (
                          <li key={i}>{renderItem(stmt)}</li>
                        )
                      )}
                    </ul>
                  </div>
                  <div className="subsection">
                    <h4>Current Quarter Bearish Statements</h4>
                    <ul>
                      {asArray(result.bullish_bearish_statements.current_quarter.bearish_statements).map(
                        (stmt, i) => (
                          <li key={i}>{renderItem(stmt)}</li>
                        )
                      )}
                    </ul>
                  </div>
                  <div className="subsection">
                    <h4>Current Quarter Net Sentiment</h4>
                    <p>{renderItem(result.bullish_bearish_statements.current_quarter.net_sentiment)}</p>
                  </div>

                  <div className="subsection">
                    <h4>Prior Quarter Bullish Statements</h4>
                    <ul>
                      {asArray(result.bullish_bearish_statements.prior_quarter?.bullish_statements).map(
                        (stmt, i) => (
                          <li key={i}>{renderItem(stmt)}</li>
                        )
                      )}
                    </ul>
                  </div>
                  <div className="subsection">
                    <h4>Prior Quarter Bearish Statements</h4>
                    <ul>
                      {asArray(result.bullish_bearish_statements.prior_quarter?.bearish_statements).map(
                        (stmt, i) => (
                          <li key={i}>{renderItem(stmt)}</li>
                        )
                      )}
                    </ul>
                  </div>
                  <div className="subsection">
                    <h4>Prior Quarter Net Sentiment</h4>
                    <p>{renderItem(result.bullish_bearish_statements.prior_quarter?.net_sentiment)}</p>
                  </div>
                  <div className="subsection">
                    <h4>Sentiment Change</h4>
                    <p>{renderItem(result.bullish_bearish_statements.sentiment_change)}</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="subsection">
                    <h4>Bullish Statements</h4>
                    <ul>
                      {asArray(result.bullish_bearish_statements?.bullish_statements).map((stmt, i) => (
                        <li key={i}>{renderItem(stmt)}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="subsection">
                    <h4>Bearish Statements</h4>
                    <ul>
                      {asArray(result.bullish_bearish_statements?.bearish_statements).map((stmt, i) => (
                        <li key={i}>{renderItem(stmt)}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="subsection">
                    <h4>Net Sentiment</h4>
                    <p>{renderItem(result.bullish_bearish_statements?.net_sentiment)}</p>
                  </div>
                </>
              )}
            </section>

            <section className="result-section">
              <h3>🔮 Guidance Changes</h3>
              <div className="subsection">
                <h4>Revenue Guidance</h4>
                {renderGuidanceBlock(result.guidance_changes?.revenue_guidance)}
              </div>
              <div className="subsection">
                <h4>Margin Guidance</h4>
                {renderGuidanceBlock(result.guidance_changes?.margin_guidance)}
              </div>
              <div className="subsection">
                <h4>Capex Guidance</h4>
                {renderGuidanceBlock(result.guidance_changes?.capex_guidance)}
              </div>
              <div className="subsection">
                <h4>Other Guidance</h4>
                {renderGuidanceBlock(result.guidance_changes?.other_guidance)}
              </div>
              <div className="subsection">
                <h4>Guidance Summary</h4>
                {renderGuidanceBlock(result.guidance_changes?.guidance_summary)}
              </div>
            </section>

            <section className="result-section">
              <h3>⚠️ Risk Analysis</h3>
              <div className="subsection">
                <h4>Identified Risks</h4>
                <ul>
                  {result.risk_analysis?.identified_risks?.map((risk, i) => (
                    <li key={i}>{renderItem(risk)}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>New Risks</h4>
                <ul>
                  {result.risk_analysis?.new_risks?.map((risk, i) => (
                    <li key={i}>{renderItem(risk)}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Recurring Risks</h4>
                <ul>
                  {result.risk_analysis?.recurring_risks?.map((risk, i) => (
                    <li key={i}>{renderItem(risk)}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Resolved Risks</h4>
                <ul>
                  {result.risk_analysis?.resolved_risks?.map((risk, i) => (
                    <li key={i}>{renderItem(risk)}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Risk Assessment</h4>
                <p>{renderItem(result.risk_analysis?.risk_assessment)}</p>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
