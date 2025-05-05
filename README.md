
## Setup

Setup Python virtual environment

```shell
python -m venv venv
source venv/bin/activate
```

Install Python dependencies

```shell
pip install -r requirements.txt
```

Install Node dependencies

```shell
npm install
```

## Configuration

Create `.env` file in the working directory, and add environmnent variables depending on the service you use.

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

## Run

Run with Anthropic
```shell
python client-anthropic.py node_modules/@playwright/mcp/cli.js
```

You can also pass parameters to Playwright
```shell
python client-anthropic.py ~/dev/playwright-mcp/cli.js --config ./config.json
```

