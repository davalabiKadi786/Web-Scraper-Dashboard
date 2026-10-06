import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Web Scraper App")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head><title>Scraper Control Panel</title></head>
        <body style="font-family: Arial; margin: 50px; text-align: center;">
            <h1>🕸️ Web Scraper Dashboard</h1>
            <p>Click a button below to run the scraping application processes:</p>
            <br>
            <button onclick="runScraper('quotes')" style="padding:15px 30px; font-size:16px; background:#007acc; color:white; border:none; cursor:pointer; margin:10px;">Run Quotes Scraper</button>
            <button onclick="runScraper('books')" style="padding:15px 30px; font-size:16px; background:#28a745; color:white; border:none; cursor:pointer; margin:10px;">Run Books Scraper</button>
            <div id="output" style="margin-top:30px; padding:20px; border:1px solid #ddd; background:#f9f9f9; text-align:left; white-space:pre-wrap;">System Status: Ready</div>
            
            <script>
                function runScraper(source) {
                    document.getElementById('output').innerText = "Running " + source + " scraper... please wait...";
                    fetch('/run/' + source)
                        .then(res => res.json())
                        .then(data => { document.getElementById('output').innerText = data.output; });
                }
            </script>
        </body>
    </html>
    """

@app.get("/run/{source}")
def run_scraper(source: str):
    if source not in ["books", "quotes"]:
        return {"output": "Invalid source target"}
    
    # Executes your main.py script automatically in the background
    result = subprocess.run(
        ["python", "main.py", "--source", source], 
        capture_output=True, 
        text=True
    )
    return {"output": result.stdout if result.stdout else result.stderr}