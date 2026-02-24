import React, { useState } from 'react';
import './App.css';

function App() {
  const [symbol, setSymbol] = useState('');
  const [quarter, setQuarter] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol, quarter: quarter || undefined }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Analysis failed');
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
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
                <p>{result.performance_summary?.current_quarter}</p>
              </div>
              <div className="subsection">
                <h4>Prior Quarter</h4>
                <p>{result.performance_summary?.prior_quarter}</p>
              </div>
              <div className="subsection">
                <h4>Key Changes</h4>
                <p>{result.performance_summary?.key_changes}</p>
              </div>
            </section>

            <section className="result-section">
              <h3>🎭 Management Tone</h3>
              <div className="subsection">
                <h4>Current Quarter Tone</h4>
                <p>{result.management_tone?.current_quarter_tone}</p>
              </div>
              <div className="subsection">
                <h4>Prior Quarter Tone</h4>
                <p>{result.management_tone?.prior_quarter_tone}</p>
              </div>
              <div className="subsection">
                <h4>Tone Shift</h4>
                <p>{result.management_tone?.tone_shift}</p>
              </div>
            </section>

            <section className="result-section">
              <h3>📊 Bullish/Bearish Statements</h3>
              <div className="subsection">
                <h4>Bullish Statements</h4>
                <ul>
                  {result.bullish_bearish_statements?.bullish_statements?.map((stmt, i) => (
                    <li key={i}>{stmt}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Bearish Statements</h4>
                <ul>
                  {result.bullish_bearish_statements?.bearish_statements?.map((stmt, i) => (
                    <li key={i}>{stmt}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Net Sentiment</h4>
                <p>{result.bullish_bearish_statements?.net_sentiment}</p>
              </div>
            </section>

            <section className="result-section">
              <h3>🔮 Guidance Changes</h3>
              <div className="subsection">
                <h4>Revenue Guidance</h4>
                <p>{result.guidance_changes?.revenue_guidance}</p>
              </div>
              <div className="subsection">
                <h4>Margin Guidance</h4>
                <p>{result.guidance_changes?.margin_guidance}</p>
              </div>
              <div className="subsection">
                <h4>Capex Guidance</h4>
                <p>{result.guidance_changes?.capex_guidance}</p>
              </div>
              <div className="subsection">
                <h4>Other Guidance</h4>
                <p>{result.guidance_changes?.other_guidance}</p>
              </div>
              <div className="subsection">
                <h4>Guidance Summary</h4>
                <p>{result.guidance_changes?.guidance_summary}</p>
              </div>
            </section>

            <section className="result-section">
              <h3>⚠️ Risk Analysis</h3>
              <div className="subsection">
                <h4>Identified Risks</h4>
                <ul>
                  {result.risk_analysis?.identified_risks?.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>New Risks</h4>
                <ul>
                  {result.risk_analysis?.new_risks?.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Recurring Risks</h4>
                <ul>
                  {result.risk_analysis?.recurring_risks?.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Resolved Risks</h4>
                <ul>
                  {result.risk_analysis?.resolved_risks?.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
              <div className="subsection">
                <h4>Risk Assessment</h4>
                <p>{result.risk_analysis?.risk_assessment}</p>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
