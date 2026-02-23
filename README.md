# Aemeath - Your Desktop Assistant

## How to use?
### 1. Clone the repository into your computer
`https://github.com/Y0S0NG/Aemeath.git`

### 2. Configure the OpenAI API in your backend
```bash
cd backend
cp .env.example .env
```
Then replace the placeholder with your own OpenAI API key

### 3. Start backend - FastAPI on `localhost` (you should in `\backend` directory)
```
uvicorn app.main:app --reload
```

### 4. Start frontend - Electron on desktop
```
cd ..
cd frontend
npm run electron:dev
```

And now you are all set!