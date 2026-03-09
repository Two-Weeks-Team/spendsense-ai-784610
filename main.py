from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from models import Base, engine
from routes import api_router

load_dotenv()

app = FastAPI(
    title="SpendSense AI",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def landing():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpendSense AI - Smart Finance Coach</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: { green: '#10b981', cyan: '#06b6d4' },
        dark: { bg: '#0a0a0a', card: '#171717', border: '#262626', muted: '#a3a3a3' }
      }
    }
  }
}
</script>
<style>
.gradient-text { background: linear-gradient(135deg, #10b981, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.gradient-border { border-image: linear-gradient(135deg, #10b981, #06b6d4) 1; }
@keyframes spin { to { transform: rotate(360deg); } }
.spinner { width: 1.25rem; height: 1.25rem; border: 2px solid #262626; border-top-color: #10b981; border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
</style>
</head>
<body class="bg-[#0a0a0a] text-[#e5e5e5] min-h-screen">

<div class="max-w-3xl mx-auto px-4 py-10 sm:py-16">

  <!-- Hero -->
  <header class="text-center mb-12">
    <h1 class="text-4xl sm:text-5xl font-extrabold gradient-text mb-3">SpendSense AI</h1>
    <p class="text-lg text-[#a3a3a3] mb-4">Your AI-driven personal finance coach that turns transactions into savings.</p>
    <div class="flex justify-center gap-2 flex-wrap">
      <span class="px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/25">AI-Powered</span>
      <span class="px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/25">DigitalOcean</span>
      <span class="px-3 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/25">Live</span>
    </div>
    <div class="flex justify-center gap-3 mt-5 flex-wrap">
      <a href="/docs" class="px-4 py-2 rounded-lg bg-[#10b981] text-white text-sm font-semibold hover:bg-[#059669] transition">API Docs</a>
      <a href="/redoc" class="px-4 py-2 rounded-lg bg-[#262626] text-[#d4d4d4] text-sm font-semibold border border-[#404040] hover:bg-[#333] transition">ReDoc</a>
    </div>
  </header>

  <!-- Section 1: Upload CSV -->
  <section class="bg-[#171717] border border-[#262626] rounded-xl p-5 sm:p-6 mb-4">
    <h2 class="text-lg font-bold text-[#f5f5f5] mb-1">Upload CSV</h2>
    <p class="text-xs text-[#737373] mb-4">CSV must have columns: <code class="text-[#a3a3a3]">date</code>, <code class="text-[#a3a3a3]">description</code>, <code class="text-[#a3a3a3]">amount</code></p>
    <form id="uploadForm" class="space-y-3">
      <div>
        <label class="block text-sm text-[#a3a3a3] mb-1">Select CSV file</label>
        <input type="file" id="csvFile" accept=".csv" required class="block w-full text-sm text-[#a3a3a3] file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[#262626] file:text-[#d4d4d4] hover:file:bg-[#333] file:cursor-pointer file:transition" />
      </div>
      <button type="submit" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#10b981] text-white text-sm font-semibold hover:bg-[#059669] transition disabled:opacity-50 disabled:cursor-not-allowed">
        <span>Upload</span>
        <span id="uploadSpinner" class="spinner hidden"></span>
      </button>
    </form>
    <div id="uploadResult" class="mt-4 hidden"></div>
  </section>

  <!-- Section 2: Categorize Transactions -->
  <section class="bg-[#171717] border border-[#262626] rounded-xl p-5 sm:p-6 mb-4">
    <h2 class="text-lg font-bold text-[#f5f5f5] mb-1">Categorize Transactions</h2>
    <p class="text-xs text-[#737373] mb-4">AI-powered expense categorization for your uploaded transactions.</p>
    <form id="categorizeForm" class="space-y-3">
      <div>
        <label class="block text-sm text-[#a3a3a3] mb-1">Model version <span class="text-[#525252]">(optional)</span></label>
        <input type="text" id="modelVersion" placeholder="e.g. v2" class="w-full px-3 py-2 rounded-lg bg-[#0a0a0a] border border-[#262626] text-sm text-[#e5e5e5] placeholder-[#525252] focus:outline-none focus:border-[#10b981] transition" />
      </div>
      <button type="submit" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#10b981] text-white text-sm font-semibold hover:bg-[#059669] transition disabled:opacity-50 disabled:cursor-not-allowed">
        <span>Categorize</span>
        <span id="categorizeSpinner" class="spinner hidden"></span>
      </button>
    </form>
    <div id="categorizeResult" class="mt-4 hidden"></div>
  </section>

  <!-- Section 3: Generate Savings Plan -->
  <section class="bg-[#171717] border border-[#262626] rounded-xl p-5 sm:p-6 mb-4">
    <h2 class="text-lg font-bold text-[#f5f5f5] mb-1">Generate Savings Plan</h2>
    <p class="text-xs text-[#737373] mb-4">Get AI-generated savings recommendations for a given timeframe.</p>
    <form id="savingsForm" class="space-y-3">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm text-[#a3a3a3] mb-1">Start Date</label>
          <input type="date" id="savingsStart" required class="w-full px-3 py-2 rounded-lg bg-[#0a0a0a] border border-[#262626] text-sm text-[#e5e5e5] focus:outline-none focus:border-[#10b981] transition" />
        </div>
        <div>
          <label class="block text-sm text-[#a3a3a3] mb-1">End Date</label>
          <input type="date" id="savingsEnd" required class="w-full px-3 py-2 rounded-lg bg-[#0a0a0a] border border-[#262626] text-sm text-[#e5e5e5] focus:outline-none focus:border-[#10b981] transition" />
        </div>
      </div>
      <button type="submit" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#10b981] text-white text-sm font-semibold hover:bg-[#059669] transition disabled:opacity-50 disabled:cursor-not-allowed">
        <span>Generate Plan</span>
        <span id="savingsSpinner" class="spinner hidden"></span>
      </button>
    </form>
    <div id="savingsResult" class="mt-4 hidden"></div>
  </section>

  <!-- Section 4: Weekly Report -->
  <section class="bg-[#171717] border border-[#262626] rounded-xl p-5 sm:p-6 mb-4">
    <h2 class="text-lg font-bold text-[#f5f5f5] mb-1">Weekly Report</h2>
    <p class="text-xs text-[#737373] mb-4">View spending breakdown and savings recommendations for a date range.</p>
    <form id="reportForm" class="space-y-3">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm text-[#a3a3a3] mb-1">Start Date</label>
          <input type="date" id="reportStart" required class="w-full px-3 py-2 rounded-lg bg-[#0a0a0a] border border-[#262626] text-sm text-[#e5e5e5] focus:outline-none focus:border-[#10b981] transition" />
        </div>
        <div>
          <label class="block text-sm text-[#a3a3a3] mb-1">End Date</label>
          <input type="date" id="reportEnd" required class="w-full px-3 py-2 rounded-lg bg-[#0a0a0a] border border-[#262626] text-sm text-[#e5e5e5] focus:outline-none focus:border-[#10b981] transition" />
        </div>
      </div>
      <button type="submit" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#10b981] text-white text-sm font-semibold hover:bg-[#059669] transition disabled:opacity-50 disabled:cursor-not-allowed">
        <span>Get Report</span>
        <span id="reportSpinner" class="spinner hidden"></span>
      </button>
    </form>
    <div id="reportResult" class="mt-4 hidden"></div>
  </section>

  <!-- Footer -->
  <footer class="text-center mt-8 text-xs text-[#525252]">
    Generated by <a href="https://github.com/Two-Weeks-Team/vibeDeploy" class="text-[#10b981] hover:underline">vibeDeploy</a>
    &bull; Powered by <a href="https://www.digitalocean.com/products/gradient-ai" class="text-[#10b981] hover:underline">DigitalOcean Gradient AI</a>
  </footer>

</div>

<script>
function showLoading(spinnerId, btnEl) {
  document.getElementById(spinnerId).classList.remove('hidden');
  btnEl.disabled = true;
}
function hideLoading(spinnerId, btnEl) {
  document.getElementById(spinnerId).classList.add('hidden');
  btnEl.disabled = false;
}
function showResult(containerId, html, isError) {
  const el = document.getElementById(containerId);
  el.innerHTML = html;
  el.className = 'mt-4 p-4 rounded-lg text-sm ' + (isError ? 'bg-red-500/10 border border-red-500/30 text-red-400' : 'bg-green-500/10 border border-green-500/30 text-green-300');
  el.classList.remove('hidden');
}
function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// Upload CSV
document.getElementById('uploadForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = this.querySelector('button');
  const fileInput = document.getElementById('csvFile');
  if (!fileInput.files.length) return;
  showLoading('uploadSpinner', btn);
  try {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const res = await fetch('/api/v1/upload-csv', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    const rows = data.rows_processed || data.rows || data.count || '—';
    showResult('uploadResult',
      '<p class="font-semibold mb-1">Upload Successful</p>' +
      '<p>Status: ' + escapeHtml(data.status || 'ok') + '</p>' +
      '<p>Rows processed: ' + escapeHtml(String(rows)) + '</p>', false);
  } catch (err) {
    showResult('uploadResult', '<p class="font-semibold">Error</p><p>' + escapeHtml(err.message) + '</p>', true);
  } finally {
    hideLoading('uploadSpinner', btn);
  }
});

// Categorize Transactions
document.getElementById('categorizeForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = this.querySelector('button');
  showLoading('categorizeSpinner', btn);
  try {
    const body = { model_version: document.getElementById('modelVersion').value || null };
    const res = await fetch('/api/v1/categorize-transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    const txns = data.transactions || data.results || data.categorized_transactions || (Array.isArray(data) ? data : []);
    let html = '<p class="font-semibold mb-2">Categorization Results</p>';
    if (txns.length === 0) {
      html += '<p class="text-[#a3a3a3]">No transactions found. Upload a CSV first.</p>';
    } else {
      html += '<div class="overflow-x-auto"><table class="w-full text-left text-xs"><thead><tr class="border-b border-[#262626]">' +
        '<th class="py-2 pr-3">Description</th><th class="py-2 pr-3">Amount</th><th class="py-2 pr-3">Category</th><th class="py-2">Confidence</th></tr></thead><tbody>';
      txns.forEach(function(t) {
        html += '<tr class="border-b border-[#262626]/50">' +
          '<td class="py-1.5 pr-3">' + escapeHtml(t.description || '—') + '</td>' +
          '<td class="py-1.5 pr-3">' + escapeHtml(String(t.amount != null ? t.amount : '—')) + '</td>' +
          '<td class="py-1.5 pr-3">' + escapeHtml(t.predicted_category || t.category || '—') + '</td>' +
          '<td class="py-1.5">' + escapeHtml(t.confidence_score != null ? (parseFloat(t.confidence_score) * 100).toFixed(1) + '%' : '—') + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }
    showResult('categorizeResult', html, false);
  } catch (err) {
    showResult('categorizeResult', '<p class="font-semibold">Error</p><p>' + escapeHtml(err.message) + '</p>', true);
  } finally {
    hideLoading('categorizeSpinner', btn);
  }
});

// Generate Savings Plan
document.getElementById('savingsForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = this.querySelector('button');
  showLoading('savingsSpinner', btn);
  try {
    const body = {
      timeframe_start: document.getElementById('savingsStart').value,
      timeframe_end: document.getElementById('savingsEnd').value
    };
    const res = await fetch('/api/v1/generate-savings-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    const recs = data.recommendations || data.savings_plan || data.plans || (Array.isArray(data) ? data : []);
    let html = '<p class="font-semibold mb-2">Savings Plan</p>';
    if (recs.length === 0) {
      html += '<p class="text-[#a3a3a3]">No recommendations generated. Try uploading and categorizing data first.</p>';
    } else {
      recs.forEach(function(r) {
        html += '<div class="mb-3 p-3 rounded-lg bg-[#0a0a0a] border border-[#262626]">' +
          '<p class="font-medium text-[#f5f5f5]">' + escapeHtml(r.description || r.recommendation || '—') + '</p>' +
          '<div class="flex gap-4 mt-1 text-xs text-[#a3a3a3]">' +
          '<span>Confidence: ' + escapeHtml(r.confidence != null ? (parseFloat(r.confidence) * 100).toFixed(1) + '%' : '—') + '</span>' +
          '<span>Est. monthly savings: $' + escapeHtml(r.estimated_monthly_savings != null ? parseFloat(r.estimated_monthly_savings).toFixed(2) : '—') + '</span>' +
          '</div></div>';
      });
    }
    showResult('savingsResult', html, false);
  } catch (err) {
    showResult('savingsResult', '<p class="font-semibold">Error</p><p>' + escapeHtml(err.message) + '</p>', true);
  } finally {
    hideLoading('savingsSpinner', btn);
  }
});

// Weekly Report
document.getElementById('reportForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = this.querySelector('button');
  showLoading('reportSpinner', btn);
  try {
    const startDate = document.getElementById('reportStart').value;
    const endDate = document.getElementById('reportEnd').value;
    const res = await fetch('/api/v1/weekly-report?start_date=' + encodeURIComponent(startDate) + '&end_date=' + encodeURIComponent(endDate));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    let html = '<p class="font-semibold mb-2">Weekly Report</p>';
    html += '<p class="mb-2">Total spending: <span class="text-[#f5f5f5] font-medium">$' + escapeHtml(data.total_spending != null ? parseFloat(data.total_spending).toFixed(2) : '—') + '</span></p>';
    const breakdown = data.category_breakdown || data.breakdown || {};
    const cats = Object.keys(breakdown);
    if (cats.length > 0) {
      html += '<p class="text-xs text-[#a3a3a3] mb-1">Category Breakdown</p>';
      html += '<div class="overflow-x-auto"><table class="w-full text-left text-xs mb-3"><thead><tr class="border-b border-[#262626]">' +
        '<th class="py-2 pr-3">Category</th><th class="py-2">Amount</th></tr></thead><tbody>';
      cats.forEach(function(c) {
        html += '<tr class="border-b border-[#262626]/50"><td class="py-1.5 pr-3">' + escapeHtml(c) + '</td>' +
          '<td class="py-1.5">$' + escapeHtml(parseFloat(breakdown[c]).toFixed(2)) + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }
    const tips = data.savings_recommendations || data.recommendations || [];
    if (tips.length > 0) {
      html += '<p class="text-xs text-[#a3a3a3] mb-1">Savings Recommendations</p><ul class="list-disc list-inside text-xs space-y-1">';
      tips.forEach(function(t) {
        const text = typeof t === 'string' ? t : (t.description || t.recommendation || JSON.stringify(t));
        html += '<li>' + escapeHtml(text) + '</li>';
      });
      html += '</ul>';
    }
    showResult('reportResult', html, false);
  } catch (err) {
    showResult('reportResult', '<p class="font-semibold">Error</p><p>' + escapeHtml(err.message) + '</p>', true);
  } finally {
    hideLoading('reportSpinner', btn);
  }
});
</script>

</body>
</html>"""


app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
