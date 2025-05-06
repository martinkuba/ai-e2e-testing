
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
ANTHROPIC_API_KEY=...
```

## Run

Run with interactive chat interface
```shell
python client-anthropic.py node_modules/@playwright/mcp/cli.js
```

Run predefined test cases (list of prompts)
```shell
python client-anthropic.py test-instructions.py
```
